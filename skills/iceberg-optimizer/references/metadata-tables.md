# Iceberg metadata tables: schemas & diagnostic queries

Every Iceberg table exposes read-only virtual tables. In Spark and Trino they are
addressed as `catalog.schema.table.<name>` (Spark) or
`catalog.schema."table$name"` (Trino). All queries below are written for Spark
SQL; the Trino equivalents are noted where the syntax differs.

The complete set: `snapshots`, `history`, `metadata_log_entries`, `refs`,
`manifests`, `all_manifests`, `files`, `data_files`, `delete_files`, `entries`,
`all_entries`, `all_files`, `all_data_files`, `all_delete_files`, `partitions`,
`position_deletes`. The five that drive this skill are `snapshots`, `files`,
`partitions`, `manifests`, and `history`.

---

## `files` — the richest diagnostic source

One row per data/delete file in the **current** snapshot.

| Column | Type | Use |
|---|---|---|
| `content` | int | 0 = data, 1 = position-delete, 2 = equality-delete |
| `file_path` | string | identify hot/cold files |
| `file_format` | string | PARQUET / ORC / AVRO |
| `record_count` | long | rows in file; with size → avg row width |
| `file_size_in_bytes` | long | **small-file detection** |
| `column_sizes` | map<int,long> | per-column bytes — find bloated columns |
| `value_counts` | map<int,long> | non-null values per column |
| `null_value_counts` | map<int,long> | null density (high nulls weaken min/max skipping) |
| `nan_value_counts` | map<int,long> | float quality |
| `lower_bounds` | map<int,binary> | per-column min per file (serialized) |
| `upper_bounds` | map<int,binary> | per-column max per file (serialized) |
| `split_offsets` | array<long> | row-group offsets |
| `equality_ids` | array<int> | columns an equality-delete matches on |
| `added_snapshot_id` | long | which commit created the file |
| `data_sequence_number` | long | ordering in table history |

`lower_bounds`/`upper_bounds` are the statistical basis for **sort-key
selection**: if two files' ranges for a column overlap heavily, a query filtering
that column must read both; sorting on it shrinks the overlap so files can be
skipped. The map keys are *field IDs*, not names — get IDs from
`DESCRIBE EXTENDED` or the table schema. Bounds are type-serialized; decode per
column type (ints little-endian, strings UTF-8, timestamps micros-since-epoch).

### File-size health

```sql
SELECT
  COUNT(*)                                              AS data_files,
  ROUND(AVG(file_size_in_bytes)/1048576, 1)             AS avg_mb,
  ROUND(percentile_approx(file_size_in_bytes, 0.5)/1048576, 1) AS median_mb,
  SUM(CASE WHEN file_size_in_bytes < 64*1048576 THEN 1 ELSE 0 END) AS files_under_64mb,
  ROUND(SUM(file_size_in_bytes)/1073741824, 2)          AS total_gb
FROM db.tbl.files
WHERE content = 0;
```
`avg_mb < 64` or a large `files_under_64mb` share → bin-pack candidate. Target is
256–512 MB (`write.target-file-size-bytes`).

### Delete-file pressure (v2 merge-on-read tables)

```sql
SELECT content, COUNT(*) AS files, SUM(record_count) AS records
FROM db.tbl.files
WHERE content IN (1, 2)
GROUP BY content;
```
Many delete files, or deletes whose `records` are a large fraction of live rows,
slow every read until compaction merges them. Delete files > ~10% of data files
is a strong, time-sensitive compaction trigger.

---

## `partitions` — partition-level health

One row per partition in the current snapshot.

| Column | Use |
|---|---|
| `partition` | the partition tuple (struct) |
| `record_count` | **data skew** across partitions |
| `file_count` | compact if high |
| `total_data_file_size_in_bytes` | partition size |
| `position_delete_record_count` | pending position deletes |
| `equality_delete_record_count` | pending equality deletes (expensive) |

```sql
SELECT
  partition,
  file_count,
  ROUND(total_data_file_size_in_bytes/1048576, 1) AS mb,
  ROUND(total_data_file_size_in_bytes/file_count/1048576, 1) AS avg_file_mb,
  record_count
FROM db.tbl.partitions
ORDER BY file_count DESC;
```
Skew check: `MAX(record_count) / MIN(record_count)`. Ratio > 10 with an identity
partition transform → consider `bucket(N, col)` instead. Total file size per
partition ideally sits in the 1–10 GB+ range with individual files ≥ ~100 MB.

---

## `snapshots` — write pattern, velocity, and ingestion shape

One row per commit. This table is how Phase 2a *derives the ingestion pipeline*
without asking the user.

| Column | Use |
|---|---|
| `committed_at` | timestamp of commit → cadence |
| `snapshot_id` / `parent_id` | lineage |
| `operation` | `append` / `overwrite` / `delete` / `replace` |
| `summary` | map<string,string> of commit metrics (below) |

Useful `summary` keys: `added-data-files`, `deleted-data-files`,
`added-records`, `deleted-records`, `added-files-size`, `changed-partition-count`,
`total-data-files`, `total-records`, `total-files-size`,
`total-position-deletes`, `total-equality-deletes`.

### Write cadence → streaming / micro-batch / batch

