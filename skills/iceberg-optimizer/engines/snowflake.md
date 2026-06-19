# Snowflake Iceberg maintenance procedures

Snowflake supports two Iceberg integration modes with different maintenance implications.
**Identify the mode first** — the procedures differ significantly.

---

## Mode 1: Snowflake-managed Iceberg tables

Snowflake acts as the catalog and manages the table metadata and storage. Snowflake handles
background compaction automatically for most workloads. Manual maintenance is still possible
and sometimes necessary.

### Detect current state

```sql
-- List Iceberg tables and mode
SHOW ICEBERG TABLES;

-- Table properties (snapshot count, compaction status, format version)
SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
  WHERE "kind" = 'ICEBERG';

-- Snapshot history
SELECT * FROM TABLE(
  INFORMATION_SCHEMA.ICEBERG_TABLE_SNAPSHOTS(
    TABLE_NAME => 'MY_TABLE',
    SCHEMA_NAME => 'MY_SCHEMA'
  )
) ORDER BY committed_at DESC LIMIT 20;
```

### Compaction

Snowflake performs background compaction automatically. To trigger manual compaction:

```sql
-- Manual compaction (available in Snowflake Enterprise+ with Iceberg tables)
ALTER ICEBERG TABLE my_db.my_schema.my_table COMPACT;
```

For write-time target file size (controls the size of files written by Snowflake):

```sql
ALTER ICEBERG TABLE my_db.my_schema.my_table SET
  FILE_FORMAT = (TYPE = PARQUET SNAPPY_COMPRESSION = TRUE)
  TARGET_FILE_SIZE = 268435456;  -- 256 MB
```

### Snapshot retention

```sql
-- Set retention window (Snowflake expires older snapshots automatically)
ALTER ICEBERG TABLE my_db.my_schema.my_table
  SET SNAPSHOT_RETENTION_TIME = 7;  -- days

-- Manual snapshot expiry (removes snapshots older than N days)
ALTER ICEBERG TABLE my_db.my_schema.my_table
  EXECUTE EXPIRE_SNAPSHOTS(RETENTION_THRESHOLD => '7 days');
```

### Sort order / clustering

Snowflake Iceberg tables support Snowflake's native clustering as of 2024:

```sql
-- Define a clustering key (Snowflake manages reclustering automatically)
ALTER ICEBERG TABLE my_db.my_schema.my_table
  CLUSTER BY (event_date, tenant_id);

-- Check clustering state
SELECT SYSTEM$CLUSTERING_INFORMATION('my_db.my_schema.my_table');
```

Snowflake's automatic clustering runs asynchronously and does not use the Iceberg sort-order
spec. It produces Snowflake micro-partitioned layout. For cross-engine compatibility, prefer
setting an Iceberg-native sort order via Spark if the table is also read by Trino/Athena.

### Format version upgrade

```sql
-- Check current format version
SHOW TBLPROPERTIES my_db.my_schema.my_table;

-- Upgrade to v2 (enables row-level deletes in other engines reading this table)
-- Note: Snowflake Iceberg tables created after 2024 default to v2.
ALTER ICEBERG TABLE my_db.my_schema.my_table
  SET TBLPROPERTIES ('format-version' = '2');
```

### GDPR / compliance sequence

```sql
-- 1. Delete the row
DELETE FROM my_db.my_schema.my_table WHERE user_id = '<subject>';

-- 2. Trigger compaction to physically remove the row
ALTER ICEBERG TABLE my_db.my_schema.my_table COMPACT;

-- 3. Expire snapshots (remove pre-delete snapshot)
ALTER ICEBERG TABLE my_db.my_schema.my_table
  EXECUTE EXPIRE_SNAPSHOTS(RETENTION_THRESHOLD => '1 days');

-- 4. Verify
SELECT COUNT(*) FROM my_db.my_schema.my_table WHERE user_id = '<subject>';
```

---

## Mode 2: External Iceberg tables (Snowflake reads an external catalog)

Snowflake reads a table whose Iceberg metadata lives in an external catalog (AWS Glue,
Polaris, REST catalog) and whose files live in external object storage (S3, GCS).

**Snowflake is read-only in this mode.** All maintenance (compaction, snapshot expiry,
orphan cleanup) runs via Spark, Trino, or another engine. Snowflake does not write to
external Iceberg tables.

### Refresh after external maintenance

After running maintenance in Spark/Trino, refresh Snowflake's view of the table:

```sql
-- Refresh Snowflake's metadata cache from the external catalog
ALTER ICEBERG TABLE my_db.my_schema.my_external_table REFRESH;

-- Or refresh to a specific snapshot
ALTER ICEBERG TABLE my_db.my_schema.my_external_table REFRESH '<snapshot-id>';
```

Snowflake auto-refreshes on a schedule; manual refresh accelerates propagation after
a maintenance run.

### Verify catalog connectivity

```sql
-- Check external volume and catalog integration
SHOW INTEGRATIONS LIKE 'my_catalog_integration%';
SHOW EXTERNAL VOLUMES LIKE 'my_external_volume%';

-- Test that Snowflake sees the current snapshot
SELECT SYSTEM$ICEBERG_METADATA_SCHEMA('my_db.my_schema.my_external_table');
```

---

## Engine selection for Snowflake environments

| Operation | Snowflake (managed) | Snowflake (external) | Spark / Trino |
|---|---|---|---|
| Bin-pack compaction | Auto + manual COMPACT | ✗ (use Spark) | ✓ |
| Sort / z-order compaction | Native clustering | ✗ (use Spark) | Spark only |
| Expire snapshots | ✓ | ✗ (use Spark) | ✓ |
| Remove orphan files | Managed automatically | ✗ (use Spark) | ✓ |
| GDPR row deletion | ✓ (DELETE + COMPACT) | Run in Spark; REFRESH | ✓ |
| Format version upgrade | ✓ | ✗ (use Spark) | ✓ |

**Recommendation:** For Snowflake-managed tables, rely on Snowflake's automatic maintenance
for routine compaction; use `COMPACT` and `EXPIRE_SNAPSHOTS` for ad-hoc or compliance
operations. For external tables, run all maintenance in Spark/Trino and refresh Snowflake
afterward.
