#!/usr/bin/env python3
"""Generate fixture files (profile.json, workload.json, simulate_output.txt) for each
benchmark scenario. Uses the same data builders as the pytest suite so fixtures stay
in sync with the tests.

Run once (or whenever fixture data changes):
    python tests/skill_benchmark/generate_fixtures.py

Outputs into tests/skill_benchmark/fixtures/<scenario>/.
"""
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

SKILL_DIR = Path(__file__).parent.parent.parent
SCRIPTS = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).parent.parent))  # for test_profiler helpers

from profile_table import profile_files, profile_snapshots, _flags
from simulate import simulate, ASSUMPTIONS, PRIORITY_KEY, render_table

FIXTURE_DIR = Path(__file__).parent / "fixtures"
MB = 1024 * 1024
GB = 1024 * 1024 * 1024


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_profile(files_rows, snap_rows):
    p = {
        "files": profile_files(files_rows, target_mb=256),
        "snapshots": profile_snapshots(snap_rows),
    }
    p["flags"] = _flags(p)
    return p


def run_simulate(profile, workload, qpm, priority="total"):
    import copy
    a = copy.deepcopy(ASSUMPTIONS)
    a["queries_per_month"] = qpm
    rows = simulate(profile, workload, a)
    key = PRIORITY_KEY[priority]
    ranked = sorted(rows, key=lambda r: (r[key] is None, r[key]))
    winner = ranked[0]
    buf = io.StringIO()
    buf.write(f"queries/month = {qpm}   priority = {priority}\n\n")
    buf.write("SCENARIO COMPARISON (directional estimates, not a benchmark):\n\n")
    buf.write(render_table(rows))
    buf.write(f"\n\n>>> Optimizing for '{priority}': recommend '{winner['scenario']}' "
              f"({key} = {winner[key]}).\n")
    if winner["scenario"] == "do_nothing":
        buf.write("    NOTE: doing nothing wins — maintenance compute would cost more "
                  "than it saves at this query volume.\n")
    return buf.getvalue()


def write_fixture(name, profile, workload, simulate_output):
    d = FIXTURE_DIR / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "profile.json").write_text(json.dumps(profile, indent=2, default=str))
    (d / "workload.json").write_text(json.dumps(workload, indent=2))
    (d / "simulate_output.txt").write_text(simulate_output)
    print(f"  wrote {name}/")


# ── Scenario A: cold_archive ──────────────────────────────────────────────────

def gen_cold_archive():
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    files = [
        {"content": 0, "file_size_in_bytes": 300 * MB, "record_count": 5_000_000}
        for _ in range(10)
    ]
    snaps = [
        {
            "operation": "append",
            "committed_at": _iso(base + timedelta(weeks=i)),
            "summary": {"added-data-files": "1", "added-files-size": str(300 * MB),
                        "changed-partition-count": "1"},
        }
        for i in range(10)
    ]
    profile = build_profile(files, snaps)
    workload = {
        "table": "prod.archive.user_events",
        "matched_query_count": 3,
        "filter_columns": [{"column": "event_date", "count": 3, "dominant": "range"}],
        "range_cols": ["event_date"],
        "equality_cols": [],
        "partition_prune_rate": 0.8,
        "selectivity": None,
        "parser": "sqlglot",
    }
    sim = run_simulate(profile, workload, qpm=5, priority="total")
    write_fixture("cold_archive", profile, workload, sim)


# ── Scenario B: streaming_thin_spread ─────────────────────────────────────────

def gen_streaming_thin_spread():
    files = [
        {"content": 0, "file_size_in_bytes": 1 * MB, "record_count": 10_000}
        for _ in range(5_000)
    ]
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    snaps = [
        {
            "operation": "append",
            "committed_at": _iso(base + timedelta(seconds=30 * i)),
            "summary": {"added-data-files": "5", "added-files-size": str(5 * MB),
                        "changed-partition-count": "20"},
        }
        for i in range(1_100)
    ]
    profile = build_profile(files, snaps)
    workload = {
        "table": "prod.events.stream",
        "scans_analyzed": 200,
        "filter_columns": [
            {"column": "tenant_id", "count": 180, "dominant": "equality"},
            {"column": "event_time", "count": 150, "dominant": "range"},
        ],
        "equality_cols": ["tenant_id"],
        "range_cols": ["event_time"],
        "partition_prune_rate": 0.4,
        "selectivity": {"median_bytes_scanned": int(4.8 * GB), "source": "spark-sql-metrics"},
        "parser": "spark-eventlog-regex",
    }
    sim = run_simulate(profile, workload, qpm=50_000, priority="query_cost")
    write_fixture("streaming_thin_spread", profile, workload, sim)


