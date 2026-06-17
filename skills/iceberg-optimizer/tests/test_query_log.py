"""Pytest tests for parse_query_log.py.

Imports functions directly; only test_explain_analyze_parsing writes a temp file.
Run with: pytest tests/ -v
"""
import sys
import os
import statistics as stats
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from parse_query_log import (
    _flatten_trino_event_listener,
    _selectivity,
    analyze_sql_statements,
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
