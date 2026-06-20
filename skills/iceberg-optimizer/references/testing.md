# Benchmarking & Testing Plan — iceberg-optimizer

## Overview

Testing is split into two tiers:

**Tier 1 — Unit / fixture tests** (`tests/`)
Fast pytest suite that imports the Python functions directly and exercises them
against inline dict fixtures (no file I/O, no Docker, no network). Covers the
five archetype scenarios below. These run in a few seconds and are the right
place to iterate on logic.

**Tier 2 — End-to-end with Docker Compose** (`docker/`)
Spins up a real Spark-Iceberg cluster (REST catalog + MinIO). You write actual
Iceberg tables, export the metadata tables, then run the scripts against the real
dumps. Validates that the full pipeline works against live Iceberg output format
including Spark's stringified map columns.

---

## Scenario Matrix

| ID | Name | Cadence | Dominant problem | Expected recommendation |
|----|------|---------|-----------------|------------------------|
| A | `cold_archive` | Batch weekly | Nothing wrong (healthy cold table) | `do_nothing` (at low QPM) |
| B | `streaming_thin_spread` | Streaming (30-second commits) | Massive small-file proliferation across many partitions | `light` or `targeted_sort`; `snapshot_bloat` + `thin_spread` |
| C | `gdpr_deletes` | Daily batch + delete files | High equality-delete pressure from GDPR erasure | `aggressive` rewrite to merge equality deletes |
| D | `snapshot_bloat_only` | Hourly, large files | Snapshot log bloated but files are fine | `light` (expire snapshots only) |
| E | `healthy_batch` | Daily batch, well-maintained | Nothing wrong | `do_nothing` |

### Flag expectations per scenario

| Flag | A | B | C | D | E |
|------|---|---|---|---|---|
| `needs_binpack` | False | True | False | False | False |
| `delete_pressure` | False | False | True | False | False |
| `equality_delete_pressure` | False | False | True | False | False |
| `thin_spread` | False | True | False | False | False |
| `structural_small_files` | False | True | False | False | False |
| `mutated` | False | False | True | False | False |
| `snapshot_bloat` | False | True | False | True | False |

---

## Running tests locally

```bash
cd skills/iceberg-optimizer
pip install pytest            # only dependency beyond stdlib
pytest tests/ -v
```

`sqlglot` is optional — tests that exercise SQL parsing run against the regex
fallback when it is not installed.

No conftest.py or pytest.ini needed; pytest discovers `test_*.py` automatically.

---

## Docker Compose end-to-end setup

```bash
cd skills/iceberg-optimizer/docker
docker compose up -d
# Wait ~30 s for MinIO and Spark to initialise
docker exec -it spark-iceberg bash
```

Inside the container you have a full Spark session pre-wired to the REST catalog
and MinIO. Run any of the SQL examples from `references/procedures.md` against the
`demo` catalog. The `tests/` and `scripts/` directories are bind-mounted at
`/opt/tests` and `/opt/scripts`.

### Export metadata and run the scripts

```bash
# Inside the container
spark-sql --conf spark.sql.catalog.demo=org.apache.iceberg.spark.SparkCatalog \
  -e "SELECT * FROM demo.db.mytable.snapshots" > /tmp/snap.json

# On your host
docker cp spark-iceberg:/tmp/snap.json snap.json
python scripts/profile_table.py \
  --snapshots snap.json --files files.json --out profile.json
python scripts/simulate.py --profile profile.json
```

---

## How to add a new scenario

1. Decide which flags you want to exercise and pick representative numbers for
   `file_size_in_bytes`, `record_count`, snapshot `operation`, `summary`, and
   `committed_at` spacing.
2. Add a fixture builder function in `tests/test_profiler.py` that returns
   `(files_rows, snapshots_rows)` inline dicts.
3. Add two test functions:
   - `test_<name>_profile_files()` — assert the numeric profile stats
   - `test_<name>_flags()` — assert the boolean flags from `_flags()`
4. If the scenario adds a new flag, add the flag computation to `_flags()` in
   `scripts/profile_table.py` before committing.
5. Update the scenario matrix table above.

---

## Key invariants to check

### Profile invariants (all scenarios)

- `files["data_files"] + files["delete_files"]` equals total rows with `content != 0`
  counted separately.
- `files["delete_file_pct"]` is in `[0, 1]`.
- `files["avg_mb"]` matches `sum(file_size_in_bytes for data files) / count / MB`.
- `snapshots["snapshot_count"]` equals the number of parseable timestamps.
- `snapshots["write_cadence"]["class"]` is one of `streaming`, `micro-batch`,
  `hourly-batch`, `batch`, `unknown`.

### Flag invariants

- `needs_binpack=True` requires either `avg_mb < 64` or `>30 %` of files under 64 MB.
- `delete_pressure=True` requires `delete_file_pct > 0.10`.
- `equality_delete_pressure=True` requires `eq_delete_pressure > 0.05`
  (equality-delete record count / data record count). *(Requires profile_table.py update.)*
- `thin_spread=True` requires median partitions per commit > 3 AND avg added file MB < 64.
- `structural_small_files=True` when the writer is not buffering to target size
  (`buffers_to_target=False`).
- `mutated=True` when any snapshot has `operation` other than `append`.
- `snapshot_bloat=True` when `snapshot_count > 1000`.

### Simulator invariant

- Scenario with the lowest `total_cost_month_usd` is the `do_nothing` case when
  `queries_per_month` is very low (≤ 5) on a healthy cold table (no rewrite costs
  outweigh query savings at that volume).
