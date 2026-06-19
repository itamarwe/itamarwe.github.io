# Ingestion pipeline configuration

This file covers write-time changes: fixing the ingestion pipeline before compacting its
output. Loaded when Group 2 (Ingestion) actions are recommended.

---

## Identifying the ingestion pipeline type

Signal combinations from profile.json + workload.json that identify the writer:

| Signal | Most likely writer |
|---|---|
| `write_cadence = streaming`, `avg_added_file_mb < 5`, `thin_spread = true` | Flink (default config) or Spark Structured Streaming with short trigger intervals |
| `write_cadence = streaming`, `avg_added_file_mb ≥ 50` | Flink with large checkpoint interval or manual file sizing |
| `write_cadence = micro_batch` (5s–5min commits) | Spark Structured Streaming |
| `write_cadence = batch`, large commits, `late_data = false` | Spark batch ETL or dbt |
| `write_cadence = batch`, small-to-medium commits, irregular intervals | Apache NiFi (`PutIcebergRecord`) or Beam/Dataflow batch pipeline |
| `write_cadence = streaming`, small files, `thin_spread = false`, low parallelism | Apache Beam / Dataflow streaming with low `numShards` |
| `operation_mix` has high `overwrite` + `append` | CDC connector (Debezium, DeltaStreamer, Hudi-Iceberg bridge) or Airbyte full-refresh |
| `operation_mix` dominated by full partition `overwrite`, regular cadence | Airbyte full-refresh or Fivetran managed sync |
| `eq_delete_pressure > 0.05`, `operation_mix` has `merge` | Merge-on-read CDC (MOR mode) — Iceberg sink with equality deletes |
| `pos_delete_pressure > 0.2`, no equality deletes | Copy-on-write CDC or MOR with position deletes |
| `write_cadence = batch`, very large one-off commits, then silence | AWS DMS migration load or historical backfill |

**Always show derived writer type to the user and ask them to confirm:**
"Based on commit cadence (~30s gaps, ~0.5 MB files per commit), this looks like a Flink streaming job without distribution mode set. Is that right? What connector / framework writes to this table?"

---

## Action J — Write-time distribution and file size tuning

### Flink Iceberg sink

The most common Flink thin-spread root cause: Flink writes one file per checkpoint per
task per partition. With 50 partitions and 10 tasks, that's 500 files per checkpoint.

```xml
<!-- Iceberg Flink sink configuration -->
<flink-iceberg-sink
  write.distribution-mode="hash"            <!-- routes rows to a single task per partition -->
  write.target-file-size-bytes="268435456"  <!-- 256 MB buffer before flushing -->
  sink.parallelism="4"                      <!-- match to partition count / target throughput -->
/>
```

Or via the FlinkSQL / DataStream API:

```java
// DataStream API
IcebergSink.forRowData(dataStream)
  .table(table)
  .tableLoader(tableLoader)
  .distributionMode(DistributionMode.HASH)  // routes by partition key — eliminates thin spread
  .writeParallelism(4)
  .build();
```

```sql
-- FlinkSQL sink option
INSERT INTO catalog.db.tbl
  /*+ OPTIONS('write.distribution-mode'='hash') */
SELECT ...;
```

**Checkpoint interval tuning:** longer checkpoint intervals mean larger files per checkpoint.
A 5-minute checkpoint with 256 MB target produces well-sized files from a moderate-throughput
stream:

```yaml
# Flink config (flink-conf.yaml or programmatic)
execution.checkpointing.interval: 300000   # 5 minutes
execution.checkpointing.mode: EXACTLY_ONCE
```

### Spark Structured Streaming

```scala
df.writeStream
  .format("iceberg")
  .option("write.distribution-mode", "hash")     // eliminates thin spread
  .option("write.target-file-size-bytes", "268435456")
  .option("write.spark.fanout.enabled", "false")  // disable if not needed
  .trigger(Trigger.ProcessingTime("5 minutes"))   // longer trigger → larger files
  .option("checkpointLocation", "/path/to/checkpoint")
  .start("catalog.db.tbl")
```

### Spark batch

```python
df.write \
  .format("iceberg") \
  .option("write.distribution-mode", "hash") \
  .option("write.target-file-size-bytes", "268435456") \
  .mode("append") \
  .save("catalog.db.tbl")
```

### Apache NiFi (`PutIcebergRecord`)

NiFi's `PutIcebergRecord` processor (NiFi 2.x+) commits per flow-file batch. The
default batch size is small, so each processor execution can produce many tiny files
if the flow rate is high.

Key processor properties to tune:

```
Maximum File Size     → 268435456 (256 MB)  # buffer before flushing a file
```

NiFi does not expose `write.distribution-mode` directly — configure it as a table
property so every writer (including NiFi) inherits it:

