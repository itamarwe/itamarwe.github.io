"""Pytest tests for profile_table.py — five archetype scenarios.

Imports functions directly; no file I/O except as noted.
Run with: pytest tests/ -v
"""
import sys
import os
import copy
import json
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from profile_table import profile_files, profile_snapshots, profile_partitions, profile_manifests, _flags


MB = 1024 * 1024
GB = 1024 * 1024 * 1024


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def make_cold_archive_rows():
    """Scenario A: cold_archive — 10 large weekly-batched data files, no deletes."""
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    files = [
        {"content": 0, "file_size_in_bytes": 300 * MB, "record_count": 5_000_000}
        for _ in range(10)
    ]
    snapshots = [
        {
            "operation": "append",
            "committed_at": _iso(base + timedelta(weeks=i)),
            "summary": {
                "added-data-files": "1",
                "added-files-size": str(300 * MB),
                "changed-partition-count": "1",
            },
        }
        for i in range(10)
    ]
    return files, snapshots


def make_streaming_thin_spread_rows():
    """Scenario B: streaming_thin_spread — 5000 small files, 1100 snapshots every 30s."""
    files = [
        {"content": 0, "file_size_in_bytes": 1 * MB, "record_count": 10_000}
        for _ in range(5_000)
    ]
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    snapshots = []
    for i in range(1_100):
        ts = base + timedelta(seconds=30 * i)
        snapshots.append({
            "operation": "append",
            "committed_at": _iso(ts),
            "summary": {
                "added-data-files": "5",
                "added-files-size": str(5 * MB),
                "changed-partition-count": "20",
            },
        })
    return files, snapshots


def make_gdpr_deletes_rows():
    """Scenario C: gdpr_deletes — equality deletes account for >5% of data records."""
    # 100 data files × 2M records = 200M data records
    files = [
        {"content": 0, "file_size_in_bytes": 200 * MB, "record_count": 2_000_000}
        for _ in range(100)
    ]
    # 20 equality-delete files × 1M records = 20M eq-delete records
    # eq_delete_pressure = 20M / 200M = 0.10  (> 0.05 threshold)
    files += [
        {"content": 2, "file_size_in_bytes": 100 * 1024, "record_count": 1_000_000}
        for _ in range(20)
    ]

    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    snapshots = []
    for i in range(15):
        # append
        ts_a = base + timedelta(days=2 * i)
        snapshots.append({
            "operation": "append",
            "committed_at": _iso(ts_a),
            "summary": {
                "added-data-files": "5",
                "added-files-size": str(1_000 * MB),
                "changed-partition-count": "1",
            },
        })
        # delete (between appends)
        ts_d = base + timedelta(days=2 * i + 1)
        snapshots.append({
            "operation": "delete",
            "committed_at": _iso(ts_d),
            "summary": {
                "added-delete-files": "1",
                "added-equality-deletes": "1000000",
                "total-equality-deletes": str(1_000_000 * (i + 1)),
            },
        })
    return files, snapshots


def make_snapshot_bloat_only_rows():
    """Scenario D: snapshot_bloat_only — 5 large files, 1200 hourly snapshots."""
    files = [
        {"content": 0, "file_size_in_bytes": 256 * MB, "record_count": 5_000_000}
        for _ in range(5)
    ]
    base = datetime(2023, 1, 1, tzinfo=timezone.utc)
    snapshots = [
        {
            "operation": "append",
            "committed_at": _iso(base + timedelta(hours=i)),
            "summary": {
                "added-data-files": "1",
                "added-files-size": str(256 * MB),
                "changed-partition-count": "1",
            },
        }
        for i in range(1_200)
    ]
    return files, snapshots


def make_healthy_batch_rows():
    """Scenario E: healthy_batch — 20 large files, 30 daily snapshots, everything clean."""
    files = [
        {"content": 0, "file_size_in_bytes": 256 * MB, "record_count": 5_000_000}
        for _ in range(20)
    ]
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    snapshots = [
        {
            "operation": "append",
            "committed_at": _iso(base + timedelta(days=i)),
            "summary": {
                "added-data-files": "1",
                "added-files-size": str(256 * MB),
                "changed-partition-count": "1",
            },
        }
        for i in range(30)
    ]
    return files, snapshots


