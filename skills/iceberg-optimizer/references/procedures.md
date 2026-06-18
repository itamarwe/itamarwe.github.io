# Maintenance procedures by engine

Verified against Apache Iceberg docs, Spark procedures, and the Trino 481 Iceberg
connector. **Always run in this order:** compact → expire snapshots → remove
orphans → rewrite manifests.

**Why this order matters (dependency chain):**
- **Compact before expire snapshots:** compaction must run first because expiring
  snapshots makes previously-referenced delete files unreachable. If snapshots
  expire before compaction, the ability to physically remove those rows is lost
  permanently — the deleted-row data survives in data files until those files are
  rewritten in a future compaction, but the delete files that track them may no
  longer be valid.
- **Expire before orphan cleanup:** running orphan cleanup too early risks deleting
  files that are still referenced by unexpired snapshots. Always expire first to
  dereference stale files, then remove orphans to reclaim storage for files no
  longer referenced by any snapshot.

**Engine flexibility:** Any Iceberg-compatible engine (Spark, Trino, Dremio, or
others) can run maintenance operations. Organizations can centralize maintenance
workflows even in heterogeneous multi-engine environments. The choice of engine
per operation is driven by capability (sort/z-order require Spark; bin-pack and
snapshot expiry work in Trino or Spark) rather than by data ownership. See the
engine selection table below.

## Format-version upgrade (one-time prerequisite for delete workloads)

Must be run before any E1/E2 delete-file compaction on a v1 table.
Metadata-only, instant, backwards-compatible.

**Format version roadmap:** v1 → v2 → v3. V2 adds row-level deletes
(position and equality delete files). V3 replaces position delete files with
**deletion vectors** — compact bitmaps stored per data file that track which
rows are deleted. Deletion vectors reduce per-scan overhead and simplify
retention (fewer files to track), but require engine support (e.g., Amazon EMR
with Iceberg v3 enabled). Upgrade to v3 only when your engines support it; the
compaction procedure (`rewrite_data_files`) is the same, but the resulting
delete format is more efficient. Until v3 is standard in your environment,
target v2 and use `rewrite_position_delete_files` (see below) to manage
position delete accumulation.

**Migration notes:**
- v1 → v2 is fully backwards-compatible. V1 tables remain readable by v2 engines
  with no metadata changes required; the upgrade is an additive metadata-only
  operation. Existing files stay valid. Safe to apply to production tables without
  a maintenance window.
- v3 features (deletion vectors, extended types, row lineage, encryption) are
  additive but adoption depends on engine support across all engines that read the
  table. Before upgrading to v3, verify that every engine in your environment
  (Spark, Trino, Dremio, Flink, etc.) supports it. No ALTER TABLE migration
  procedure for v3 is standardized across engines — check current release notes
  for your specific engine before proceeding.

```sql
-- Check current version
SHOW TBLPROPERTIES db.tbl ('format-version');    -- Spark
SELECT * FROM catalog.db."tbl$properties"
  WHERE key = 'format-version';                  -- Trino

-- Upgrade to v2 (enables row-level deletes, merge-on-read, Puffin stats)
ALTER TABLE cat.db.tbl SET TBLPROPERTIES ('format-version' = '2');
```

## Write-time sort order (free clustering — no rewrite)

Set once; all future writes cluster by the sort key at zero extra maintenance cost.
The table sort order persists in the table metadata and is respected by Spark and
Trino writers.

```sql
-- Spark: persisted sort order (writers cluster up-front)
ALTER TABLE cat.db.tbl WRITE ORDERED BY event_date ASC NULLS LAST, tenant_id ASC NULLS LAST;

-- Trino: equivalent via table property
ALTER TABLE cat.db.tbl SET PROPERTIES sorted_by = ARRAY['event_date', 'tenant_id'];

-- Remove sort order (revert to unsorted writes)
ALTER TABLE cat.db.tbl WRITE UNORDERED;  -- Spark
```

**When to use:** table has no sort order AND writers buffer to near-target file
size (i.e. `avg_added_file_mb ≥ 64`). Writers that flush tiny files get little
benefit — fix write-time buffering (Action J) first, then add sort order.

---

---

## Spark (most complete)

