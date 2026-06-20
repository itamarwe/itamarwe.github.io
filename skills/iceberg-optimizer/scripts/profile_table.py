#!/usr/bin/env python3
"""Profile an Iceberg table from exported metadata tables.

Reads dumps of the `snapshots` and `files` metadata tables (and optionally
`partitions` and `manifests`) and emits a structured JSON profile describing the
table's physical state and — crucially — its *ingestion shape* (write cadence,
file size at write, partition fan-out, mutability), so Phase 2 can confirm rather
than ask.

Stdlib only. Accepts JSON (array or newline-delimited) or CSV. Tolerant of
Spark's stringified map columns, e.g. summary = "{added-data-files=3, ...}".

Run the queries in references/metadata-tables.md and export the results, e.g.
  spark.sql("SELECT * FROM db.tbl.snapshots").toPandas().to_json("snap.json", orient="records")
  spark.sql("SELECT content, file_size_in_bytes, record_count FROM db.tbl.files").toPandas().to_json("files.json", orient="records")

Usage:
  profile_table.py --snapshots snap.json --files files.json \
                   [--partitions parts.json] [--manifests mans.json] \
                   [--target-mb 256] [--out profile.json]
"""
import argparse
import csv
import json
import re
import statistics as stats
import sys
from datetime import datetime, timezone

MB = 1024 * 1024
GB = 1024 * 1024 * 1024
SMALL_FILE_MB = 64


def load_rows(path):
    """Load a list of dict rows from JSON (array or NDJSON) or CSV."""
    with open(path, "r") as fh:
        text = fh.read().strip()
    if not text:
        return []
    if path.endswith(".csv"):
        return list(csv.DictReader(text.splitlines()))
    # JSON: try a single array/object, then newline-delimited.
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]


def parse_map(val):
    """Parse an Iceberg `summary`-style map: dict, JSON string, or Spark
    `{k=v, k2=v2}` toString form."""
    if val is None or val == "":
        return {}
    if isinstance(val, dict):
        return val
    s = str(val).strip()
    try:
        out = json.loads(s)
        if isinstance(out, dict):
            return out
    except json.JSONDecodeError:
        pass
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1]
    out = {}
    for part in re.split(r",\s*(?=[\w.-]+=)", s):
        if "=" in part:
            k, _, v = part.partition("=")
            out[k.strip()] = v.strip()
    return out


