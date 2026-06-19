# Spark maintenance procedures

Requires the Iceberg SQL extensions (Spark 3.x); native in Spark 4.0.

```
spark.sql.extensions = org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
```

**Always run in this order:** compact → expire snapshots → remove orphans → rewrite manifests.

- **Compact before expire snapshots:** expiring snapshots makes previously-referenced delete
  files unreachable. Compact first to physically remove rows; expire afterward to dereference
  the pre-compaction snapshot.
- **Expire before orphan cleanup:** orphan cleanup too early risks deleting files still
  referenced by unexpired snapshots. Always expire first.

---

## rewrite_data_files — compaction

```sql
-- Bin-pack: resize small files to target
CALL cat.system.rewrite_data_files(
  table   => 'db.tbl',
  strategy => 'binpack',
  options  => map(
    'target-file-size-bytes',            '268435456',  -- 256 MB
    'min-input-files',                   '5',
    'max-concurrent-file-group-rewrites','10',
    'partial-progress.enabled',          'true',        -- commit in batches; fault-tolerant
    'remove-dangling-deletes',           'true'         -- absorb delete files
  ),
  where => 'event_date < current_date()'               -- compact only cold partitions
);

-- Sort: cluster by a key for data skipping
CALL cat.system.rewrite_data_files(
  table      => 'db.tbl',
  strategy   => 'sort',
  sort_order => 'event_date ASC NULLS LAST, tenant_id ASC NULLS LAST',
  options    => map('target-file-size-bytes','268435456')
);

-- Z-order: multi-dimensional clustering (2–4 high-cardinality cols; equality+range predicates only)
CALL cat.system.rewrite_data_files(
  table      => 'db.tbl',
  strategy   => 'sort',
  sort_order => 'zorder(tenant_id, event_time)',
  options    => map('rewrite-all','true','target-file-size-bytes','268435456')
);
```

Key options: `target-file-size-bytes` (default 512 MB), `min-input-files` (default 5),
`max-file-group-size-bytes` (default 100 GB — raise for huge partitions),
`max-concurrent-file-group-rewrites`, `partial-progress.enabled` +
`partial-progress.max-commits`, `rewrite-all`, `remove-dangling-deletes`.

---

## expire_snapshots

```sql
CALL cat.system.expire_snapshots(
  table                => 'db.tbl',
  older_than           => TIMESTAMP '2025-06-01 00:00:00.000',
  retain_last          => 10,       -- ALWAYS set > 1 in production
  max_concurrent_deletes => 10
);
```

Or set table properties for auto-expiry on every write:
`history.expire.max-snapshot-age-ms`, `history.expire.min-snapshots-to-keep`.

---

## remove_orphan_files (destructive — dry-run first)

```sql
CALL cat.system.remove_orphan_files(
  table      => 'db.tbl',
  older_than => TIMESTAMP '2025-05-29 00:00:00.000',  -- ≥ 3 days; ≥ longest write
  dry_run    => true
);
```

Never shorten `older_than` below the longest in-flight write window — doing so can
corrupt the table.

---

## rewrite_position_delete_files (MOR-specific)

Compacts position delete files without rewriting data files. Use when
`pos_delete_pressure` is high but data files are already well-sized.

```sql
CALL cat.system.rewrite_position_delete_files(
  table   => 'db.tbl',
  options => map(
    'target-file-size-bytes', '67108864',  -- 64 MB for delete files
    'partial-progress.enabled', 'true'
  )
);

-- Target a specific partition
CALL cat.system.rewrite_position_delete_files(
  table   => 'db.tbl',
  options => map('target-file-size-bytes', '67108864'),
  where   => 'event_date < current_date()'
);
```

For full physical removal of deleted rows (GDPR), `rewrite_data_files` is still required —
`rewrite_position_delete_files` leaves data files untouched.

---

## rewrite_manifests

```sql
-- Consolidate: merge many small manifests into fewer large ones
CALL cat.system.rewrite_manifests(table => 'db.tbl');

-- Cluster: reorder manifests so each covers a contiguous partition range
-- Enables manifest-level pruning — planner skips entire manifests for narrow filters
CALL cat.system.rewrite_manifests(
  table   => 'db.tbl',
  sort_by => array('event_date')   -- dominant partition / filter column
);
```

