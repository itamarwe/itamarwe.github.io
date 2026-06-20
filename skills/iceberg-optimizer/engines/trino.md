# Trino maintenance procedures

Trino uses `EXECUTE` (not `CALL`) and **duration strings** (not timestamps). Enforce
catalog-level minimum-retention floors — you cannot undercut them per-call.

Trino supports: bin-pack compaction, snapshot expiry, orphan removal, manifest consolidation.
Trino does **not** support sort/z-order compaction or manifest clustering — use Spark for those.

---

## Compaction (bin-pack only)

```sql
-- Bin-pack; WHERE targets specific partitions
ALTER TABLE cat.db.tbl EXECUTE optimize(file_size_threshold => '256MB')
  WHERE event_date >= DATE '2025-01-01';
```

No sort or z-order strategies in Trino's `optimize`. For sort/z-order, use Spark.
Set the table sort order so Trino *writes* clustered data going forward:

```sql
ALTER TABLE cat.db.tbl SET PROPERTIES sorted_by = ARRAY['event_date', 'tenant_id'];
```

---

## Expire snapshots

```sql
-- retention_threshold must be ≥ catalog min-retention floor (default 7d)
ALTER TABLE cat.db.tbl EXECUTE expire_snapshots(retention_threshold => '7d');
```

---

## Remove orphan files

```sql
ALTER TABLE cat.db.tbl EXECUTE remove_orphan_files(retention_threshold => '7d');
```

---

## Rewrite manifests (consolidate only)

```sql
-- Consolidates manifests; does NOT sort by partition (use Spark for clustering)
ALTER TABLE cat.db.tbl EXECUTE optimize_manifests;
```

---

## Format version upgrade

```sql
ALTER TABLE cat.db.tbl SET TBLPROPERTIES ('format-version' = '2');
```

---

## Capability comparison: Spark vs Trino

| Operation | Spark | Trino | Notes |
|---|---|---|---|
| Format upgrade | ✓ | ✓ | `ALTER TABLE SET TBLPROPERTIES` in both |
| Write-time sort order | `WRITE ORDERED BY col` | `SET PROPERTIES sorted_by` | |
| Bin-pack compaction | ✓ | ✓ | Trino: simpler; Spark: more options |
| Sort / z-order compaction | ✓ | ✗ | Spark only |
| Expire snapshots | ✓ | ✓ | Trino enforces catalog minimum retention |
| Remove orphan files | ✓ | ✓ | Same note |
| Rewrite manifests (consolidate) | ✓ | ✓ | |
| Rewrite manifests (cluster by partition) | ✓ | ✗ | `sort_by` is Spark-only |
| Rewrite position delete files | ✓ | ✗ | Spark-only procedure |

**Practical guidance:** Use Trino for lightweight maintenance (expiry, bin-pack, orphan
cleanup) when a Spark cluster is costly. Use Spark for any operation requiring sort order,
z-order, manifest clustering, or position delete rewriting.

---

## GDPR compliance sequence (Trino)

```sql
-- 1. Delete the row
DELETE FROM cat.db.tbl WHERE user_id = '<subject>';

-- 2. Compact to physically remove the row (Trino bin-pack)
ALTER TABLE cat.db.tbl EXECUTE optimize(file_size_threshold => '256MB');

-- 3. Expire snapshots
ALTER TABLE cat.db.tbl EXECUTE expire_snapshots(retention_threshold => '1d');

-- 4. Verify — must return 0
SELECT COUNT(*) FROM cat.db.tbl WHERE user_id = '<subject>';
```

For sort/z-order compaction as part of GDPR cleanup, run Step 2 via Spark instead.