Requires the Iceberg SQL extensions (Spark 3.x); native in Spark 4.0.

```
spark.sql.extensions = org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
```

### rewrite_data_files — compaction

```sql
-- Bin-pack (default): just resize small files
CALL cat.system.rewrite_data_files(
  table => 'db.tbl',
  strategy => 'binpack',
  options => map(
    'target-file-size-bytes', '268435456',     -- 256 MB
    'min-input-files', '5',
    'max-concurrent-file-group-rewrites', '10',
    'partial-progress.enabled', 'true',         -- commit in batches; fault-tolerant
    'remove-dangling-deletes', 'true'           -- clean delete files during rewrite
  ),
  where => 'event_date < current_date()'        -- e.g. compact only cold partitions
);

-- Sort: cluster by a key for data skipping
CALL cat.system.rewrite_data_files(
  table => 'db.tbl', strategy => 'sort',
  sort_order => 'event_date ASC NULLS LAST, tenant_id ASC NULLS LAST',
  options => map('target-file-size-bytes','268435456')
);

-- Z-order: multi-dimensional clustering (2–4 high-cardinality cols)
CALL cat.system.rewrite_data_files(
  table => 'db.tbl', strategy => 'sort',
  sort_order => 'zorder(tenant_id, event_time)',
  options => map('rewrite-all','true','target-file-size-bytes','268435456')
);
```

Key options: `target-file-size-bytes` (default 512 MB), `min-input-files`
(default 5), `max-file-group-size-bytes` (default 100 GB — raise for huge
partitions), `max-concurrent-file-group-rewrites`, `partial-progress.enabled` +
`partial-progress.max-commits`, `rewrite-all`, `remove-dangling-deletes`.

### expire_snapshots

```sql
CALL cat.system.expire_snapshots(
  table => 'db.tbl',
  older_than => TIMESTAMP '2025-06-01 00:00:00.000',
  retain_last => 10,                 -- default is 1 — ALWAYS raise in production
  max_concurrent_deletes => 10
);
```
Or let any writer auto-expire via table properties:
`history.expire.max-snapshot-age-ms`, `history.expire.min-snapshots-to-keep`.

### remove_orphan_files (destructive — dry-run first)

```sql
CALL cat.system.remove_orphan_files(
  table => 'db.tbl',
  older_than => TIMESTAMP '2025-05-29 00:00:00.000',  -- ≥ 3 days; ≥ longest write
  dry_run => true
);
```
Default safety interval is 3 days. Shorter than the longest in-flight write can
corrupt the table — never reduce it without certainty.

### rewrite_position_delete_files (MOR-specific)

Compacts and restructures position delete files without rewriting data files.
Use when position delete files have accumulated (high `pos_delete_pressure`)
but you want to reduce delete-file overhead without paying the full cost of a
data-file rewrite. Also used for compliance: removes dangling position deletes
that reference rows already removed by prior compaction.

```sql
-- Consolidate position delete files for a table (Spark)
CALL cat.system.rewrite_position_delete_files(
  table => 'db.tbl',
  options => map(
    'target-file-size-bytes', '67108864',   -- 64 MB for delete files
    'partial-progress.enabled', 'true'
  )
);

-- Target a specific partition (where clause supported)
CALL cat.system.rewrite_position_delete_files(
  table => 'db.tbl',
  options => map('target-file-size-bytes', '67108864'),
  where => 'event_date < current_date()'
);
```

**Key distinction from `rewrite_data_files`:** `rewrite_data_files` rewrites
data files and can absorb delete files during the process (when
`remove-dangling-deletes: true`). `rewrite_position_delete_files` only
rewrites delete files — cheaper but leaves data files untouched. Use it as a
lightweight maintenance pass when delete file count is high but data files are
already well-sized. For full physical removal of deleted rows (e.g., GDPR),
`rewrite_data_files` is still required.

**Trino:** No direct equivalent. Use `rewrite_data_files` (via Spark) or
`EXECUTE optimize` (which merges deletes into data files as a side effect).

### rewrite_manifests

Two goals — pick per situation:

