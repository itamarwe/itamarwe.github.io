#!/usr/bin/env python3
"""Simulate maintenance scenarios for an Iceberg table across four cost axes:
query latency, query cost, maintenance cost, and storage cost.

This is a TRANSPARENT, directional model — not a benchmark. It is driven by the
table's real numbers (from profile.json / workload.json) and a set of named
assumptions that are printed with every run and overridable via --assumptions.
Treat the outputs as order-of-magnitude comparisons, then replace the heuristic
factors (especially the per-scenario `scan_fraction`) with measured values.

Usage:
  simulate.py --profile profile.json [--workload workload.json]
              [--queries-per-month N] [--assumptions a.json]
              [--priority total|query_cost|latency|maintenance_cost|storage]
"""
import argparse
import json

# --- Named assumptions (override any subset via --assumptions JSON) ----------
ASSUMPTIONS = {
    "scan_price_per_tb_usd": 5.00,        # price per TB scanned (e.g. Athena-class)
    "compaction_price_per_tb_usd": 5.00,  # compute price per TB rewritten
    "storage_price_per_gb_month_usd": 0.023,  # object storage (S3 standard-class)
    "scan_throughput_gb_s": 2.0,          # effective scan throughput for latency proxy
    "queries_per_month": 1000,            # overridden by --queries-per-month / workload
    "assumed_prune_rate": 0.5,            # if no measured bytes-scanned, scan (1-this) of table
    # Per-scenario fraction of the BASELINE bytes a typical query scans afterward.
    # These are heuristics — the single most important thing to replace with
    # measured numbers from your own EXPLAIN ANALYZE / query stats.
    "scan_fraction": {
        "do_nothing": 1.00,
        "light": 0.90,          # fewer/larger files: less planning + open cost
        "targeted_sort": 0.25,  # dominant filter column clustered
        "aggressive": 0.15,     # sort/z-order + bloom on point lookups
        "storage_min": 0.95,
    },
    # Storage multiplier vs current live size (snapshot/bloom/retention overhead).
    "storage_multiplier": {
        "do_nothing": 1.30,     # unexpired snapshots accumulate copies
        "light": 1.10,
        "targeted_sort": 1.10,
        "aggressive": 1.20,     # bloom filters + more frequent snapshots
        "storage_min": 1.00,    # aggressive expiry, minimal retention
    },
    # Maintenance runs per month and what fraction of the table each run rewrites.
    "runs_per_month": {
        "do_nothing": 0, "light": 4, "targeted_sort": 4,
        "aggressive": 30, "storage_min": 1,
    },
    # "small" => only small-file bytes; "full" => whole table each run.
    "rewrite_scope": {
        "do_nothing": "none", "light": "small", "targeted_sort": "full",
        "aggressive": "full", "storage_min": "small",
    },
}

SCENARIOS = ["do_nothing", "light", "targeted_sort", "aggressive", "storage_min"]
GB_PER_TB = 1024.0


def deep_update(base, override):
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_update(base[k], v)
        else:
            base[k] = v
    return base


def baseline_bytes_gb(profile, workload, a):
    """Bytes a typical query scans today, in GB."""
    if workload:
        sel = workload.get("selectivity") or {}
        if sel.get("median_bytes_scanned"):
            return sel["median_bytes_scanned"] / (1024 ** 3)
    total_gb = profile.get("files", {}).get("total_gb", 0.0)
    prune = a["assumed_prune_rate"]
    if workload and workload.get("partition_prune_rate") is not None:
        prune = workload["partition_prune_rate"]
    return total_gb * (1.0 - prune)


def small_file_gb(profile):
    f = profile.get("files", {})
    return f.get("total_gb", 0.0) * f.get("files_under_64mb_pct", 0.0)