Cheap and concurrent with reads/writes. Target manifest size via
`commit.manifest.target-size-bytes` (default 8 MB).

---

## GDPR / compliance delete sequence (Spark)

```sql
-- 1. Delete the row
DELETE FROM db.tbl WHERE user_id = '<subject>';

-- 2. Compact immediately — must finish BEFORE snapshot expiry
CALL cat.system.rewrite_data_files(
  table   => 'db.tbl',
  options => map('remove-dangling-deletes','true')
);

-- 3. Expire snapshots so no historical snapshot retains the deleted row
CALL cat.system.expire_snapshots(
  table       => 'db.tbl',
  older_than  => NOW(),
  retain_last => 1
);

-- 4. Verify — both queries must return 0
SELECT COUNT(*) FROM db.tbl WHERE user_id = '<subject>';
```

**COW alternative:** set write modes to copy-on-write so DELETE rewrites files immediately,
eliminating the compaction step:

```sql
ALTER TABLE cat.db.tbl SET TBLPROPERTIES (
  'write.delete.mode' = 'copy-on-write',
  'write.update.mode' = 'copy-on-write',
  'write.merge.mode'  = 'copy-on-write'
);
```

---

## Table properties reference

**File size guidance:** Default `target-file-size-bytes` is 512 MB — rarely right for all workloads.

- **Streaming / CDC / high-write tables:** 10–64 MB. Many streaming environments benefit from
  smaller targets because large-file compaction cycles cost more than scan savings.
- **Mixed workloads (read + write):** 128–256 MB. Balances write throughput with scan efficiency.
- **Large analytic tables (Trino, Dremio over 10+ TB):** 256–512 MB. Large sequential scans
  handle big files well.
- **Wide tables (50+ columns) or nested schemas:** 64–256 MB. Wide schemas increase per-file
  memory pressure — smaller files reduce peak executor usage.

```sql
ALTER TABLE cat.db.tbl SET TBLPROPERTIES (
  'write.target-file-size-bytes'         = '268435456',  -- 256 MB
  'write.distribution-mode'              = 'hash',         -- curb thin-spread small files
  'commit.manifest.target-size-bytes'    = '8388608',
  'history.expire.max-snapshot-age-ms'   = '604800000',  -- 7 days
  'history.expire.min-snapshots-to-keep' = '10',
  'write.metadata.metrics.default'       = 'truncate(16)',
  'write.metadata.metrics.column.tenant_id' = 'full',
  'format-version'                       = '2'
);

-- Persisted sort order (all future writers cluster by these columns)
ALTER TABLE cat.db.tbl WRITE ORDERED BY event_date ASC NULLS LAST, tenant_id ASC NULLS LAST;
```

---

## Failure patterns and alerting

- **OOM / executor-lost on compaction:** partition too large for executor config. Raise
  `max-file-group-size-bytes` or increase executor memory; narrow `WHERE` clause.
- **Wildly inconsistent compaction durations:** partition skew. Profile with `$partitions`;
  use partition-targeted `WHERE` for the outlier.
- **Delete file counts never drop (no sawtooth):** compaction is not keeping up, is
  misconfigured (wrong `where` clause), or silently failing. A healthy compaction cycle
  produces a sawtooth — counts rise between runs and drop after each run.
- **Alert on:** (1) compaction missed N consecutive schedules; (2) delete-file count
  unchanged after scheduled run; (3) snapshot count > 2× `retain_last`; (4) orphan-file
  count growing faster than write rate.

---

## Access control

- Maintenance jobs need: data-file write/delete access + metadata-write access.
- `remove_orphan_files` is destructive — require explicit approval, always `dry_run` first,
  scope to specific S3/GCS prefixes; never grant bucket-wide delete.
- Use catalog RBAC (Polaris, Nessie, Unity) to restrict which tables a maintenance role
  can call procedures on. Storage permissions are defense-in-depth, not the primary control.
- Maintenance identity should not have query or data-write access beyond maintenance scope.