```sql
-- 1. Consolidate: merge many small manifests into fewer large ones
--    (reduces planning I/O; run after high-frequency streaming commits)
CALL cat.system.rewrite_manifests(table => 'db.tbl');

-- 2. Cluster: reorder manifests so each covers a contiguous partition range
--    (enables manifest-level pruning — the planner skips entire manifests
--    for narrow partition filters without reading their file lists)
CALL cat.system.rewrite_manifests(
  table   => 'db.tbl',
  sort_by => array('event_date')   -- the dominant partition / filter column
);
```

Cheap, concurrent with reads/writes. Target manifest size via
`commit.manifest.target-size-bytes` (default 8 MB).

**When clustering matters:** after many streaming commits, each manifest
contains a random mix of partition values (one file from partition_A, one from
partition_B, etc.). A query for `event_date = '2025-01-01'` must read ALL
manifests to find qualifying files because no manifest is exclusively
`event_date = '2025-01-01'`. After `sort_by => array('event_date')`, manifests
are ordered by `event_date` and the planner can skip most of them with a single
bounds check. This reduces planning latency for all queries, independently of
data skipping.

---

## Trino — `ALTER TABLE … EXECUTE`

Trino uses `EXECUTE` (not `CALL`) and **duration strings** (not timestamps), and
enforces catalog-level minimum-retention floors you cannot undercut per call.
Trino **does** support snapshot expiry, orphan removal, and manifest optimization
— do not claim otherwise.

```sql
-- Compaction (bin-pack); WHERE targets partitions
ALTER TABLE cat.db.tbl EXECUTE optimize(file_size_threshold => '256MB')
  WHERE event_date >= DATE '2025-01-01';

-- Expire snapshots (>= iceberg.expire-snapshots.min-retention, default 7d)
ALTER TABLE cat.db.tbl EXECUTE expire_snapshots(retention_threshold => '7d');

-- Remove orphan files (>= iceberg.remove-orphan-files.min-retention, default 7d)
ALTER TABLE cat.db.tbl EXECUTE remove_orphan_files(retention_threshold => '7d');

-- Rewrite/consolidate manifests (Trino ~479+; PR #25378)
-- Note: Trino's optimize_manifests consolidates but does NOT sort by partition.
-- For manifest clustering (sort_by), use Spark's rewrite_manifests procedure.
ALTER TABLE cat.db.tbl EXECUTE optimize_manifests;
```

Trino does **not** expose sort/z-order *strategies* in `optimize` (bin-pack
only). For sort/z-order rewrites, use Spark. Set the table sort order so Trino
writes clustered data: `ALTER TABLE cat.db.tbl SET PROPERTIES sorted_by = ARRAY['event_date'];`

| Operation | Spark | Trino |
|---|---|---|
| Format upgrade | `ALTER TABLE … SET TBLPROPERTIES ('format-version' = '2')` | same |
| Write-time sort order | `ALTER TABLE … WRITE ORDERED BY col` | `ALTER TABLE … SET PROPERTIES sorted_by = ARRAY['col']` |
| Compact data (bin-pack) | `CALL …rewrite_data_files(strategy=>'binpack',...)` | `ALTER TABLE t EXECUTE optimize(...)` |
| Sort / z-order compaction | `strategy => 'sort' / zorder(...)` | not available (use Spark) |
| Expire snapshots | `CALL …expire_snapshots(older_than => TIMESTAMP …)` | `EXECUTE expire_snapshots(retention_threshold => '7d')` |
| Remove orphans | `CALL …remove_orphan_files(...)` | `EXECUTE remove_orphan_files(retention_threshold => '7d')` |
| Rewrite manifests (consolidate) | `CALL …rewrite_manifests(...)` | `EXECUTE optimize_manifests` |
| Rewrite manifests (cluster by partition) | `CALL …rewrite_manifests(sort_by => array('col'))` | not available (use Spark) |

---

## AWS Glue / EMR / S3 Tables

- Glue/EMR run Spark, so all Spark procedures above work directly against the
  Glue Data Catalog (`glue_catalog.system.rewrite_data_files(...)`).
- Set `write.target-file-size-bytes` on the table so every writer (Glue, EMR,
  Athena) produces target-sized files at write time.
- **S3 Tables** (managed Iceberg) runs compaction *for you*, and since mid-2025
  supports **sort and z-order** compaction natively via the S3 Tables maintenance
  configuration — no Spark cluster needed. Prefer it when on S3 Tables.

