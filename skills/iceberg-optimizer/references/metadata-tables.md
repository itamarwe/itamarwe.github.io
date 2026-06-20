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
-- Count and record pressure per delete type
SELECT content, COUNT(*) AS files, SUM(record_count) AS delete_records
FROM db.tbl.files
WHERE content IN (1, 2)
GROUP BY content;
-- content 1 = position delete, content 2 = equality delete

-- Equality delete pressure ratio: fraction of live data rows covered by eq deletes.
-- > 5% means every scan carries a meaningful join overhead until compacted.
SELECT
  SUM(CASE WHEN content = 2 THEN record_count ELSE 0 END) AS eq_delete_records,
  SUM(CASE WHEN content = 0 THEN record_count ELSE 0 END) AS data_records,
  ROUND(
    SUM(CASE WHEN content = 2 THEN record_count ELSE 0 END) /
    NULLIF(SUM(CASE WHEN content = 0 THEN record_count ELSE 0 END), 0), 4
  ) AS eq_delete_pressure
FROM db.tbl.files;
```

**Equality deletes (content=2) are the high-urgency case.** Each equality delete
record represents a deletion predicate that must be evaluated as a join against
*every data file* on every scan, regardless of partition pruning. Position deletes
(content=1) are cheaper — they are a per-row seek within files that overlap by
position. A table with significant `eq_delete_pressure` needs compaction
urgently; a table with only position deletes has more slack.

```sql
-- Delete accumulation rate from $snapshots summary keys
SELECT
  COUNT(*) FILTER (WHERE summary['added-delete-files'] IS NOT NULL
                     AND CAST(summary['added-delete-files'] AS int) > 0)
                                       AS delete_commits,
  SUM(CAST(COALESCE(summary['added-delete-files'],'0') AS int))
                                       AS total_added_delete_files,
  SUM(CAST(COALESCE(summary['added-equality-deletes'],'0') AS int))
                                       AS total_added_eq_delete_records,
  -- Latest snapshot running totals
  MAX_BY(CAST(COALESCE(summary['total-equality-deletes'],'0') AS long),
         committed_at)                 AS current_total_eq_deletes,
  MAX_BY(CAST(COALESCE(summary['total-position-deletes'],'0') AS long),
         committed_at)                 AS current_total_pos_deletes
FROM db.tbl.snapshots
WHERE committed_at > now() - INTERVAL 30 DAYS;
```

Rising `current_total_eq_deletes` without intervening `rewrite_data_files` commits
means equality deletes are accumulating — the scan cost compounds until compaction.
If the deletion pattern is driven by compliance (GDPR), treat compaction + snapshot
expiry as a compliance obligation, not a performance optimization.

**Sawtooth pattern diagnostic:** In a healthy compaction cycle, delete file counts
rise between compaction runs (as new deletes arrive) and drop sharply after each
successful compaction run — a sawtooth wave over time. Query the snapshot summary
keys over a window to check the shape:

```sql
SELECT
  committed_at,
  CAST(COALESCE(summary['total-delete-files'],'0') AS long) AS total_delete_files,
  CAST(COALESCE(summary['total-equality-deletes'],'0') AS long) AS total_eq_deletes,
  CAST(COALESCE(summary['total-position-deletes'],'0') AS long) AS total_pos_deletes,
  operation
FROM db.tbl.snapshots
WHERE committed_at > now() - INTERVAL 7 DAYS
ORDER BY committed_at;
```

If `total_delete_files` only grows and never drops, compaction is not keeping up
or is silently failing. Look for: (1) `replace` operations (compaction commits)
in the `operation` column — their absence means no compaction ran; (2) compaction
commits that don't reduce the count — indicates the `where` clause excludes the
partitions with the highest delete accumulation. A monotonically increasing trend
without drops warrants immediate investigation of the compaction job's
configuration and logs.

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
  record_count,
  equality_delete_record_count,
  position_delete_record_count,
  ROUND(equality_delete_record_count / NULLIF(record_count, 0), 4)
                                      AS partition_eq_delete_pressure
FROM db.tbl.partitions
ORDER BY equality_delete_record_count DESC, file_count DESC;
```
`equality_delete_record_count` per partition identifies which partitions are most
affected and should be prioritized in a targeted compaction (e.g.
`WHERE partition_col = <hot_partition>`).
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

## `manifests` — metadata-layer health and planning efficiency

Every Iceberg query plan works in two layers of pruning:
1. **Manifest pruning** — the planner reads each manifest's `partition_summaries`
   (per-field lower/upper bounds) and skips manifests whose bounds don't overlap
   the query predicate. This is *before* any file is opened.
2. **File pruning** — within surviving manifests, the planner skips files by their
   per-file `lower_bounds`/`upper_bounds` (the sort-key effectiveness).

