#!/usr/bin/env python3
"""Reconstruct the read access pattern for an Iceberg table from query logs.

Two input modes (use one):
  --trino-queries FILE   JSON/CSV export of system.runtime.queries (or any table
                         with a `query` column; optional input_rows/output_rows/
                         input_bytes columns enable selectivity & scan stats).
  --sql-file FILE        Raw SQL statements separated by ';' or newlines.
  --spark-eventlog FILE  Spark event-log (NDJSON); best-effort plan parsing of
                         PartitionFilters / dataFilters / PushedFilters.

Emits workload.json: ranked WHERE-clause columns, predicate type per column
(equality vs range → sort vs z-order vs bloom hints), join columns, query
frequency, selectivity, and (Spark) partition-pruning effectiveness.

SQL-text parsing uses `sqlglot` when importable (accurate); otherwise a regex
fallback (approximate — flagged in the output). Stdlib only otherwise.

Usage:
  parse_query_log.py --trino-queries q.json --table cat.db.tbl --out workload.json
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


def load_rows(path):
    with open(path) as fh:
        text = fh.read().strip()
    if not text:
        return []
    if path.endswith(".csv"):
        return list(csv.DictReader(text.splitlines()))
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        return [json.loads(l) for l in text.splitlines() if l.strip()]


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
    """Return (referenced: bool, equality_cols, range_cols, join_cols) or None
    if the statement could not be parsed."""
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
            res = extract_regex(sql, aliases)  # fall back per-statement
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
        ib = _num(r.get("input_bytes") or r.get("physical_input_bytes"))
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
    """Best-effort parse of physical plans. Counts one scan per matching plan and
    extracts columns only from genuine attribute references (`name#<id>`), which
    excludes Spark function names (isnotnull) and literal values."""
    part_present, scans = 0, 0
    col_counts = {}
    attr_re = re.compile(r"([a-zA-Z_]\w*)#\d+")  # Spark attribute reference
    filt_re = re.compile(r"(PartitionFilters|dataFilters):\s*\[([^\]]*)\]")
    plan_re = re.compile(r"physicalPlanDescription", re.IGNORECASE)
    with open(path) as fh:
        for line in fh:
            if not plan_re.search(line):
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            plan = ev.get("physicalPlanDescription") or ""
            if not any(a in plan.lower() for a in aliases):
                continue
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
    ranked = [{"column": c, "count": n} for c, n in
              sorted(col_counts.items(), key=lambda kv: kv[1], reverse=True)]
    return {
        "scans_analyzed": scans,
        "filter_columns": ranked,
        "partition_filter_present": part_present,
        "partition_prune_rate": round(part_present / scans, 3) if scans else None,
        "parser": "spark-eventlog-regex",
        "note": "Plan-text parsing is approximate; one scan counted per plan, "
                "columns from attribute refs (name#id) only.",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", required=True, help="fully-qualified table, e.g. cat.db.tbl")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--trino-queries")
    src.add_argument("--sql-file")
    src.add_argument("--spark-eventlog")
    ap.add_argument("--query-column", default="query")
    ap.add_argument("--out", default="-")
    args = ap.parse_args(argv)

    aliases = table_aliases(args.table)
    result = {"table": args.table}

    if args.spark_eventlog:
        result.update(analyze_spark_eventlog(args.spark_eventlog, aliases))
    else:
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