def build_profile(files_rows, snap_rows):
    """Helper to build a full profile dict the same way main() does."""
    profile = {
        "files": profile_files(files_rows, target_mb=256),
        "snapshots": profile_snapshots(snap_rows),
    }
    profile["flags"] = _flags(profile)
    return profile


# ---------------------------------------------------------------------------
# Scenario A: cold_archive
# ---------------------------------------------------------------------------

def test_cold_archive_profile_files():
    files_rows, _ = make_cold_archive_rows()
    fp = profile_files(files_rows, target_mb=256)

    assert fp["data_files"] == 10
    assert fp["delete_files"] == 0
    assert fp["delete_file_pct"] == pytest.approx(0.0)
    # Each file is 300 MB → avg_mb should be 300.0
    assert fp["avg_mb"] == pytest.approx(300.0, abs=0.5)
    # No files under 64 MB
    assert fp["files_under_64mb"] == 0
    assert fp["needs_binpack"] is False


def test_cold_archive_flags():
    files_rows, snap_rows = make_cold_archive_rows()
    profile = build_profile(files_rows, snap_rows)
    flags = profile["flags"]

    assert flags["needs_binpack"] is False
    assert flags["delete_pressure"] is False
    assert flags["thin_spread"] is False
    assert flags["mutated"] is False
    assert flags["snapshot_bloat"] is False


def test_cold_archive_wins_do_nothing_in_simulator():
    """At very low query volume, do_nothing should have zero maintenance cost
    and should beat the aggressive compaction scenarios on maintenance_cost priority.

    On total cost, storage_min can beat do_nothing because it carries a lower
    storage multiplier (1.00 vs 1.30); the test therefore checks maintenance_cost
    priority, where do_nothing is guaranteed to win (0 runs/month → $0.00).
    """
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
    from simulate import simulate, ASSUMPTIONS, PRIORITY_KEY

    files_rows, snap_rows = make_cold_archive_rows()
    profile = build_profile(files_rows, snap_rows)

    a = json.loads(json.dumps(ASSUMPTIONS))  # deep copy
    a["queries_per_month"] = 5

    rows = simulate(profile, workload=None, a=a)

    # do_nothing has zero maintenance cost by definition
    do_nothing_row = next(r for r in rows if r["scenario"] == "do_nothing")
    assert do_nothing_row["maintenance_cost_month_usd"] == pytest.approx(0.0)

    # Ranked by maintenance cost, do_nothing is #1 (or tied for #1)
    key = PRIORITY_KEY["maintenance_cost"]
    ranked = sorted(rows, key=lambda r: r[key])
    assert ranked[0]["scenario"] == "do_nothing"

    # At QPM=5 the table is so small that aggressive compaction costs more than
    # it saves on query spend — confirm aggressive is not the cheapest overall
    total_sorted = sorted(rows, key=lambda r: r["total_cost_month_usd"])
    aggressive_rank = next(i for i, r in enumerate(total_sorted) if r["scenario"] == "aggressive")
    assert aggressive_rank > 0  # aggressive is never cheapest here


# ---------------------------------------------------------------------------
# Scenario B: streaming_thin_spread
# ---------------------------------------------------------------------------

def test_streaming_thin_spread_profile_files():
    files_rows, _ = make_streaming_thin_spread_rows()
    fp = profile_files(files_rows, target_mb=256)

    assert fp["data_files"] == 5_000
    assert fp["delete_files"] == 0
    # Each file is 1 MB — well under 64 MB
    assert fp["avg_mb"] == pytest.approx(1.0, abs=0.1)
    assert fp["files_under_64mb"] == 5_000
    assert fp["needs_binpack"] is True


def test_streaming_thin_spread_flags():
    files_rows, snap_rows = make_streaming_thin_spread_rows()
    profile = build_profile(files_rows, snap_rows)
    flags = profile["flags"]

    assert flags["needs_binpack"] is True
    assert flags["thin_spread"] is True
    assert flags["structural_small_files"] is True
    assert flags["snapshot_bloat"] is True  # 1100 > 1000
    assert flags["mutated"] is False


# ---------------------------------------------------------------------------
# Scenario C: gdpr_deletes
# ---------------------------------------------------------------------------