If manifests are poorly clustered (each manifest contains a random mix of
partitions), manifest pruning fires rarely and the planner must read *all*
manifests to find qualifying files — even for a narrow partition filter.
`rewrite_manifests(sort_by)` fixes this by clustering manifests so that each
covers a contiguous range of a partition column; the planner can then skip
entire manifests with a single bounds comparison.

| Column | Use |
|---|---|
| `path`, `length` | manifest file size; many small manifests increase planning I/O |
| `partition_spec_id` | **detect mixed specs** after partition evolution |
| `added_files_count` / `existing_files_count` / `deleted_files_count` | manifest churn |
| `added_rows_count` / `existing_rows_count` / `deleted_rows_count` | row churn |
| `partition_summaries` | array of per-field `{contains_null, contains_nan, lower_bound, upper_bound}` — the basis for manifest-level pruning; bounds are type-serialized binary, not directly human-readable in SQL |

### Overall manifest health

```sql
SELECT
  partition_spec_id,
  COUNT(*)                                   AS manifests,
  ROUND(AVG(length)/1048576, 2)              AS avg_manifest_mb,
  SUM(added_files_count + existing_files_count) AS files_referenced
FROM db.tbl.manifests
GROUP BY partition_spec_id
ORDER BY manifests DESC;
```
`COUNT(*) > 500` → `rewrite_manifests` / `optimize_manifests`. Multiple
`partition_spec_id` values → old data still on the old partition layout; a
`rewrite-all` compaction is needed to physically migrate it. Small `avg_manifest_mb`
(< 1 MB) with many manifests → high planning I/O; consolidate.

### Manifest clustering / scatter diagnostic

A well-clustered manifest list means each manifest covers a narrow, contiguous
partition range, so the planner can skip most manifests for a narrow filter. A
scattered manifest list means each manifest contains a random mix of partitions;
the planner cannot skip any of them.

```sql
-- Scatter proxy: how many manifests reference each distinct partition spec?
-- A ratio of manifests >> distinct partition values suggests random ordering.
SELECT
  partition_spec_id,
  COUNT(*)                                    AS manifest_count,
  SUM(added_files_count + existing_files_count) AS total_files,
  ROUND(SUM(length)/1048576, 1)              AS total_manifest_mb,
  -- Average files per manifest: low value = many tiny manifests (bad for planning)
  ROUND(
    SUM(added_files_count + existing_files_count) / NULLIF(COUNT(*), 0), 1
  )                                           AS avg_files_per_manifest
FROM db.tbl.manifests
GROUP BY partition_spec_id;
```

**Interpretation:**
- `avg_files_per_manifest < 100` with `manifest_count > 500` → many tiny manifests,
  high planning I/O. `rewrite_manifests` consolidates them.
- `manifest_count` is high but `partition_spec_id` is homogeneous → run
  `rewrite_manifests(sort_by => array('<partition_col>'))` (Spark) to cluster
  manifests by partition and restore skip efficiency.
- Multiple `partition_spec_id` values → mixed spec; each query must consult
  manifests from all specs. A `rewrite-all` compaction (or `rewrite_manifests`
  covering all specs) normalises this.

### Manifest scatter ratio

A simple heuristic: compare `manifest_count` to the number of distinct active
partition values. If `manifest_count >> distinct_partitions`, manifests are
scattered — each manifest covers files from many different partitions, so the
planner cannot skip any manifest for a narrow filter. After
`rewrite_manifests(sort_by)`, the ratio drops: each manifest covers a narrow
partition range.

```sql
-- Compute scatter ratio: high ratio → clustering beneficial
SELECT
  (SELECT COUNT(*) FROM db.tbl.manifests)           AS manifest_count,
  (SELECT COUNT(DISTINCT partition) FROM db.tbl.partitions) AS distinct_partitions,
  ROUND(
    (SELECT COUNT(*) FROM db.tbl.manifests) * 1.0 /
    NULLIF((SELECT COUNT(DISTINCT partition) FROM db.tbl.partitions), 0), 1
  )                                                  AS manifests_per_partition;
-- Ratio > 3 with manifest_count > 100 → run rewrite_manifests with sort_by
-- Ratio < 2 → manifests already clustered; no action needed
```

**Bucket count heuristic for partition evolution:** when adding a `bucket(N, col)`
partition transform, target 1–5 GB of data per bucket at current table size.
Formula: `N = ceil(total_gb / 2)`, capped at ~1000. Too few buckets → skew
reappears; too many → metadata overhead and small files per bucket. Re-evaluate
N when table size grows by 10×.

**Note on `partition_summaries` bounds:** The per-manifest lower/upper bounds
in `partition_summaries` are type-serialized binary and cannot be decoded in plain
SQL. To quantitatively measure manifest overlap (the true signal for clustering
quality), you need the Iceberg Java/Python library or a custom Spark UDF that
reads the bounds as Iceberg types. For the SQL-only diagnostic above, use
`avg_files_per_manifest` and `manifest_count` as heuristic proxies.

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
