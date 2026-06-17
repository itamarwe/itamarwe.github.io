# Maintenance procedures by engine

Verified against Apache Iceberg docs, Spark procedures, and the Trino 481 Iceberg
connector. **Always run in this order:** compact → expire snapshots → remove
orphans → rewrite manifests. Never remove orphans before expiring snapshots
(expiry dereferences files; orphan removal then deletes them).

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

### rewrite_manifests

```sql
CALL cat.system.rewrite_manifests(table => 'db.tbl');           -- consolidate
CALL cat.system.rewrite_manifests(table => 'db.tbl', sort_by => array('event_date'));
```
Cheap, concurrent with reads/writes. Output size via
`commit.manifest.target-size-bytes`.

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

-- Rewrite/cluster manifests by top-level partition (Trino ~479+; PR #25378)
ALTER TABLE cat.db.tbl EXECUTE optimize_manifests;
```

Trino does **not** expose sort/z-order *strategies* in `optimize` (bin-pack
only). For sort/z-order rewrites, use Spark. Set the table sort order so Trino
writes clustered data: `ALTER TABLE cat.db.tbl SET PROPERTIES sorted_by = ARRAY['event_date'];`

| Operation | Spark | Trino |
|---|---|---|
| Compact data | `CALL …rewrite_data_files(...)` | `ALTER TABLE t EXECUTE optimize(...)` |
| Sort / z-order | `strategy => 'sort' / zorder(...)` | not available (use Spark) |
| Expire snapshots | `CALL …expire_snapshots(older_than => TIMESTAMP …)` | `EXECUTE expire_snapshots(retention_threshold => '7d')` |
| Remove orphans | `CALL …remove_orphan_files(...)` | `EXECUTE remove_orphan_files(retention_threshold => '7d')` |
| Rewrite manifests | `CALL …rewrite_manifests(...)` | `EXECUTE optimize_manifests` |

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

## Table properties worth setting

```sql
ALTER TABLE cat.db.tbl SET TBLPROPERTIES (
  'write.target-file-size-bytes'           = '268435456',  -- 256 MB
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