---

## Apache Flink

Flink writes one file per checkpoint per partition per task → small files by
design. Flink does not compact inline; run the Iceberg action as a batch job:

```java
RewriteDataFilesActionResult r = Actions.forTable(table)
    .rewriteDataFiles()
    .targetSizeInBytes(256L * 1024 * 1024)
    .execute();
```
Or use the Flink maintenance operators / a companion Spark job on a schedule.

---

## GDPR / compliance delete sequence

When individual rows are deleted for compliance reasons (right-to-be-forgotten,
GDPR Art. 17), logical deletion (the delete file) is not sufficient — the data
remains in the data files and in retained snapshots. The physical removal sequence:

```sql
-- Step 1: Delete the row (creates an equality delete file)
DELETE FROM db.tbl WHERE user_id = '<subject>';

-- Step 2: Compact to physically remove the row from data files
-- Must complete before snapshot expiry, not after.
CALL cat.system.rewrite_data_files(
  table => 'db.tbl',
  options => map('remove-dangling-deletes','true')
);
-- Trino: ALTER TABLE cat.db.tbl EXECUTE optimize(file_size_threshold => '256MB');

-- Step 3: Expire snapshots so no historical snapshot retains the deleted row.
-- older_than must be AFTER the delete commit to ensure the pre-delete snapshot
-- is also removed. Confirm no audit/replay requirement conflicts with this.
CALL cat.system.expire_snapshots(
  table => 'db.tbl',
  older_than => NOW(),   -- or: deletion_timestamp + 1 second
  retain_last => 1       -- keep only the post-compaction snapshot
);

-- Step 4: Verify — query the deleted user_id against current snapshot
-- and against the oldest retained snapshot. Both must return 0 rows.
SELECT COUNT(*) FROM db.tbl WHERE user_id = '<subject>';
```

**Copy-on-write as an alternative:** set `write.merge.mode = copy-on-write` and
`write.delete.mode = copy-on-write`. DELETE statements then rewrite affected data
files immediately, producing no delete files. Snapshot expiry alone then completes
physical removal. Higher write cost but simpler compliance posture — no separate
compaction step needed.

```sql
ALTER TABLE cat.db.tbl SET TBLPROPERTIES (
  'write.delete.mode'           = 'copy-on-write',
  'write.update.mode'           = 'copy-on-write',
  'write.merge.mode'            = 'copy-on-write',
  'history.expire.max-snapshot-age-ms' = '86400000'  -- 1 day; size to compliance SLA
);
```

---

## Engine selection for maintenance operations

Choose the engine based on the operation and available infrastructure:

| Operation | Use Spark | Use Trino | Notes |
|---|---|---|---|
| Bin-pack compaction | Yes | Yes | Trino is simpler; Spark supports more options (`partial-progress`, `rewrite-job-order`) |
| Sort / z-order compaction | Yes | No | Trino does not expose sort strategies; must use Spark |
| Expire snapshots | Yes | Yes | Both support this; Trino enforces catalog minimum retention floors |
| Remove orphan files | Yes | Yes | Same note on minimum retention floors for Trino |
| Rewrite manifests (consolidate) | Yes | Yes | Both support basic consolidation |
| Rewrite manifests (cluster by partition) | Yes | No | `sort_by` option is Spark-only |
| Rewrite position delete files | Yes | No | Spark-only procedure; Trino has no equivalent |
| Format version upgrade | Yes | Yes | `ALTER TABLE SET TBLPROPERTIES` works in both |

**Practical guidance:** Use Trino for lightweight, low-overhead maintenance
(snapshot expiry, bin-pack, orphan cleanup) when a Spark cluster is not
available or too costly to spin up. Use Spark for any operation requiring sort
order, z-order, manifest clustering, or position delete file rewriting. In
mixed environments, run Trino operations on a schedule and gate Spark
operations on threshold triggers.

## Table properties worth setting

**File size guidance:** The default `target-file-size-bytes` is 512 MB, but this
is rarely the right value for all workloads. Choose based on workload type:
- **High-write / streaming / CDC tables:** 10–20 MB. Many production streaming
  environments produce better results with smaller target sizes because the overhead
  of large-file compaction cycles outweighs the scan benefits.