# ── Scenario C: gdpr_deletes ──────────────────────────────────────────────────

def gen_gdpr_deletes():
    files = (
        [{"content": 0, "file_size_in_bytes": 200 * MB, "record_count": 2_000_000}
         for _ in range(100)] +
        [{"content": 2, "file_size_in_bytes": 100 * 1024, "record_count": 1_000_000}
         for _ in range(20)]
    )
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    snaps = []
    for i in range(15):
        snaps.append({
            "operation": "append",
            "committed_at": _iso(base + timedelta(days=2 * i)),
            "summary": {"added-data-files": "5", "added-files-size": str(1_000 * MB),
                        "changed-partition-count": "1"},
        })
        snaps.append({
            "operation": "delete",
            "committed_at": _iso(base + timedelta(days=2 * i + 1)),
            "summary": {"added-delete-files": "1", "added-equality-deletes": "1000000",
                        "total-equality-deletes": str(1_000_000 * (i + 1))},
        })
    profile = build_profile(files, snaps)
    workload = {
        "table": "prod.compliance.user_data",
        "matched_query_count": 30,
        "filter_columns": [
            {"column": "user_id", "count": 28, "dominant": "equality"},
            {"column": "event_date", "count": 10, "dominant": "range"},
        ],
        "equality_cols": ["user_id"],
        "range_cols": ["event_date"],
        "partition_prune_rate": 0.6,
        "selectivity": {"median_bytes_scanned": int(8 * GB)},
        "parser": "sqlglot",
    }
    sim = run_simulate(profile, workload, qpm=500, priority="query_cost")
    write_fixture("gdpr_deletes", profile, workload, sim)


# ── Scenario D: partition_misalignment ────────────────────────────────────────

def gen_partition_misalignment():
    files = [
        {"content": 0, "file_size_in_bytes": 256 * MB, "record_count": 5_000_000}
        for _ in range(50)
    ]
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    snaps = [
        {
            "operation": "append",
            "committed_at": _iso(base + timedelta(days=i)),
            "summary": {"added-data-files": "1", "added-files-size": str(256 * MB),
                        "changed-partition-count": "1"},
        }
        for i in range(50)
    ]
    profile = build_profile(files, snaps)
    workload = {
        "table": "prod.analytics.events",
        "scans_analyzed": 500,
        "filter_columns": [
            {"column": "tenant_id", "count": 490, "dominant": "equality"},
            {"column": "event_date", "count": 200, "dominant": "range"},
        ],
        "equality_cols": ["tenant_id"],
        "range_cols": ["event_date"],
        # The critical signal: zero partition pruning because tenant_id is not
        # the partition column (event_date is), so every query scans the full table.
        "partition_prune_rate": 0.0,
        "selectivity": {"median_bytes_scanned": int(12.5 * GB), "source": "spark-sql-metrics"},
        "parser": "spark-eventlog-regex",
    }
    sim = run_simulate(profile, workload, qpm=1_000, priority="query_cost")
    write_fixture("partition_misalignment", profile, workload, sim)


# ── Scenario E: snapshot_bloat_only ──────────────────────────────────────────

def gen_snapshot_bloat_only():
    files = [
        {"content": 0, "file_size_in_bytes": 256 * MB, "record_count": 5_000_000}
        for _ in range(5)
    ]
    base = datetime(2023, 1, 1, tzinfo=timezone.utc)
    snaps = [
        {
            "operation": "append",
            "committed_at": _iso(base + timedelta(hours=i)),
            "summary": {"added-data-files": "1", "added-files-size": str(256 * MB),
                        "changed-partition-count": "1"},
        }
        for i in range(1_200)
    ]
    profile = build_profile(files, snaps)
    workload = {
        "table": "prod.reports.daily_summary",
        "matched_query_count": 20,
        "filter_columns": [{"column": "report_date", "count": 20, "dominant": "range"}],
        "range_cols": ["report_date"],
        "equality_cols": [],
        "partition_prune_rate": 0.9,
        "selectivity": None,
        "parser": "sqlglot",
    }
    sim = run_simulate(profile, workload, qpm=200, priority="storage")
    write_fixture("snapshot_bloat_only", profile, workload, sim)


if __name__ == "__main__":
    print("Generating fixtures...")
    gen_cold_archive()
    gen_streaming_thin_spread()
    gen_gdpr_deletes()
    gen_partition_misalignment()
    gen_snapshot_bloat_only()
    print("Done.")