```sql
ALTER TABLE cat.db.tbl SET TBLPROPERTIES (
  'write.distribution-mode'      = 'hash',
  'write.target-file-size-bytes' = '268435456'
);
```

**Thin-spread diagnosis for NiFi:** If each processor execution touches many
partitions (high fan-out), verify the catalog is configured with a partition spec
that matches the data distribution. NiFi does not route rows to tasks by partition —
unlike Flink, it relies entirely on the table-level `write.distribution-mode` property
to avoid thin spread.

**NiFi flow-file batching:** To increase effective batch size without changing the
processor, increase the upstream queue's batch count or merge small flow-files with
`MergeContent` before `PutIcebergRecord`.

### Apache Beam / Google Dataflow

Beam's `IcebergIO` sink (Beam 2.54+) controls file sizing and parallelism via
pipeline options. The defaults often produce too many shards (one per bundle), which
causes thin spread especially in Dataflow's auto-scaling mode.

```java
// Beam Java SDK — write to Iceberg
PCollection<Row> rows = ...;
rows.apply(
  IcebergIO.writeToDynamicDestinations(
    IcebergCatalogConfig.builder()
      .setCatalogName("my_catalog")
      .setCatalogProperties(ImmutableMap.of(...))
      .build()
  )
  .to(DynamicDestinations.singleTable(
    TableIdentifier.of("db", "tbl")
  ))
  .withMaxBytesPerFile(268_435_456L)   // 256 MB — key knob
  .withNumShards(4)                    // reduce from default; match to partition count
);
```

**Python SDK (Apache Beam 2.56+):**

```python
rows | beam.io.iceberg.WriteToIceberg(
    table=TableIdentifier(["db", "tbl"]),
    catalog_name="my_catalog",
    catalog_properties={...},
    max_bytes_per_file=268_435_456,
    num_shards=4,
)
```

**Dataflow-specific guidance:**
- `numShards` controls parallelism per partition. Too high → thin spread (many small
  files per partition). Too low → bottleneck at high throughput. Start at 2–4 and
  tune up only if you see write-side backpressure.
- In streaming Dataflow, Beam commits on each bundle boundary. Long streaming jobs with
  small bundles produce many tiny commits. Prefer setting `maxBytesPerFile` over
  reducing `numShards` alone.
- Set table-level `write.target-file-size-bytes` as a fallback for other writers:

```sql
ALTER TABLE cat.db.tbl SET TBLPROPERTIES (
  'write.target-file-size-bytes' = '268435456'
);
```

---

## Action K — Write-time sort order

Persisted on the table — all future writers cluster by the sort key at zero extra
maintenance cost. Do not set K if `has_sort_order = true` in the profile.

```sql
-- Spark: persisted sort order (writers cluster by these columns)
ALTER TABLE cat.db.tbl WRITE ORDERED BY event_date ASC NULLS LAST, tenant_id ASC NULLS LAST;

-- Trino: equivalent via table property
ALTER TABLE cat.db.tbl SET PROPERTIES sorted_by = ARRAY['event_date', 'tenant_id'];

-- Remove sort order
ALTER TABLE cat.db.tbl WRITE UNORDERED;   -- Spark
```

**Sequence:** Apply J (distribution mode) first, then K (sort order). Without
`distribution-mode=hash`, sort order has limited effect — rows for the same sort key
land in different tasks and produce many small sorted files rather than fewer large ones.

---

## Managed connectors (Airbyte, Fivetran, AWS DMS)

These connectors expose fewer tunable knobs than Flink or Spark. The most impactful
lever is **write mode** — choosing between full-refresh (partition overwrite) and
incremental append. The wrong write mode is the most common source of file health
problems in managed connector pipelines.

### Airbyte

Airbyte's Iceberg destination supports two write modes:

| Write mode | Behavior | File health impact |
|---|---|---|
| `append` | New records appended as new data files | Small files accumulate if sync frequency is high; bin-pack compaction (Action A) is required |
| `overwrite` (full refresh) | Drops and rewrites the entire table or partition each sync | Large files per sync; no small-file accumulation, but high write cost and no history |
| `merge` (upsert, if supported) | Generates equality-delete files via MOR | Equality-delete pressure accumulates if compaction doesn't keep up |

**Recommendation:** Use `append` for append-only sources. Use `merge` only if the source
has true CDC (primary key updates/deletes). Avoid `overwrite` for large tables — the
write cost grows linearly with table size.

Configure in Airbyte's Iceberg destination connector settings:
- **Destination type:** `Iceberg`
- **Write method:** `Append`, `Overwrite`, or `Merge` depending on source type
- **Target file size (if exposed):** set to 256 MB

For small-file accumulation from high-frequency Airbyte `append` syncs: schedule
bin-pack compaction (Action A) after each sync batch, or daily if syncs are frequent.