- **Mixed workloads (read + write):** 128–256 MB. Balances write throughput with
  scan efficiency. The 256 MB default used in examples here is appropriate for
  most mixed environments.
- **Large analytic engines (Dremio, Trino over large tables):** 256–512 MB. These
  engines are optimized for large sequential scans and can handle larger files
  without per-file overhead penalties.
- **Memory-constrained environments or wide schemas:** 128–256 MB. Very wide tables
  (50+ columns) or deeply nested schemas increase per-file memory pressure —
  smaller files reduce peak executor memory usage.

```sql
ALTER TABLE cat.db.tbl SET TBLPROPERTIES (
  'write.target-file-size-bytes'           = '268435456',  -- 256 MB (tune per guidance above)
  'write.distribution-mode'                = 'hash',        -- curb thin-spread small files
  'commit.manifest.target-size-bytes'      = '8388608',
  'history.expire.max-snapshot-age-ms'     = '604800000',  -- 7 days
  'history.expire.min-snapshots-to-keep'   = '10',
  'write.metadata.metrics.default'         = 'truncate(16)',
  'write.metadata.metrics.column.tenant_id'= 'full',
  'write.parquet.bloom-filter-enabled.column.tenant_id' = 'true',
  'format-version'                         = '2'            -- row-level deletes
);

-- Persisted sort order (writers cluster up front):
ALTER TABLE cat.db.tbl WRITE ORDERED BY event_date, tenant_id;   -- Spark
```

---

## Access control for maintenance jobs

Maintenance jobs need elevated but scoped permissions. Apply least-privilege
principles:

- **Required permissions:** write access to data files (compaction rewrites them),
  delete access to old data/delete files and orphaned objects, and metadata-write
  access (snapshot creation, manifest updates). Read-only permissions are
  insufficient.
- **`remove_orphan_files` is destructive** — it deletes files by path, and a
  misconfigured `older_than` window can corrupt live tables. Require explicit
  approval or a separate elevated role before running in production. Always
  `dry_run` first.
- **Path-based scoping:** grant the maintenance job identity (IAM role, service
  account) write/delete access only to the specific S3 prefixes or GCS paths
  for the tables it maintains. Never grant bucket-wide delete permissions.
- **Catalog RBAC:** if using a modern catalog (Polaris, Nessie, Unity Catalog),
  use its metadata-layer access control to restrict which tables a maintenance
  role can call procedures on. Catalog-level RBAC is the preferred control plane
  — storage permissions are a defense-in-depth layer, not the primary control.
- **Separation of duties:** the maintenance identity should not have query or
  data-write access beyond what maintenance requires. A job that can compact
  tables should not also be able to read PII data or write to application tables.

---

## Maintenance failure patterns and alerting

Common failure signatures and what they indicate:

- **Repeated task failures with system exceptions** (e.g., "too many open files",
  OOM, executor lost): usually signals that a partition is too large for the
  executor configuration. Raise `max-file-group-size-bytes` or increase executor
  memory; alternatively, scope the compaction to a narrower `WHERE` clause.
- **Inconsistent task durations** (some compaction runs take 10x longer than
  others): often caused by partition skew — one partition is vastly larger than
  others. Profile with the `partitions` metadata table; use partition-targeted
  `WHERE` clauses for the skewed partition.
- **Monotonically increasing delete file counts** (no sawtooth pattern): if delete
  file counts only ever grow and never drop after a compaction run, compaction
  is not keeping up with ingestion, is misconfigured (e.g., wrong `where` clause
  that excludes the hot partition), or is silently failing. A healthy compaction
  cycle produces a sawtooth: counts rise between runs and drop after each
  successful compaction. Flat or monotonically increasing counts mean the
  maintenance job is not functioning as intended. (See also: sawtooth diagnostic
  in metadata-tables.md.)
- **Alert on:** (1) compaction job missing its schedule for N consecutive periods;
  (2) delete file count not decreasing after a scheduled compaction run; (3)
  total snapshot count exceeding 2× the configured `retain_last` (indicates
  expiry is failing); (4) orphan file count growing faster than write rate
  (indicates aborted writes are not being cleaned up).