def simulate(profile, workload, a):
    total_gb = profile.get("files", {}).get("total_gb", 0.0)
    base_gb = max(baseline_bytes_gb(profile, workload, a), 0.0)
    small_gb = small_file_gb(profile)
    qpm = a["queries_per_month"]
    rows = []
    for s in SCENARIOS:
        scan_gb = base_gb * a["scan_fraction"][s]
        query_cost = scan_gb / GB_PER_TB * a["scan_price_per_tb_usd"] * qpm

        scope = a["rewrite_scope"][s]
        rewrite_gb = {"none": 0.0, "small": small_gb, "full": total_gb}[scope]
        runs = a["runs_per_month"][s]
        maint_cost = rewrite_gb / GB_PER_TB * a["compaction_price_per_tb_usd"] * runs

        storage_gb = total_gb * a["storage_multiplier"][s]
        storage_cost = storage_gb * a["storage_price_per_gb_month_usd"]

        latency_s = scan_gb / a["scan_throughput_gb_s"] if a["scan_throughput_gb_s"] else None

        rows.append({
            "scenario": s,
            "bytes_scanned_per_query_gb": round(scan_gb, 3),
            "query_latency_s": round(latency_s, 3) if latency_s is not None else None,
            "query_cost_month_usd": round(query_cost, 2),
            "maintenance_cost_month_usd": round(maint_cost, 2),
            "storage_cost_month_usd": round(storage_cost, 2),
            "total_cost_month_usd": round(query_cost + maint_cost + storage_cost, 2),
        })
    return rows


PRIORITY_KEY = {
    "total": "total_cost_month_usd",
    "query_cost": "query_cost_month_usd",
    "latency": "query_latency_s",
    "maintenance_cost": "maintenance_cost_month_usd",
    "storage": "storage_cost_month_usd",
}


def render_table(rows):
    cols = [("scenario", 14), ("bytes_scanned_per_query_gb", 12),
            ("query_latency_s", 11), ("query_cost_month_usd", 12),
            ("maintenance_cost_month_usd", 14), ("storage_cost_month_usd", 12),
            ("total_cost_month_usd", 12)]
    head = {"scenario": "scenario", "bytes_scanned_per_query_gb": "scan GB/q",
            "query_latency_s": "latency s", "query_cost_month_usd": "query $/mo",
            "maintenance_cost_month_usd": "maint $/mo",
            "storage_cost_month_usd": "storage $/mo",
            "total_cost_month_usd": "total $/mo"}
    line = lambda vals: "  ".join(str(v).ljust(w) for v, w in zip(vals, [w for _, w in cols]))
    out = [line([head[c] for c, _ in cols]),
           line(["-" * w for _, w in cols])]
    for r in rows:
        out.append(line([r[c] for c, _ in cols]))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--workload")
    ap.add_argument("--assumptions", help="JSON file overriding any assumptions")
    ap.add_argument("--queries-per-month", type=int)
    ap.add_argument("--priority", default="total", choices=list(PRIORITY_KEY))
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = ap.parse_args(argv)

    a = json.loads(json.dumps(ASSUMPTIONS))  # deep copy
    if args.assumptions:
        with open(args.assumptions) as fh:
            deep_update(a, json.load(fh))
    if args.queries_per_month is not None:
        a["queries_per_month"] = args.queries_per_month

    with open(args.profile) as fh:
        profile = json.load(fh)
    workload = None
    if args.workload:
        with open(args.workload) as fh:
            workload = json.load(fh)

    rows = simulate(profile, workload, a)
    key = PRIORITY_KEY[args.priority]
    ranked = sorted(rows, key=lambda r: (r[key] is None, r[key]))
    winner = ranked[0]

    if args.json:
        print(json.dumps({"assumptions": a, "scenarios": rows,
                          "priority": args.priority,
                          "recommended": winner["scenario"]}, indent=2))
        return 0

    print("ASSUMPTIONS (override with --assumptions; replace scan_fraction with measured values):")
    print(json.dumps(a, indent=2))
    print(f"\nqueries/month = {a['queries_per_month']}   priority = {args.priority}")
    print("\nSCENARIO COMPARISON (directional estimates, not a benchmark):\n")
    print(render_table(rows))
    print(f"\n>>> Optimizing for '{args.priority}': recommend '{winner['scenario']}' "
          f"({key} = {winner[key]}).")
    print("    Re-run with a different --priority to see the trade-off shift.")
    if winner["scenario"] == "do_nothing":
        print("    NOTE: doing nothing wins here — maintenance compute would cost more\n"
              "    than it saves at this query volume. Pay at query time.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
