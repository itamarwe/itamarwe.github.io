#!/usr/bin/env python3
"""Reconstruct the read access pattern for an Iceberg table from query logs.

Input modes (one SQL source required, --explain-analyze is supplementary):
  --trino-queries FILE   JSON/CSV export of system.runtime.queries (or any table
                         with a `query` column; optional input_rows/output_rows/
                         input_bytes/physical_input_bytes columns enable selectivity
                         and scan stats). Also accepts Trino JSON event-listener logs
                         (queryCompletedEvent envelope auto-detected; physicalInputDataSize
                         read as a measured byte count).
  --sql-file FILE        Raw SQL statements separated by ';' or newlines.
  --spark-eventlog FILE  Spark event-log (NDJSON); parses PartitionFilters/dataFilters
                         from physicalPlanDescription and extracts measured bytes-scanned
                         from SparkListenerSQLExecutionEnd metrics ("size of files read").

  --explain-analyze FILE  EXPLAIN ANALYZE text output (supplementary, can be combined
                          with any source above). Extracts "Physical Input Data Size"
                          lines from Trino EXPLAIN ANALYZE output and uses them as
                          measured median_bytes_scanned if not already set by the log.

Emits workload.json: ranked WHERE-clause columns, predicate type per column
(equality vs range → sort vs z-order vs bloom hints), join columns, query
frequency, selectivity, and (Spark) partition-pruning effectiveness.

When median_bytes_scanned is present in workload.json, simulate.py uses it as
the real baseline rather than estimating from total_gb × (1 - prune_rate).

SQL-text parsing uses `sqlglot` when importable (accurate); otherwise a regex
fallback (approximate — flagged in the output). Stdlib only otherwise.

Usage:
  parse_query_log.py --trino-queries q.json --table cat.db.tbl --out workload.json
  parse_query_log.py --spark-eventlog app.log --table cat.db.tbl --out workload.json
  parse_query_log.py --sql-file q.sql --explain-analyze explain.txt --table cat.db.tbl
"""
import argparse
import csv
import json
import re
import statistics as stats
import sys

try:
    import sqlglot
    from sqlglot import exp
    _HAVE_SQLGLOT = True
except ImportError:
    _HAVE_SQLGLOT = False

RANGE_OPS = ("between", ">", "<", ">=", "<=")


# ---------- Byte-string parser ----------