```sql
SELECT
  COUNT(*) AS commits,
  ROUND(percentile_approx(gap_sec, 0.5), 1) AS median_gap_sec,
  ROUND(percentile_approx(gap_sec, 0.9), 1) AS p90_gap_sec
FROM (
  SELECT unix_timestamp(committed_at)
       - lag(unix_timestamp(committed_at)) OVER (ORDER BY committed_at) AS gap_sec
  FROM db.tbl.snapshots
  WHERE operation IN ('append','overwrite')
);
```
median gap < ~60 s → near-real-time/streaming · 1–15 min → micro-batch ·
≥ hourly → batch.

### File size at write → does the writer buffer to target?

```sql
SELECT
  ROUND(AVG( CAST(summary['added-files-size'] AS double)
           / NULLIF(CAST(summary['added-data-files'] AS double),0) )/1048576, 1)
        AS avg_added_file_mb,
  percentile_approx(CAST(summary['added-data-files'] AS int), 0.5)
        AS median_files_per_commit
FROM db.tbl.snapshots
WHERE operation = 'append' AND committed_at > now() - INTERVAL 7 DAYS;
```
Tiny `avg_added_file_mb` + many files/commit → the writer flushes small files
(no buffering); the small-file problem is structural and compaction must be
ongoing. Near-target size → writer already buffers (e.g. `fanout` disabled,
`write.target-file-size-bytes` honored) and compaction can be infrequent.

### Partition fan-out → single partition vs thin spread

```sql
SELECT
  percentile_approx(CAST(summary['changed-partition-count'] AS int), 0.5)
        AS median_partitions_per_commit,
  ROUND(percentile_approx(
        CAST(summary['added-data-files'] AS double)
      / NULLIF(CAST(summary['changed-partition-count'] AS double),0), 0.5), 1)
        AS median_files_per_partition_per_commit
FROM db.tbl.snapshots
WHERE operation = 'append' AND committed_at > now() - INTERVAL 7 DAYS;
```
≈ 1 partition/commit → each batch lands in one (usually time) partition; clean to
compact. High partition count with few files each → **thin spread**: every commit
sprinkles tiny files across many partitions, the worst small-file generator.
Mitigations: align ingest to fewer partitions, set the write distribution mode
(`write.distribution-mode = hash`), or compact aggressively.

### Late / out-of-order arrival

Compare the event-time *bounds* of recently-added files against their commit
time. If files committed today carry old event-times, data is late/out-of-order:

```sql
-- replace 3 with the field ID of your event-time column; decode bounds per type
SELECT f.added_snapshot_id, s.committed_at,
       f.lower_bounds[3] AS min_event_time_raw,
       f.upper_bounds[3] AS max_event_time_raw
FROM db.tbl.files f
JOIN db.tbl.snapshots s ON f.added_snapshot_id = s.snapshot_id
WHERE s.committed_at > now() - INTERVAL 1 DAYS AND f.content = 0;
```
Late data breaks two common assumptions: (1) "compact only cold partitions" — old
partitions keep receiving writes; (2) data is naturally time-clustered — it is
not, so an explicit sort order matters more.

### Mutability seen so far

```sql
SELECT operation, COUNT(*) AS commits FROM db.tbl.snapshots GROUP BY operation;
```
Only `append` → append-only in practice. Presence of `delete`/`overwrite` or
delete files in `files` → the table is mutated; confirm the outlook in the
interview (it affects copy-on-write vs merge-on-read and compaction urgency).

---

## `manifests` — metadata-layer health

| Column | Use |
|---|---|
| `path`, `length` | manifest file size |
| `partition_spec_id` | **detect mixed specs** after partition evolution |
| `added_files_count` / `existing_files_count` / `deleted_files_count` | manifest churn |
| `added_rows_count` / `existing_rows_count` / `deleted_rows_count` | row churn |

```sql
SELECT partition_spec_id, COUNT(*) AS manifests, SUM(existing_files_count) AS files
FROM db.tbl.manifests
GROUP BY partition_spec_id;
```
`COUNT(*)` high (≳ 500) → `rewrite_manifests` / `optimize_manifests`. Multiple
`partition_spec_id` values → old data still on the old partition layout; a
`rewrite-all` compaction is needed to physically migrate it.

---

## `history` — lifecycle arc

```sql
SELECT s.operation, COUNT(*) AS commits,
       MIN(h.made_current_at) AS first_seen, MAX(h.made_current_at) AS last_seen
FROM db.tbl.history h JOIN db.tbl.snapshots s ON h.snapshot_id = s.snapshot_id
GROUP BY s.operation;
```
Reveals whether the table is actively written, append-only, or effectively
frozen — input to the "is it worth optimizing?" gate.

---

## Trino syntax notes

- Metadata tables: `SELECT * FROM catalog.schema."tbl$snapshots"` (quote the
  `$name`). Available: `$snapshots`, `$history`, `$manifests`, `$files`,
  `$partitions`, `$properties`, `$refs`, `$metadata_log_entries`.
- Trino exposes a `$files` table with the same statistical columns
  (`record_count`, `file_size_in_bytes`, `lower_bounds`, `upper_bounds`, …).
- For workload analysis, recent query text and stats are in
  `system.runtime.queries` (short retention — persist it to a table for history).
