# Ingestion pipeline configuration

This file covers write-time changes: fixing the ingestion pipeline before compacting its
output. Loaded when Group 2 (Ingestion) actions are recommended.

---

## Identifying the ingestion pipeline type

Signal combinations from profile.json + workload.json that identify the writer:

| Signal | Most likely writer |
|---|---|
| `write_cadence = streaming`, `avg_added_file_mb < 5`, `thin_spread = true` | Flink (default config), or Spark Structured Streaming with short trigger intervals |
| `write_cadence = streaming`, `avg_added_file_mb ≥ 50` | Flink with manual file sizing or large checkpoint interval |
| `write_cadence = micro_batch` (5s–5min commits) | Spark Structured Streaming |
| `write_cadence = batch`, large commits, `late_data = false` | Spark batch ETL or dbt |
| `operation_mix` has high `overwrite` + `append` | CDC connector (Debezium, DeltaStreamer, Hudi-Iceberg bridge) |
| `eq_delete_pressure > 0.05`, `operation_mix` has `merge` | Merge-on-read CDC (MOR mode) — Iceberg sink with equality deletes |
| `pos_delete_pressure > 0.2`, no equality deletes | Copy-on-write CDC or MOR with position deletes |

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

Fixing checkpoint/commit interval is the highest-leverage ingestion action — it reduces
file count at source rather than compacting the output repeatedly.
