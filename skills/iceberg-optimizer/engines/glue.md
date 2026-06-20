# AWS Glue / EMR / S3 Tables maintenance procedures

---

## AWS Glue and EMR

Glue and EMR run Spark under the hood, so all Spark procedures (see `engines/spark.md`)
apply directly. The catalog reference changes:

```sql
-- Glue Data Catalog as the catalog
CALL glue_catalog.system.rewrite_data_files(
  table => 'db.tbl', strategy => 'sort',
  sort_order => 'event_date ASC NULLS LAST',
  options => map('target-file-size-bytes','268435456')
);

CALL glue_catalog.system.expire_snapshots(
  table => 'db.tbl', older_than => TIMESTAMP '2025-01-01 00:00:00', retain_last => 10
);

CALL glue_catalog.system.remove_orphan_files(
  table => 'db.tbl', older_than => TIMESTAMP '2025-01-01 00:00:00', dry_run => true
);
```

Set `write.target-file-size-bytes` on the table so every writer (Glue, EMR, Athena)
produces target-sized files at write time:

```sql
ALTER TABLE glue_catalog.db.tbl SET TBLPROPERTIES (
  'write.target-file-size-bytes' = '268435456',
  'write.distribution-mode'      = 'hash'
);
```

---

## S3 Tables (AWS-managed Iceberg)

S3 Tables runs compaction *for you* as a managed service — no Spark cluster needed.
Since mid-2025, S3 Tables supports **sort and z-order** compaction natively via the
S3 Tables maintenance configuration.

```bash
# Enable automatic compaction (console or CLI)
aws s3tables put-table-maintenance-configuration \
  --table-bucket-arn arn:aws:s3tables:... \
  --namespace my_namespace \
  --name my_table \
  --type iceberg-compaction \
  --value '{"status":"enabled","settings":{"targetFileSizeMB":256}}'

# Enable automatic snapshot expiry
aws s3tables put-table-maintenance-configuration \
  --table-bucket-arn arn:aws:s3tables:... \
  --namespace my_namespace \
  --name my_table \
  --type iceberg-snapshot-management \
  --value '{"status":"enabled","settings":{"minSnapshotsToKeep":10,"maxSnapshotAgeHours":168}}'
```

For manual compaction or maintenance (e.g., targeted sort compaction) use Spark against
the S3 Tables Iceberg catalog endpoint. S3 Tables exposes a standard Iceberg REST catalog.

**Prefer S3 Tables automatic maintenance** when you are already on S3 Tables — it is
more efficient than running a separate Spark cluster for routine bin-pack compaction.
Use Spark only for sort/z-order compaction and manifest clustering.
