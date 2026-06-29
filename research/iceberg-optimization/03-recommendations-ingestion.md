# Part II · Chapter 3 — Ingestion optimization

> Most physical problems are *created at write time.* The cheapest small file is
> the one you never wrote. This chapter is about shaping the write so the table
> stays healthy without leaning entirely on after-the-fact maintenance. Drive it
> from the [Stage 3 ingestion analysis](01-methodology-and-analysis.md#stage-3--ingestion-log-analysis-how-the-table-is-written).

The single most important ingestion variable is **commit cadence**, because every
Iceberg commit creates a snapshot and ≥1 file per partition written. Get that
right and most other problems shrink.

---

## 3.1 Pick the ingestion model from the latency SLA

| Model | Freshness | File/metadata pressure | Use when (Stage 4 SLA) |
|---|---|---|---|
| **Batch** | hours+ | Lowest — few big commits, idempotent, easy retries | Backfills, daily loads, slowly-changing data; predictability > speed. |
| **Micro-batch** | minutes | Moderate — tune the interval | Near-real-time analytics, SaaS/API polling, file drops. |
| **Streaming** | seconds | Highest — frequent commits, small files | Fraud, monitoring, personalization; seconds matter. |

**Don't buy more freshness than the consumers asked for.** Stage 4 interviews
routinely reveal that a "real-time" table only needs 5-minute freshness — which
lets you slow commits from 30 s to minutes and eliminate the small-file problem at
the source. This is the highest-leverage ingestion fix and it costs nothing.

---

## 3.2 Commit cadence (the small-file root cause)

A streaming writer committing every 30 s makes ~2,880 snapshots/day, each writing
at least one file per partition it touches. With any partition fan-out, that's the
classic tiny-file explosion you saw in Stage 2.

**Levers:**

- **Lengthen the commit/checkpoint interval** to the largest value the SLA
  tolerates. Moving 30 s → 2–5 min cuts file and snapshot count ~4–10×.
- **Decouple commit interval from processing latency** where the engine allows —
  process continuously, commit less often.
- **Accept small files + compact** only when the SLA genuinely needs sub-minute
  freshness. Then size compaction to keep up (see [maintenance](04-recommendations-maintenance.md)).

Engine specifics:

- **Flink:** commit frequency = **checkpoint interval**
  (`execution.checkpointing.interval`). This is *the* knob. Also tune the sink's
  `write-target-file-size-bytes` and consider `write.distribution-mode=hash` so a
  checkpoint writes one file per partition rather than many.
- **Spark Structured Streaming:** the **trigger interval** sets micro-batch/commit
  cadence. `Trigger.ProcessingTime("3 minutes")` over `Trigger.Continuous`/default
  for Iceberg sinks. `write.distribution-mode=none` for cheapest streaming writes,
  then compact.
- **Kafka Connect / Tableflow / Redpanda:** the connector's commit interval and
  records-per-commit; raise them to batch more per snapshot.

---

## 3.3 Control write distribution & fan-out at the source

Fan-out (one task writing to many partitions) multiplies the small-file problem by
the partition count. Fix it write-side before relying on compaction:

- Set **`write.distribution-mode=hash`** (or `range` for sorted tables) so the
  engine shuffles rows to one task per partition — see
  [§2.4](02-recommendations-table-properties.md#24-write-distribution-mode).
- For streaming where the shuffle is too expensive, enable
  **`write.spark.fanout.enabled=true`** (Spark) to avoid per-partition sort
  buffering, accepting more open files in exchange for not failing/spilling.
- **Pre-aggregate or repartition** in the job (`.repartition(partitionCols)`)
  before the write when the engine doesn't do it for you.

---

## 3.4 Match the write operation to the mutation pattern

Iceberg supports `append`, `overwrite` (by filter/partition), row-level
`update`/`delete`, and `MERGE` (upsert). Choose deliberately:

- **Append-only facts** → plain `append`. Cheapest, fully concurrent across
  disjoint partitions. The default for event/log/telemetry ingestion.
- **Partition refresh / reprocessing** → **partition-scoped `overwrite`** (dynamic
  partition overwrite) so you replace only affected partitions, minimizing write
  amplification — not a full-table rewrite.
- **CDC / upserts / SCD** → **`MERGE`** with **MOR** mode (see
  [§2.5](02-recommendations-table-properties.md#25-copy-on-write-vs-merge-on-read)).
  Flink and Spark both support MERGE against Iceberg. Position deletes where the
  engine knows the row; equality deletes where it doesn't (and then compact hard).
- **GDPR/right-to-erasure deletes** → row-level `delete`, then ensure the multi-step
  physical-erasure flow in [§4.6](04-recommendations-maintenance.md#46-regulatory-deletion-gd-pr--cc-pa).

---

## 3.5 Concurrency & commit conflicts

Iceberg uses **optimistic concurrency**: each commit does an atomic
compare-and-swap on the table's metadata pointer; if another writer committed
first, the loser retries. This scales without locks, but under multiple concurrent
writers you must plan for conflicts:

- **Partition your writers** so they touch **disjoint partitions** — two appends to
  different partitions never conflict; two overlapping overwrites do.
- Raise **`commit.retry.num-retries`** and tune backoff
  (`commit.retry.min-wait-ms`) for multi-writer tables.
- Conflicting **overwrites** are the usual culprit — serialize them or scope them
  tightly. Reserve full-table overwrites for maintenance windows.
- Failed/retried commits leave **orphan files** behind → ensure orphan cleanup runs
  (see [§4.4](04-recommendations-maintenance.md#44-orphan-file-removal)).

---

## 3.6 Schema evolution & data quality at ingest

Iceberg evolves schema safely via **stable field IDs** (add/rename/reorder/drop
without rewriting data). To keep that safety, the *pipeline* must handle drift:

- **Validate incoming schema** against the table each run/continuously (schema
  registry for streaming: Confluent/Redpanda).
- Choose a drift strategy per field criticality:
  - **Fail-fast** on critical fields (reject bad data early).
  - **Controlled casting** on optional/evolving fields (int→long, string→timestamp).
  - **Dead-letter queue (DLQ)** for unresolvable rows — keep ingestion flowing,
    capture rejects for inspection. In practice, combine all three.
- Don't build a bespoke schema-history store — Iceberg's metadata tables already
  record schema evolution alongside snapshots (audit trail for free).

---

## 3.7 What each ingestion tool does (and doesn't) do for you

The tool determines how much of the above you own vs inherit. Key Iceberg-relevant
facts:

| Tool | Model | Iceberg write story | What it automates / caveats |
|---|---|---|---|
| **Spark** | batch / micro-batch / structured streaming | Native (Iceberg Spark runtime); append/overwrite/MERGE/streaming. Also the canonical **maintenance** engine. | You own commit cadence (trigger), distribution, and maintenance. Most control, most responsibility. |
| **Flink** | streaming (+ batch) | Native Iceberg Sink; exactly-once via checkpoint↔commit coordination; CDC/MERGE; position deletes. | Checkpoint interval = commit cadence (the key knob). Watch equality-delete + same-sequence-number upsert pitfalls; compact frequently. |
| **NiFi** | flow-based micro-batch | `PutIceberg` (1.19.0–1.23.x) writes to **existing** tables via a catalog service. | **Does not create tables or compact** — an external engine (Spark/Trino) must do DDL + maintenance. NiFi 2.0 dropped direct Iceberg; often used to land files for a downstream writer. Batch flowfiles to avoid tiny commits. |
| **dbt** | batch (warehouse-executed SQL) | Iceberg materializations (`table`/`incremental`/dynamic) on Spark, Snowflake (1.9+), and others. | You set table props/partitioning via model `config`. Incremental models use MERGE — pick `merge`/`append`/`insert_overwrite` strategy. Maintenance is the platform's or a separate job's responsibility. |
| **Kafka Connect (Iceberg sink)** | streaming | Native sink; commit interval batches records. | Raise commit interval/records-per-commit to avoid tiny files. |
| **Confluent Tableflow** | streaming | Materializes Kafka topics → Iceberg; auto compaction, schema-registry evolution. | **Append-only** (no upsert/retract); one catalog per cluster; external catalog needs BYO storage. |
| **Redpanda** | streaming | Topic→Iceberg (spec v2); REST or filesystem catalog; topic-level partitioning; DLQ on schema failure. | Extra CPU for translation; producer backpressure if under-resourced. |
| **Fivetran / Airbyte / Qlik** | managed ELT (batch/CDC) | Write Parquet→Iceberg via REST catalog; MOR with equality-delete dedup (Airbyte). | Managed services **automate compaction, snapshot/orphan cleanup, stats** (Fivetran, Qlik) — you inherit maintenance. Verify their defaults match your profile. |
| **Cloud-native (Glue / ADF / Dataflow / Firehose)** | batch + streaming | Glue (Spark) native; ADF Iceberg sink to ADLS; Dataflow lands Parquet for later registration; Firehose → S3/Iceberg. | Maturity varies; check catalog integration and whether the service does any maintenance (mostly it doesn't). |

> See the [platform playbooks](05-platform-playbooks.md) for the full three-category
> mapping (table / ingestion / maintenance) on Databricks, Snowflake, bespoke,
> NiFi, Flink, and dbt.

→ Continue to [Maintenance optimization](04-recommendations-maintenance.md).