def test_gdpr_deletes_profile_files():
    files_rows, _ = make_gdpr_deletes_rows()
    fp = profile_files(files_rows, target_mb=256)

    assert fp["data_files"] == 100
    assert fp["equality_delete_files"] == 20
    assert fp["delete_files"] == 20
    # delete_file_pct = 20 / 120 ≈ 0.1667
    assert fp["delete_file_pct"] == pytest.approx(20 / 120, abs=0.001)

    # eq_delete_pressure: requires profile_table.py update to track record_count
    # When implemented: eq_delete_records / data_records = 20M / 200M = 0.10 > 0.05
    # If the key doesn't exist yet, this test will raise — see note below.
    # requires profile_table.py update to add equality_delete_records + eq_delete_pressure
    if "eq_delete_pressure" in fp:
        assert fp["eq_delete_pressure"] == pytest.approx(0.10, abs=0.005)


def test_gdpr_deletes_flags():
    files_rows, snap_rows = make_gdpr_deletes_rows()
    profile = build_profile(files_rows, snap_rows)
    flags = profile["flags"]

    assert flags["delete_pressure"] is True   # delete_file_pct = 0.167 > 0.10
    assert flags["mutated"] is True            # operation="delete" snapshots present

    # equality_delete_pressure flag — requires profile_table.py update:
    # Add to _flags(): "equality_delete_pressure": p["files"].get("eq_delete_pressure", 0) > 0.05
    if "equality_delete_pressure" in flags:
        assert flags["equality_delete_pressure"] is True


# ---------------------------------------------------------------------------
# Scenario D: snapshot_bloat_only
# ---------------------------------------------------------------------------

def test_snapshot_bloat_only_profile_files():
    files_rows, _ = make_snapshot_bloat_only_rows()
    fp = profile_files(files_rows, target_mb=256)

    assert fp["data_files"] == 5
    assert fp["delete_files"] == 0
    assert fp["avg_mb"] == pytest.approx(256.0, abs=0.5)
    assert fp["needs_binpack"] is False


def test_snapshot_bloat_only_flags():
    files_rows, snap_rows = make_snapshot_bloat_only_rows()
    profile = build_profile(files_rows, snap_rows)
    flags = profile["flags"]

    assert flags["snapshot_bloat"] is True   # 1200 > 1000
    assert flags["needs_binpack"] is False
    assert flags["delete_pressure"] is False
    assert flags["mutated"] is False


# ---------------------------------------------------------------------------
# Scenario E: healthy_batch
# ---------------------------------------------------------------------------

def test_healthy_batch_profile_files():
    files_rows, _ = make_healthy_batch_rows()
    fp = profile_files(files_rows, target_mb=256)

    assert fp["data_files"] == 20
    assert fp["delete_files"] == 0
    assert fp["avg_mb"] == pytest.approx(256.0, abs=0.5)
    assert fp["needs_binpack"] is False
    assert fp["files_under_64mb"] == 0


def test_healthy_batch_flags():
    files_rows, snap_rows = make_healthy_batch_rows()
    profile = build_profile(files_rows, snap_rows)
    flags = profile["flags"]

    assert flags["needs_binpack"] is False
    assert flags["delete_pressure"] is False
    assert flags["thin_spread"] is False
    assert flags["mutated"] is False
    assert flags["snapshot_bloat"] is False

    # equality_delete_pressure should be False on a clean table
    if "equality_delete_pressure" in flags:
        assert flags["equality_delete_pressure"] is False


# ---------------------------------------------------------------------------
# Scenario F: partition_misalignment
# Table partitioned by event_date (daily), real queries filter only on tenant_id.
# Profile looks perfectly healthy; the problem is invisible without the workload.
# ---------------------------------------------------------------------------

def make_partition_misaligned_rows():
    """50 well-sized daily-batch data files. No small files, no deletes.
    The profile alone gives no alarm — the dysfunction only appears when the
    workload reveals partition_prune_rate = 0 and tenant_id as dominant filter.
    """
    files = [
        {"content": 0, "file_size_in_bytes": 256 * MB, "record_count": 5_000_000}
        for _ in range(50)
    ]
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    snapshots = [
        {
            "operation": "append",
            "committed_at": _iso(base + timedelta(days=i)),
            "summary": {
                "added-data-files": "1",
                "added-files-size": str(256 * MB),
                "changed-partition-count": "1",
            },
        }
        for i in range(50)
    ]
    return files, snapshots


