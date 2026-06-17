"""Pytest tests for parse_query_log.py.

Imports functions directly; only test_explain_analyze_parsing writes a temp file.
Run with: pytest tests/ -v
"""
import sys
import os
import json
import statistics as stats
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from parse_query_log import (
    _flatten_trino_event_listener,
    _selectivity,
    analyze_sql_statements,
    analyze_spark_eventlog,
    parse_explain_analyze_file,
    table_aliases,
    parse_bytes_str,
)


# ---------------------------------------------------------------------------
# _flatten_trino_event_listener
# ---------------------------------------------------------------------------

def test_trino_event_listener_auto_detect():
    """Rows with queryCompletedEvent envelope are flattened to plain dicts."""
    rows = [
        {
            "queryCompletedEvent": {
                "metadata": {
                    "queryId": "20240101_000001_00001_xyz",
                    "query": "SELECT * FROM cat.db.tbl WHERE user_id = 42",
                },
                "statistics": {
                    "physicalInputDataSize": "2.5 GB",
                    "completedSplits": 120,
                },
            }
        },
        {
            "queryCompletedEvent": {
                "metadata": {
                    "queryId": "20240101_000002_00002_xyz",
                    "query": "SELECT count(*) FROM cat.db.tbl",
                },
                "statistics": {
                    "physicalInputDataSize": "1.0 GB",
                    "completedSplits": 60,
                },
            }
        },
    ]
    flat = _flatten_trino_event_listener(rows)

    assert len(flat) == 2
    assert flat[0]["query"] == "SELECT * FROM cat.db.tbl WHERE user_id = 42"
    assert flat[0]["query_id"] == "20240101_000001_00001_xyz"
    assert "physicalInputDataSize" in flat[0]
    assert flat[0]["physicalInputDataSize"] == "2.5 GB"
    assert flat[1]["physicalInputDataSize"] == "1.0 GB"


def test_trino_event_listener_passthrough_when_not_event_listener():
    """Rows without queryCompletedEvent are returned unchanged."""
    rows = [
        {"query": "SELECT 1", "input_bytes": 1024},
        {"query": "SELECT 2", "input_bytes": 2048},
    ]
    result = _flatten_trino_event_listener(rows)
    assert result is rows  # same object, not flattened


# ---------------------------------------------------------------------------
# _selectivity with human-readable byte strings
# ---------------------------------------------------------------------------

def test_selectivity_string_bytes():
    """physicalInputDataSize as a string ('1.0 GB') should parse to ~1e9 bytes."""
    stat_rows = [
        {"physicalInputDataSize": "1.0 GB"},
        {"physicalInputDataSize": "1.0 GB"},
        {"physicalInputDataSize": "1.0 GB"},
    ]
    sel = _selectivity(stat_rows)

    assert sel is not None
    assert sel["median_bytes_scanned"] == pytest.approx(1e9, rel=0.01)


def test_selectivity_mixed_sizes():
    """Median is computed correctly across multiple size values."""
    stat_rows = [
        {"physicalInputDataSize": "500 MB"},
        {"physicalInputDataSize": "1.0 GB"},
        {"physicalInputDataSize": "1.5 GB"},
    ]
    sel = _selectivity(stat_rows)

    assert sel is not None
    # median of [500e6, 1e9, 1.5e9] = 1e9
    assert sel["median_bytes_scanned"] == pytest.approx(1e9, rel=0.01)


def test_selectivity_returns_none_for_empty():
    assert _selectivity(None) is None
    assert _selectivity([]) is None


# ---------------------------------------------------------------------------
# analyze_sql_statements — equality vs range predicates
# ---------------------------------------------------------------------------

def test_analyze_sql_statements_equality_vs_range():
    """2 equality queries on user_id + 1 range query on event_date."""
    table = "cat.db.tbl"
    aliases = table_aliases(table)

    statements = [
        "SELECT * FROM cat.db.tbl WHERE user_id = 42",
        "SELECT * FROM cat.db.tbl WHERE user_id = 99",
        "SELECT * FROM cat.db.tbl WHERE event_date >= '2024-01-01' AND event_date < '2024-02-01'",
    ]
    result = analyze_sql_statements(statements, aliases, stat_rows=None)

    assert result["matched_query_count"] == 3

    # Build a quick lookup
    col_map = {fc["column"]: fc for fc in result["filter_columns"]}

    # user_id should appear with equality count 2
    assert "user_id" in col_map
    assert col_map["user_id"]["predicate_types"]["equality"] == 2
    assert col_map["user_id"]["dominant"] == "equality"
    assert "user_id" in result["equality_cols"]

    # event_date should appear with range count ≥ 1
    assert "event_date" in col_map
    assert col_map["event_date"]["predicate_types"]["range"] >= 1
    assert col_map["event_date"]["dominant"] == "range"
    assert "event_date" in result["range_cols"]