### Fivetran

Fivetran's Iceberg connector is fully managed — write mode, file sizing, and commit
frequency are not user-configurable. Fivetran handles compaction internally for
Fivetran-managed tables.

**Practical guidance:**
- If you observe small-file accumulation from Fivetran syncs, check whether Fivetran's
  background compaction is enabled for your connector (available in Enterprise plans).
- For Fivetran writing to an external Iceberg catalog (S3 + Glue), you own the
  compaction. Schedule Action A (bin-pack) on a cadence slightly longer than the
  Fivetran sync frequency.
- Fivetran does not expose `write.distribution-mode`. Set it as a table property:
  ```sql
  ALTER TABLE cat.db.tbl SET TBLPROPERTIES ('write.distribution-mode' = 'hash');
  ```

### AWS DMS (Database Migration Service)

AWS DMS writes to Iceberg via the S3 target with Glue Data Catalog integration.
It is primarily a migration tool — most deployments are one-time full-load jobs
rather than ongoing CDC streams.

**Full-load (migration) mode:** DMS writes large Parquet files; file health is
typically good. Run orphan file cleanup and snapshot expiry after migration completes.

**CDC mode (ongoing replication):** DMS in CDC mode can generate small files and
equality-delete pressure if the source has a high update rate.

```
# DMS task settings for Iceberg targets (set in the DMS console or API)
TargetMetadata:
  ParquetVersion: parquet_2_0
  EnableStatistics: true
  # DMS does not expose Iceberg write.distribution-mode directly.
  # Set on the table after initial load:
```

```sql
-- After DMS creates the table, apply write-time settings for any subsequent loads
ALTER TABLE glue_catalog.db.dms_tbl SET TBLPROPERTIES (
  'write.distribution-mode'      = 'hash',
  'write.target-file-size-bytes' = '268435456'
);
```

For ongoing DMS CDC, monitor `eq_delete_pressure` — if it rises above 0.05,
schedule Action E1 (equality-delete compaction) and consider whether COW mode
is feasible for the source table's update rate.

---

## CDC connector write-mode tuning

CDC pipelines (Debezium, Kafka Connect Iceberg sink, AWS DMS, Hudi-Iceberg) can be
configured for merge-on-read (MOR) or copy-on-write (COW):

```sql
-- Switch from MOR (accumulates delete files) to COW (rewrites at write time)
-- Higher write cost, lower read cost, eliminates equality-delete accumulation
ALTER TABLE cat.db.tbl SET TBLPROPERTIES (
  'write.delete.mode' = 'copy-on-write',
  'write.update.mode' = 'copy-on-write',
  'write.merge.mode'  = 'copy-on-write'
);
```

**When to prefer COW:**
- `eq_delete_pressure` grows faster than compaction can reduce it.
- Interactive queries; high read frequency; every scan paying equality-delete join cost.
- Regulatory: COW + snapshot expiry achieves physical deletion without a separate compaction step.

**When to keep MOR:**
- Very high update throughput where COW write amplification is unacceptable.
- Append-dominant with occasional updates: MOR write cost is near-zero for inserts.

---

## Streaming checkpoint / commit tuning

For reducing small-file creation at the source (before any compaction):

| Framework | Knob | Target value | Effect |
|---|---|---|---|
| Flink | `execution.checkpointing.interval` | 5–15 min | Larger files per commit |
| Flink | `write.target-file-size-bytes` | 128–256 MB | Buffer more before flushing |
| Flink | `write.distribution-mode` | `hash` | One task per partition — no thin spread |
| Spark SS | `trigger(ProcessingTime(...))` | 5–15 min | Larger micro-batches |
| Spark SS | `write.target-file-size-bytes` | 128–256 MB | Larger output files |
| Kafka Connect | `iceberg.tables.dynamic.enabled` | `true` | Fan-out partitions correctly |
| Kafka Connect | `file.commit.mode` | `commit-based` | Commit when buffer full, not per-interval |
| NiFi | `Maximum File Size` (processor) | 256 MB | Buffer before committing a file |
| NiFi | `write.distribution-mode` (table property) | `hash` | Inherited by all writers including NiFi |
| Beam / Dataflow | `withMaxBytesPerFile` | 268435456 | Buffer before closing a shard |
| Beam / Dataflow | `withNumShards` | 2–4 | Fewer shards → fewer, larger files per partition |
| Airbyte | write method | `append` (not `overwrite`) | Avoid full-table rewrites on each sync |
| AWS DMS CDC | `write.distribution-mode` (table property) | `hash` | Apply after initial load |

Fixing checkpoint/commit interval is the highest-leverage ingestion action — it reduces
file count at source rather than compacting the output repeatedly.