def to_float(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def to_int(v, default=None):
    f = to_float(v, None)
    return int(f) if f is not None else default


def parse_ts(v):
    """Parse committed_at as ISO-ish string or epoch millis/seconds → UTC datetime."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
        n = float(v)
        if n > 1e11:  # milliseconds
            n /= 1000.0
        return datetime.fromtimestamp(n, tz=timezone.utc)
    s = str(v).strip().replace("T", " ")
    s = re.sub(r"[+-]\d{2}:?\d{2}$", "", s).replace("Z", "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def get(row, *names):
    """First present, non-empty value among candidate column names."""
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return None


def classify_cadence(median_gap_sec):
    if median_gap_sec is None:
        return "unknown"
    if median_gap_sec < 60:
        return "streaming"
    if median_gap_sec < 900:
        return "micro-batch"
    if median_gap_sec < 6 * 3600:
        return "hourly-batch"
    return "batch"


def profile_files(rows, target_mb):
    data, deletes, pos_del, eq_del = [], 0, 0, 0
    data_records, pos_del_records, eq_del_records = 0, 0, 0
    for r in rows:
        content = to_int(get(r, "content"), 0)
        size = to_int(get(r, "file_size_in_bytes", "file_size"), 0) or 0
        record_count = to_int(get(r, "record_count"), 0) or 0
        if content == 0:
            data.append(size)
            data_records += record_count
        else:
            deletes += 1
            if content == 1:
                pos_del += 1
                pos_del_records += record_count
            elif content == 2:
                eq_del += 1
                eq_del_records += record_count
    out = {
        "data_files": len(data),
        "delete_files": deletes,
        "position_delete_files": pos_del,
        "equality_delete_files": eq_del,
        # Record-level delete pressure: fraction of live data rows affected.
        # Equality deletes are re-evaluated as a join on EVERY scan until compacted —
        # they are far more expensive than position deletes and need urgent attention.
        "data_records": data_records,
        "position_delete_records": pos_del_records,
        "equality_delete_records": eq_del_records,
    }
    total = len(data) + deletes
    out["delete_file_pct"] = round(deletes / total, 4) if total else 0.0
    if data_records > 0:
        out["eq_delete_pressure"] = round(eq_del_records / data_records, 4)
        out["pos_delete_pressure"] = round(pos_del_records / data_records, 4)
    if data:
        small = sum(1 for s in data if s < SMALL_FILE_MB * MB)
        out.update({
            "avg_mb": round(sum(data) / len(data) / MB, 1),
            "median_mb": round(stats.median(data) / MB, 1),
            "files_under_64mb": small,
            "files_under_64mb_pct": round(small / len(data), 4),
            "total_gb": round(sum(data) / GB, 3),
            "target_mb": target_mb,
            "needs_binpack": (sum(data) / len(data) / MB < SMALL_FILE_MB)
                             or (small / len(data) > 0.3),
        })
    return out


def profile_snapshots(rows):
    parsed = []
    for r in rows:
        parsed.append({
            "ts": parse_ts(get(r, "committed_at", "made_current_at")),
            "op": (get(r, "operation") or "unknown"),
            "summary": parse_map(get(r, "summary")),
        })
    parsed = [p for p in parsed if p["ts"]]
    parsed.sort(key=lambda p: p["ts"])

    op_mix = {}
    for p in parsed:
        op_mix[p["op"]] = op_mix.get(p["op"], 0) + 1

    gaps = [(parsed[i]["ts"] - parsed[i - 1]["ts"]).total_seconds()
            for i in range(1, len(parsed))]
    median_gap = stats.median(gaps) if gaps else None

    added_file_mb, files_per_commit, parts_per_commit = [], [], []
    for p in parsed:
        if p["op"] not in ("append", "overwrite"):
            continue
        s = p["summary"]
        nfiles = to_float(s.get("added-data-files"))
        nbytes = to_float(s.get("added-files-size"))
        nparts = to_float(s.get("changed-partition-count"))
        if nfiles and nfiles > 0:
            files_per_commit.append(nfiles)
            if nbytes is not None:
                added_file_mb.append(nbytes / nfiles / MB)
        if nparts is not None:
            parts_per_commit.append(nparts)

    median_parts = stats.median(parts_per_commit) if parts_per_commit else None
    median_files = stats.median(files_per_commit) if files_per_commit else None
    avg_added_mb = round(stats.mean(added_file_mb), 1) if added_file_mb else None
    # thin spread: each commit hits many partitions with few small files each.
    thin_spread = bool(median_parts and median_parts > 3 and avg_added_mb is not None
                       and avg_added_mb < SMALL_FILE_MB)

    # Delete rate — derived from snapshot summary keys, not from $files.
    # total-equality-deletes / total-position-deletes are running totals in the
    # latest snapshot. added-delete-files / added-equality-deletes accumulate
    # across all snapshots to give a rate.
    delete_commits = 0
    added_del_files = 0
    added_eq_records = 0
    added_pos_records = 0
    total_eq_from_latest = None
    total_pos_from_latest = None
    for p in parsed:
        s = p["summary"]
        n_del_files = to_int(s.get("added-delete-files"), 0) or 0
        n_eq = to_int(s.get("added-equality-deletes"), 0) or 0
        n_pos = to_int(s.get("added-position-deletes"), 0) or 0
        if n_del_files > 0:
            delete_commits += 1
        added_del_files += n_del_files
        added_eq_records += n_eq
        added_pos_records += n_pos
    if parsed:
        latest = parsed[-1]["summary"]
        total_eq_from_latest = to_int(latest.get("total-equality-deletes"))
        total_pos_from_latest = to_int(latest.get("total-position-deletes"))

    span_days = None
    delete_rate_per_day = None
    if len(parsed) >= 2:
        span_days = (parsed[-1]["ts"] - parsed[0]["ts"]).total_seconds() / 86400
        if span_days > 0:
            delete_rate_per_day = round(added_del_files / span_days, 2)

    return {
        "snapshot_count": len(parsed),
        "operation_mix": op_mix,
        "append_only_observed": set(op_mix) <= {"append"},
        "write_cadence": {
            "median_gap_sec": round(median_gap, 1) if median_gap is not None else None,
            "class": classify_cadence(median_gap),
        },
        "write_file_size": {
            "avg_added_file_mb": avg_added_mb,
            "median_files_per_commit": median_files,
            "buffers_to_target": bool(avg_added_mb and avg_added_mb >= SMALL_FILE_MB),
        },
        "partition_fanout": {
            "median_partitions_per_commit": median_parts,
            "thin_spread": thin_spread,
        },
        "delete_pattern": {
            "delete_commits": delete_commits,
            "added_delete_files_total": added_del_files,
            "added_equality_delete_records_total": added_eq_records,
            "added_position_delete_records_total": added_pos_records,
            "delete_rate_per_day": delete_rate_per_day,
            "total_equality_deletes_latest": total_eq_from_latest,
            "total_position_deletes_latest": total_pos_from_latest,
        },
        "first_commit": parsed[0]["ts"].isoformat() if parsed else None,
        "last_commit": parsed[-1]["ts"].isoformat() if parsed else None,
    }


def profile_partitions(rows):
    counts = [to_int(get(r, "record_count"), 0) or 0 for r in rows]
    fcounts = [to_int(get(r, "file_count"), 0) or 0 for r in rows]
    counts = [c for c in counts if c > 0]
    out = {"partition_count": len(rows)}
    if counts:
        out["skew_ratio"] = round(max(counts) / min(counts), 1)
    if fcounts:
        out["max_files_in_partition"] = max(fcounts)
    return out


def profile_manifests(rows):
    specs = {to_int(get(r, "partition_spec_id"), 0) for r in rows}
    return {"manifest_count": len(rows),
            "distinct_partition_specs": len(specs),
            "mixed_partition_specs": len(specs) > 1}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshots", required=True)
    ap.add_argument("--files", required=True)
    ap.add_argument("--partitions")
    ap.add_argument("--manifests")
    ap.add_argument("--target-mb", type=int, default=256)
    ap.add_argument("--out", default="-")
    args = ap.parse_args(argv)

    profile = {
        "files": profile_files(load_rows(args.files), args.target_mb),
        "snapshots": profile_snapshots(load_rows(args.snapshots)),
    }
    if args.partitions:
        profile["partitions"] = profile_partitions(load_rows(args.partitions))
    if args.manifests:
        profile["manifests"] = profile_manifests(load_rows(args.manifests))

    profile["flags"] = _flags(profile)

    text = json.dumps(profile, indent=2, default=str)
    if args.out == "-":
        print(text)
    else:
        with open(args.out, "w") as fh:
            fh.write(text)
        print(f"wrote {args.out}", file=sys.stderr)
    return 0


def _flags(p):
    """Top-level booleans the decision framework keys off."""
    f = p["files"]
    s = p["snapshots"]
    dp = s.get("delete_pattern", {})
    return {
        "needs_binpack": f.get("needs_binpack", False),
        "delete_pressure": f.get("delete_file_pct", 0) > 0.1,
        # Equality deletes are applied as a join on every scan until compacted.
        # Any significant equality delete pressure demands urgent compaction
        # regardless of query frequency — including GDPR-driven tables.
        "equality_delete_pressure": f.get("eq_delete_pressure", 0) > 0.05,
        # Delete files are accumulating over time (not a one-off historical state).
        "delete_accumulating": (dp.get("delete_rate_per_day") or 0) > 0.5,
        "thin_spread": s["partition_fanout"]["thin_spread"],
        "structural_small_files": not s["write_file_size"]["buffers_to_target"],
        "mutated": not s["append_only_observed"],
        "manifest_bloat": p.get("manifests", {}).get("manifest_count", 0) > 500,
        "mixed_specs": p.get("manifests", {}).get("mixed_partition_specs", False),
        "snapshot_bloat": s["snapshot_count"] > 1000,
    }


if __name__ == "__main__":
    raise SystemExit(main())