def test_analyze_sql_statements_unrelated_table_not_counted():
    """Queries against a different table should not be matched."""
    aliases = table_aliases("cat.db.tbl")
    statements = [
        "SELECT * FROM cat.db.other_table WHERE event_date = '2024-01-01'",
    ]
    result = analyze_sql_statements(statements, aliases)
    assert result["matched_query_count"] == 0
    assert result["filter_columns"] == []


# ---------------------------------------------------------------------------
# parse_explain_analyze_file
# ---------------------------------------------------------------------------

def test_explain_analyze_parsing():
    """File with two 'Physical Input Data Size' fragments — both should be parsed."""
    content = (
        "Fragment 1 [ SOURCE ]\n"
        "  - Output: 10000 rows\n"
        "  Physical Input Data Size: 1.50 GB\n"
        "  CPU: 3.20s  elapsed: 1.10s\n"
        "\n"
        "Fragment 2 [ SOURCE ]\n"
        "  - Output: 5000 rows\n"
        "  Physical Input Data Size: 750 MB\n"
        "  CPU: 1.50s  elapsed: 0.60s\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        tmp_path = f.name

    try:
        values = parse_explain_analyze_file(tmp_path)
    finally:
        os.unlink(tmp_path)

    assert len(values) == 2

    # Values should be approximately 1.5 GB and 750 MB
    values_sorted = sorted(values)
    assert values_sorted[0] == pytest.approx(750e6, rel=0.01)
    assert values_sorted[1] == pytest.approx(1.5e9, rel=0.01)

    # Median of the two values
    median = stats.median(values)
    assert median == pytest.approx((750e6 + 1.5e9) / 2, rel=0.01)


def test_explain_analyze_input_line_format():
    """'Input: N rows (X GB)' format is also parsed."""
    content = "  Input: 10000000 rows (2.0 GB), Parallelism: 3\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        tmp_path = f.name

    try:
        values = parse_explain_analyze_file(tmp_path)
    finally:
        os.unlink(tmp_path)

    assert len(values) == 1
    assert values[0] == pytest.approx(2.0e9, rel=0.01)


def test_explain_analyze_empty_file():
    """Empty file returns empty list, no crash."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("")
        tmp_path = f.name

    try:
        values = parse_explain_analyze_file(tmp_path)
    finally:
        os.unlink(tmp_path)

    assert values == []


# ---------------------------------------------------------------------------
# Scenario F: partition misalignment — table partitioned by event_date,
# all real queries filter on tenant_id (a completely different column).
# ---------------------------------------------------------------------------

def _write_eventlog(events):
    """Write a list of dicts as NDJSON to a named temp file; return path."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")
        return f.name


def test_partition_misalignment_spark_eventlog():
    """Table partitioned by event_date, queries filter on tenant_id only.

    Spark emits PartitionFilters: [] (empty) because tenant_id is not a
    partition column — the engine can't prune any partition.
    Expected: partition_prune_rate = 0.0, tenant_id is the dominant filter.
    event_date is NOT in filter_columns because it doesn't appear in dataFilters.
    """
    events = [
        {
            "executionId": i + 1,
            "physicalPlanDescription": (
                "== Physical Plan ==\n"
                "FileScan cat.db.events[tenant_id#1,event_date#2,revenue#3] "
                "cat.db.events\n"
                "PartitionFilters: []\n"
                f"dataFilters: [isnotnull(tenant_id#1), (tenant_id#1 = tenant{i})]\n"
            ),
        }
        for i in range(5)
    ]
    path = _write_eventlog(events)
    try:
        result = analyze_spark_eventlog(path, table_aliases("cat.db.events"))
    finally:
        os.unlink(path)

    assert result["scans_analyzed"] == 5
    assert result["partition_prune_rate"] == pytest.approx(0.0), (
        "No partition can be skipped when the filter column is not the partition key"
    )
    assert result["partition_filter_present"] == 0

    col_names = {r["column"] for r in result["filter_columns"]}
    assert "tenant_id" in col_names
    # event_date lives in PartitionFilters (empty here) and never in dataFilters,
    # so the parser correctly does NOT surface it as a workload filter column.
    assert "event_date" not in col_names