def parse_bytes_str(s):
    """Convert a human-readable byte string ('1.23 GB', '456 MiB', '789 B') to float bytes.
    Handles IEC (GiB/MiB/KiB) and SI (GB/MB/KB) — treated identically for this model."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).replace(",", "")
    m = re.search(r"([\d.]+)\s*([BKMGTPE]i?B?)", s, re.IGNORECASE)
    if not m:
        try:
            return float(s.split()[0])
        except (ValueError, IndexError):
            return None
    val = float(m.group(1))
    unit = m.group(2).upper().replace("IB", "B").rstrip("B")
    mult = {"": 1, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "P": 1e15, "E": 1e18}
    return val * mult.get(unit, 1.0)


# ---------- Row loading ----------

def load_rows(path):
    with open(path) as fh:
        text = fh.read().strip()
    if not text:
        return []
    if path.endswith(".csv"):
        return list(csv.DictReader(text.splitlines()))
    try:
        data = json.loads(text)
        rows = data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        rows = [json.loads(l) for l in text.splitlines() if l.strip()]
    return _flatten_trino_event_listener(rows)


def _flatten_trino_event_listener(rows):
    """Auto-detect Trino JSON event-listener format (queryCompletedEvent envelope) and flatten.

    Trino's http-event-listener / JSON event-listener plugin emits one JSON record per query.
    Each record is {"queryCompletedEvent": {"metadata": {...}, "statistics": {...}}}.
    We flatten it to a plain row dict so the rest of the pipeline can read `query` and
    byte-count fields like `physicalInputDataSize` uniformly.
    """
    if not rows:
        return rows
    if not any("queryCompletedEvent" in r for r in rows[:5]):
        return rows
    out = []
    for r in rows:
        ev = r.get("queryCompletedEvent")
        if ev is None:
            continue  # skip queryCreatedEvent etc.
        meta = ev.get("metadata", {})
        flat = dict(ev.get("statistics", {}))
        flat["query"] = meta.get("query", "")
        flat["query_id"] = meta.get("queryId", "")
        out.append(flat)
    return out


# ---------- Table alias helpers ----------

def table_aliases(fq):
    """Candidate name fragments to match a fully-qualified table in query text."""
    parts = [p.strip('`"[]') for p in fq.split(".")]
    cands = {fq, parts[-1]}
    if len(parts) >= 2:
        cands.add(".".join(parts[-2:]))
    return {c.lower() for c in cands if c}


def norm_col(name):
    return name.split(".")[-1].strip('`"[]').lower() if name else name


# ---------- SQL-text extraction ----------

def extract_sqlglot(sql, aliases):
    """Return (referenced: bool, equality_cols, range_cols, join_cols) or None."""
    tree = None
    for dialect in ("trino", "spark", None):
        try:
            tree = sqlglot.parse_one(sql, read=dialect)
            break
        except Exception:
            continue
    if tree is None:
        return None
    tables = {t.name.lower() for t in tree.find_all(exp.Table)}
    tables |= {f"{t.db}.{t.name}".lower() for t in tree.find_all(exp.Table) if t.db}
    if not (tables & aliases):
        return (False, set(), set(), set())

    eq, rng, joins = set(), set(), set()

    def cols(node):
        return {norm_col(c.name) for c in node.find_all(exp.Column)}

    where = tree.find(exp.Where)
    if where:
        for node in where.find_all(exp.EQ, exp.In):
            eq |= cols(node)
        for node in where.find_all(exp.GT, exp.LT, exp.GTE, exp.LTE, exp.Between):
            rng |= cols(node)
    for j in tree.find_all(exp.Join):
        on = j.args.get("on")
        if on:
            joins |= cols(on)
    return (True, eq, rng, joins)


def extract_regex(sql, aliases):
    low = sql.lower()
    if not any(a in low for a in aliases):
        return (False, set(), set(), set())
    m = re.search(r"\bwhere\b(.*?)(\bgroup\s+by\b|\border\s+by\b|\blimit\b|\bhaving\b|$)",
                  low, re.DOTALL)
    eq, rng = set(), set()
    if m:
        clause = m.group(1)
        for col in re.findall(r"([a-z_][\w.]*)\s+between\b", clause):
            rng.add(norm_col(col))
        for col, op in re.findall(r"([a-z_][\w.]*)\s*(>=|<=|>|<)", clause):
            rng.add(norm_col(col))
        for col in re.findall(r"([a-z_][\w.]*)\s*=\s*", clause):
            eq.add(norm_col(col))
        for col in re.findall(r"([a-z_][\w.]*)\s+in\s*\(", clause):
            eq.add(norm_col(col))
    joins = {norm_col(c) for c in re.findall(r"\bjoin\b.*?\bon\b\s*([a-z_][\w.]*)", low)}
    kw = {"and", "or", "not", "null", "is", "in", "between", "select", "from", "where"}
    clean = lambda s: {c for c in s if c and c not in kw}
    return (True, clean(eq), clean(rng), clean(joins))


def analyze_sql_statements(statements, aliases, stat_rows=None):
    extract = extract_sqlglot if _HAVE_SQLGLOT else extract_regex
    matched = 0
    eq_counts, rng_counts, join_counts = {}, {}, {}
    unparsed = 0
    for sql in statements:
        res = extract(sql, aliases)
        if res is None:
            unparsed += 1
            res = extract_regex(sql, aliases)
        referenced, eq, rng, joins = res
        if not referenced:
            continue
        matched += 1
        for c in eq:
            eq_counts[c] = eq_counts.get(c, 0) + 1
        for c in rng:
            rng_counts[c] = rng_counts.get(c, 0) + 1
        for c in joins:
            join_counts[c] = join_counts.get(c, 0) + 1

    cols = {}
    for c, n in eq_counts.items():
        cols.setdefault(c, {"equality": 0, "range": 0})["equality"] += n
    for c, n in rng_counts.items():
        cols.setdefault(c, {"equality": 0, "range": 0})["range"] += n

    ranked = []
    for c, d in cols.items():
        total = d["equality"] + d["range"]
        ranked.append({
            "column": c,
            "count": total,
            "share": round(total / matched, 3) if matched else 0.0,
            "predicate_types": d,
            "dominant": "range" if d["range"] >= d["equality"] else "equality",
        })
    ranked.sort(key=lambda x: x["count"], reverse=True)

    return {
        "matched_query_count": matched,
        "unparsed_query_count": unparsed,
        "filter_columns": ranked,
        "join_columns": sorted(join_counts, key=join_counts.get, reverse=True),
        "range_cols": [r["column"] for r in ranked if r["dominant"] == "range"],
        "equality_cols": [r["column"] for r in ranked if r["dominant"] == "equality"],
        "parser": "sqlglot" if _HAVE_SQLGLOT else "regex",
        "selectivity": _selectivity(stat_rows),
    }


def _selectivity(stat_rows):
    if not stat_rows:
        return None
    ratios, scanned = [], []
    for r in stat_rows:
        ir = _num(r.get("input_rows") or r.get("processed_rows"))
        orr = _num(r.get("output_rows"))
        # Prefer integer byte fields; fall back to human-readable string fields
        # (Trino event listener uses physicalInputDataSize as "1.23 GB" strings)
        ib = (_num(r.get("input_bytes") or r.get("physical_input_bytes"))
              or parse_bytes_str(
                  r.get("physicalInputDataSize") or r.get("processedInputDataSize")
                  or r.get("physical_input_data_size") or r.get("input_data_size")))
        if ir and orr and orr > 0:
            ratios.append(ir / orr)
        if ib:
            scanned.append(ib)
    out = {}
    if ratios:
        out["median_rows_scanned_per_returned"] = round(stats.median(ratios), 1)
    if scanned:
        out["median_bytes_scanned"] = int(stats.median(scanned))
        out["p90_bytes_scanned"] = int(sorted(scanned)[int(0.9 * (len(scanned) - 1))])
    return out or None


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ---------- Spark event-log extraction ----------

def analyze_spark_eventlog(path, aliases):
    """Parse physical plans for column extraction and SQL execution metrics for bytes-scanned.

    Two types of events are read in a single pass:
    - physicalPlanDescription (SparkListenerSQLExecutionStart): column extraction from
      PartitionFilters/dataFilters using attribute references (name#id format only).
    - SparkListenerSQLExecutionEnd: "size of files read" SQL metric for matched executions,
      giving measured bytes-scanned without running any extra queries.

    One scan is counted per physicalPlanDescription event, not per filter block.
    Columns are extracted only from genuine Spark attribute references (name#id), which
    excludes function names (isnotnull) and literal values.
    """
    matched_exec_ids = set()
    byte_scans = []
    part_present, scans = 0, 0
    col_counts = {}
    attr_re = re.compile(r"([a-zA-Z_]\w*)#\d+")
    filt_re = re.compile(r"(PartitionFilters|dataFilters):\s*\[([^\]]*)\]")
    # Fast pre-filter: skip lines that can't contain either type of event
    fast_re = re.compile(r"physicalPlanDescription|SparkListenerSQLExecutionEnd")

    with open(path) as fh:
        for line in fh:
            if not fast_re.search(line):
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue

            plan = ev.get("physicalPlanDescription") or ""
            if plan:
                if not any(a in plan.lower() for a in aliases):
                    continue
                exec_id = ev.get("executionId")
                if exec_id is not None:
                    matched_exec_ids.add(exec_id)
                scans += 1
                has_partition_filter = False
                for m in filt_re.finditer(plan):
                    kind, body = m.group(1), m.group(2)
                    if kind == "PartitionFilters" and body.strip():
                        has_partition_filter = True
                    for c in attr_re.findall(body):
                        col = norm_col(c)
                        col_counts[col] = col_counts.get(col, 0) + 1
                if has_partition_filter:
                    part_present += 1
                continue

            if ev.get("Event") == "SparkListenerSQLExecutionEnd":
                exec_id = ev.get("executionId")
                if exec_id not in matched_exec_ids:
                    continue
                metrics = ev.get("metrics") or []
                metric_vals = ev.get("metricValues") or {}
                for m in metrics:
                    name = m.get("name", "").lower()
                    if "size of files read" in name or ("bytes" in name and "read" in name):
                        mid = str(m.get("id", ""))
                        b = parse_bytes_str(metric_vals.get(mid))
                        if b and b > 0:
                            byte_scans.append(b)
                        break

    ranked = [{"column": c, "count": n} for c, n in
              sorted(col_counts.items(), key=lambda kv: kv[1], reverse=True)]
    result = {
        "scans_analyzed": scans,
        "filter_columns": ranked,
        "partition_filter_present": part_present,
        "partition_prune_rate": round(part_present / scans, 3) if scans else None,
        "parser": "spark-eventlog-regex",
        "note": "Plan-text parsing is approximate; one scan counted per plan, "
                "columns from attribute refs (name#id) only.",
    }
    if byte_scans:
        result["selectivity"] = {
            "median_bytes_scanned": int(stats.median(byte_scans)),
            "p90_bytes_scanned": int(sorted(byte_scans)[int(0.9 * max(len(byte_scans) - 1, 0))]),
            "source": "spark-sql-metrics",
            "sample_count": len(byte_scans),
        }
    return result


# ---------- EXPLAIN ANALYZE extraction ----------

def parse_explain_analyze_file(path):
    """Extract measured bytes-scanned from Trino EXPLAIN ANALYZE text output.

    Trino EXPLAIN ANALYZE prints per-operator and summary lines like:
        Physical Input Data Size: 1.23 GB
    and summary lines like:
        Input: 10000000 rows (1.23 GB), Parallelism: 3

    All matching values are collected; the caller picks the median across
    multiple queries or multiple fragments — duplicates from summary+operator
    lines for the same query self-correct at the median.

    Run on 3–5 representative queries and save the output to a file:
        trino --execute "EXPLAIN ANALYZE <your query>" >> explain.txt
    """
    bytes_list = []
    phys_re = re.compile(
        r"physical\s+input(?:\s+data)?\s+size\s*:\s*([\d.,]+\s*\S+)",
        re.IGNORECASE,
    )
    input_re = re.compile(
        r"\bInput:\s*[\d,]+\s+rows?\s+\(([\d.,]+\s*\S+)\)",
        re.IGNORECASE,
    )
    with open(path) as fh:
        for line in fh:
            m = phys_re.search(line)
            if m:
                b = parse_bytes_str(m.group(1))
                if b and b > 0:
                    bytes_list.append(b)
                continue
            m = input_re.search(line)
            if m:
                b = parse_bytes_str(m.group(1))
                if b and b > 0:
                    bytes_list.append(b)
    return bytes_list


# ---------- CLI ----------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", required=True, help="fully-qualified table, e.g. cat.db.tbl")
    src = ap.add_mutually_exclusive_group(required=False)
    src.add_argument("--trino-queries",
                     help="JSON/CSV from system.runtime.queries, or Trino JSON event-listener log")
    src.add_argument("--sql-file", help="Raw SQL file; statements delimited by ';'")
    src.add_argument("--spark-eventlog", help="Spark event-log NDJSON")
    ap.add_argument("--query-column", default="query",
                    help="column name containing SQL text (default: query)")
    ap.add_argument("--explain-analyze", metavar="FILE",
                    help="EXPLAIN ANALYZE text output file; extracts measured "
                         "Physical Input Data Size (supplementary, can combine with any source)")
    ap.add_argument("--out", default="-")
    args = ap.parse_args(argv)

    if not any([args.trino_queries, args.sql_file, args.spark_eventlog, args.explain_analyze]):
        ap.error("provide at least one of --trino-queries, --sql-file, "
                 "--spark-eventlog, or --explain-analyze")

    aliases = table_aliases(args.table)
    result = {"table": args.table}

    if args.spark_eventlog:
        result.update(analyze_spark_eventlog(args.spark_eventlog, aliases))
    elif args.trino_queries or args.sql_file:
        if args.trino_queries:
            rows = load_rows(args.trino_queries)
            statements = [r.get(args.query_column, "") for r in rows]
            stat_rows = rows
        else:
            with open(args.sql_file) as fh:
                blob = fh.read()
            statements = [s.strip() for s in re.split(r";\s*\n|;\s*$", blob, flags=re.MULTILINE)
                          if s.strip()]
            stat_rows = None
        result["total_query_count"] = len(statements)
        result.update(analyze_sql_statements(statements, aliases, stat_rows))

    # Supplementary: EXPLAIN ANALYZE bytes (fills selectivity.median_bytes_scanned
    # if not already populated from the log source above)
    if args.explain_analyze:
        bytes_list = parse_explain_analyze_file(args.explain_analyze)
        if bytes_list:
            sel = result.get("selectivity") or {}
            if not sel.get("median_bytes_scanned"):
                n = len(bytes_list)
                sel["median_bytes_scanned"] = int(stats.median(bytes_list))
                sel["p90_bytes_scanned"] = int(sorted(bytes_list)[int(0.9 * max(n - 1, 0))])
                sel["source"] = "explain_analyze"
                sel["sample_count"] = n
                result["selectivity"] = sel
            result["explain_analyze_samples"] = len(bytes_list)

    text = json.dumps(result, indent=2)
    if args.out == "-":
        print(text)
    else:
        with open(args.out, "w") as fh:
            fh.write(text)
        print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