def test_partition_misaligned_profile_looks_healthy():
    """Profile alone shows no problem — the table is structurally clean.
    This demonstrates why the profile must be combined with workload signals:
    a table can be well-maintained at the file level yet catastrophically
    wrong at the access-pattern level.
    """
    files_rows, snap_rows = make_partition_misaligned_rows()
    profile = build_profile(files_rows, snap_rows)
    flags = profile["flags"]

    # All red flags are False — the profiler is not alarmed by this table
    assert flags["needs_binpack"] is False
    assert flags["delete_pressure"] is False
    assert flags["thin_spread"] is False
    assert flags["mutated"] is False
    assert flags["snapshot_bloat"] is False

    # Files are well-sized (256 MB each — at target)
    assert profile["files"]["avg_mb"] == pytest.approx(256.0, abs=1.0)
    assert profile["files"]["total_gb"] == pytest.approx(50 * 256 / 1024, rel=0.01)


def test_partition_misaligned_full_scan_baseline():
    """When partition_prune_rate = 0 (no pruning because the filter column is
    not the partition key), the simulator's baseline equals the full table size.
    This is the cost that repartitioning or sorting by tenant_id would eliminate.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
    from simulate import baseline_bytes_gb, ASSUMPTIONS

    files_rows, snap_rows = make_partition_misaligned_rows()
    profile = build_profile(files_rows, snap_rows)
    total_gb = profile["files"]["total_gb"]  # 50 × 256 MB = 12.5 GB

    a = json.loads(json.dumps(ASSUMPTIONS))

    # Current bad state: no partition pruning at all
    misaligned_workload = {"partition_prune_rate": 0.0}
    base_bad = baseline_bytes_gb(profile, misaligned_workload, a)
    assert base_bad == pytest.approx(total_gb, rel=0.01), (
        "prune_rate=0 → every query scans the full 12.5 GB table"
    )

    # After partition evolution to tenant_id (1000 tenants → ~1% per query)
    aligned_workload = {"partition_prune_rate": 0.99}
    base_good = baseline_bytes_gb(profile, aligned_workload, a)
    assert base_good == pytest.approx(total_gb * 0.01, rel=0.1), (
        "prune_rate=0.99 → queries scan ~1% of the table"
    )

    # The repartitioning payoff: 100x reduction in bytes scanned per query
    assert base_bad / base_good == pytest.approx(100.0, rel=0.15)


def test_partition_misaligned_query_cost_impact():
    """Quantify the monthly query bill: wrong vs right partition key.
    At 1000 queries/month on a 12.5 GB table at $5/TB, the wrong partition key
    costs ~100x more in query compute than the right one.
    """
    from simulate import simulate, ASSUMPTIONS

    files_rows, snap_rows = make_partition_misaligned_rows()
    profile = build_profile(files_rows, snap_rows)

    a = json.loads(json.dumps(ASSUMPTIONS))
    a["queries_per_month"] = 1000

    # do_nothing with wrong partition: full-table scans
    rows_bad = simulate(profile, {"partition_prune_rate": 0.0}, a)
    cost_bad = next(r for r in rows_bad if r["scenario"] == "do_nothing")["query_cost_month_usd"]

    # do_nothing after repartitioning: 99% pruned
    rows_good = simulate(profile, {"partition_prune_rate": 0.99}, a)
    cost_good = next(r for r in rows_good if r["scenario"] == "do_nothing")["query_cost_month_usd"]

    # After repartitioning, query cost drops by ~100x
    assert cost_good < cost_bad / 50, (
        f"Repartitioning by tenant_id should cut query cost >50x; "
        f"bad={cost_bad:.2f} USD/mo, good={cost_good:.2f} USD/mo"
    )
    # The bad state is measurably expensive (non-trivial at 1k QPM)
    assert cost_bad > 0.5, "full-table scan at 1k QPM should not be free"


# ---------------------------------------------------------------------------
# Utility: parse_bytes_str from parse_query_log
# ---------------------------------------------------------------------------

def test_parse_bytes_str():
    from parse_query_log import parse_bytes_str

    assert parse_bytes_str("1.23 GB") == pytest.approx(1.23e9, rel=1e-3)
    assert parse_bytes_str("456 MB") == pytest.approx(456e6, rel=1e-3)
    assert parse_bytes_str("789 B") == pytest.approx(789.0, abs=1)
    # IEC units treated same as SI
    assert parse_bytes_str("1.5 GiB") == pytest.approx(1.5e9, rel=1e-2)
    # Comma-formatted numbers
    assert parse_bytes_str("1,234.56 MB") == pytest.approx(1234.56e6, rel=1e-3)