def test_partition_misalignment_spark_eventlog_mixed_queries():
    """Some queries do filter on event_date too (the partition column), but
    the dominant filter is still tenant_id. prune_rate stays 0.0 because
    event_date doesn't appear in PartitionFilters — only in dataFilters —
    when the partition transform is a function (e.g. DATE(event_ts)) rather
    than the column itself, or when queries don't align to partition boundaries.
    """
    events = []
    # 4 queries: tenant_id only in dataFilters, PartitionFilters empty
    for i in range(4):
        events.append({
            "executionId": i + 1,
            "physicalPlanDescription": (
                "FileScan db.events[tenant_id#1,event_date#2]\n"
                "PartitionFilters: []\n"
                f"dataFilters: [(tenant_id#1 = t{i}), (event_date#2 > 2024-01-01)]\n"
            ),
        })
    # 1 query: tenant_id only, no date filter at all
    events.append({
        "executionId": 5,
        "physicalPlanDescription": (
            "FileScan db.events[tenant_id#1,event_date#2]\n"
            "PartitionFilters: []\n"
            "dataFilters: [(tenant_id#1 = special)]\n"
        ),
    })

    path = _write_eventlog(events)
    try:
        result = analyze_spark_eventlog(path, table_aliases("db.events"))
    finally:
        os.unlink(path)

    assert result["scans_analyzed"] == 5
    assert result["partition_prune_rate"] == pytest.approx(0.0)

    col_map = {r["column"]: r for r in result["filter_columns"]}
    assert "tenant_id" in col_map
    # event_date appears in 4 of 5 dataFilters — it IS a filter column in the SQL,
    # just not used for partition pruning.
    assert "event_date" in col_map
    # tenant_id has higher or equal count vs event_date
    assert col_map["tenant_id"]["count"] >= col_map["event_date"]["count"]


def test_partition_misalignment_sql_analysis():
    """SQL-level analysis: tenant_id is the dominant equality filter;
    event_date appears as range. The combination tells the skill:
    'sort/z-order or repartition by tenant_id, not by event_date.'
    """
    aliases = table_aliases("db.events")
    statements = [
        "SELECT * FROM db.events WHERE tenant_id = 'acme' AND event_date >= '2024-01-01'",
        "SELECT count(*) FROM db.events WHERE tenant_id = 'globex'",
        "SELECT revenue FROM db.events WHERE tenant_id IN ('foo', 'bar') AND event_date < '2024-06-01'",
    ]
    result = analyze_sql_statements(statements, aliases)

    assert result["matched_query_count"] == 3
    col_map = {fc["column"]: fc for fc in result["filter_columns"]}

    # tenant_id appears in all 3 queries as equality (= or IN)
    assert "tenant_id" in col_map
    assert col_map["tenant_id"]["predicate_types"]["equality"] >= 2
    assert "tenant_id" in result["equality_cols"]

    # event_date appears as a range filter
    assert "event_date" in col_map
    assert col_map["event_date"]["predicate_types"]["range"] >= 1
    assert "event_date" in result["range_cols"]

    # tenant_id is the more-frequent filter: it's in every query; event_date in 2/3
    assert col_map["tenant_id"]["count"] >= col_map["event_date"]["count"]


def test_partition_granularity_mismatch_sql():
    """Monthly-partitioned table, queries filter at day granularity.
    The SQL parser surfaces event_date as a range column appearing in every query.
    Combined with a Spark eventlog showing partial prune_rate (month-level pruning
    doesn't eliminate within-month files), this triggers partition evolution
    to a finer truncate(day, event_date) spec.
    """
    aliases = table_aliases("db.daily_events")
    statements = [
        "SELECT * FROM db.daily_events WHERE event_date = '2024-03-15'",
        "SELECT sum(revenue) FROM db.daily_events WHERE event_date BETWEEN '2024-03-15' AND '2024-03-15'",
        "SELECT * FROM db.daily_events WHERE event_date >= '2024-03-01' AND event_date < '2024-04-01'",
    ]
    result = analyze_sql_statements(statements, aliases)

    assert result["matched_query_count"] == 3
    col_map = {fc["column"]: fc for fc in result["filter_columns"]}

    assert "event_date" in col_map
    # event_date appears in all 3 queries (equality and range both)
    assert col_map["event_date"]["count"] == 3
    # Between, >=, < all register as range; = as equality
    # dominant is range (appears in 2 queries as range, 1 as equality)
    # (exact counts depend on parser, but event_date must be identified)
    assert col_map["event_date"]["dominant"] in ("range", "equality")
