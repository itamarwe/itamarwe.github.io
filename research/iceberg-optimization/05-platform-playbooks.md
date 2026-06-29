# Part II · Chapter 5 — Platform playbooks

> The same three categories — **table properties / ingestion / maintenance** —
> but the *division of labor* changes per platform. The big question on every
> platform is: **what does it automate, and what do you still own?** Managed
> platforms increasingly run compaction/clustering/expiration for you; bespoke
> stacks give you every knob and every chore. Match the platform's automation to
> your [optimization profile](01-methodology-and-analysis.md#stage-5--synthesis-the-optimization-profile)
> rather than fighting it.

A note on **managed vs externally-managed** tables, which recurs below: when a
platform *manages* the Iceberg table (it owns the catalog + writes), it can
maintain it automatically. When it merely *reads* an externally-managed table
(someone else owns the catalog/writes), it will **not** maintain it — maintenance
is the writer's job. Know which mode each table is in.

---

## 5.1 Databricks (Unity Catalog)

Databricks now offers **managed Iceberg tables in Unity Catalog** (GA in early
2026): create/read/write/optimize/govern Iceberg directly, interoperable with
external engines (Trino, Snowflake, EMR) via UC Open APIs.

| Category | Guidance |
|---|---|
| **Table properties** | Prefer **Liquid Clustering** (`CLUSTER BY` keys) over manual partitioning + Z-order — it maintains layout incrementally and is the modern default. Map clustering keys from Stage 1 top filters/join keys. Set spec **v3** for deletion vectors. |
| **Ingestion** | Spark/Structured Streaming or DLT; control commit cadence via **trigger interval**. CDC via `MERGE` / DLT `APPLY CHANGES` (MOR). Same fan-out/distribution rules as bespoke Spark. |
| **Maintenance** | **Predictive Optimization** auto-runs `OPTIMIZE` (compaction, incl. clustering), `VACUUM`, and stats — *for UC-managed tables*. On by default for accounts since Nov 2024; rolling out to all by ~2026. You mostly **stop hand-running maintenance** — but verify it's enabled and watch costs. |

**Watch:** Predictive Optimization + Liquid Clustering only apply to **UC-managed**
tables. Foreign/externally-managed Iceberg tables read via UC are **not**
auto-maintained. Confirm table type before assuming maintenance is handled.

---

## 5.2 Snowflake

Snowflake supports **Snowflake-managed** Iceberg (Snowflake owns the catalog, full
read/write + lifecycle) and **externally-managed/external-catalog** Iceberg
(read-mostly, you maintain it elsewhere).

| Category | Guidance |
|---|---|
| **Table properties** | On managed tables, set a **`CLUSTERING KEY`** (drives Automatic Clustering) from Stage 1 filters; choose `EXTERNAL_VOLUME` and `BASE_LOCATION`. **v3** (preview early 2026) adds row-level deletes, managed clustering, `variant`. |
| **Ingestion** | Snowpipe/`COPY`/Snowpipe Streaming, or `INSERT`/`MERGE`. Mine `COPY_HISTORY` for cadence (Stage 3). Streaming ingestion's small files are absorbed by automatic compaction (below). |
| **Maintenance** | The **Table Optimization Service** bundles **automatic compaction + Automatic Clustering** as a background process for **managed** tables; **manifest compaction** is automatic and can't be disabled. You largely **don't** run manual maintenance on managed tables — but Automatic Clustering bills as **continuous serverless credits**, so apply a `CLUSTERING KEY` only to **frequently-queried** tables (on cold/high-churn tables it can cost more than it saves; see the [cost/scale gate](04-recommendations-maintenance.md)). |

**Watch:** for **externally-managed** Iceberg, **Snowflake performs no
maintenance** — compaction/expiration/cleanup must come from the owning engine
(Spark/Flink/etc.). Don't assume Snowflake is tidying a table it only reads.

---

## 5.3 Bespoke (Spark / Trino / PyIceberg / Dremio)

The full-control stack: you own every property *and* every maintenance chore. This
is where Part II ch. 2–4 apply verbatim.

| Category | Guidance |
|---|---|
| **Table properties** | Set everything explicitly via `ALTER TABLE … SET TBLPROPERTIES` and `WRITE ORDERED BY` (ch. 2). No automation safety net — get partitioning/sort/file-size right and keep them in version control. |
| **Ingestion** | Spark (batch/micro-batch/streaming), Trino (`INSERT`/`MERGE` for interactive/ELT), PyIceberg (lightweight Python appends/maintenance, great for small/medium tables and orchestration glue). Apply commit-cadence, distribution, and operation-matching rules from ch. 3. |
| **Maintenance** | **You run it.** Spark stored procedures (`rewrite_data_files`, `expire_snapshots`, `remove_orphan_files`, `rewrite_manifests`) on a schedule/orchestrator (Airflow). Trino exposes `ALTER TABLE … EXECUTE optimize`; Dremio exposes `OPTIMIZE TABLE` (+ `REWRITE MANIFESTS`) and `VACUUM TABLE` for expiration. Build the **health-driven scheduler** from [§4.7](04-recommendations-maintenance.md#47-the-safe-order-of-operations--scheduling). |

**Engines read large files differently:** Trino/Dremio comfortably scan 1 GB+
files; memory-limited Spark executors may prefer 128–256 MB. Tune
`target-file-size-bytes` to the *reading* engine, validated by query plans.

---

## 5.4 Apache NiFi

NiFi is a **pre-ingestion / delivery** layer, not a table manager.

| Category | Guidance |
|---|---|
| **Table properties** | **N/A — NiFi cannot create or alter tables.** Define the table (partitioning, sort, props) with Spark/Trino first; NiFi writes into the existing schema. |
| **Ingestion** | `PutIceberg` (NiFi 1.19.0–1.23.x) writes to an existing table via a catalog service (e.g. `HiveCatalogService`); Record Reader parses input, Parquet/ORC preferred. **Batch flowfiles** (raise merge/record counts) so each commit isn't tiny — NiFi's per-flowfile cadence is a small-file risk. Use `snapshot-property.*` dynamic props to annotate commits for lineage. Use NiFi's backpressure/retry/provenance for observability. NiFi 2.0 **removed** direct Iceberg support — common pattern there: land files to S3 (`PutS3Object`) and let Spark/Flink ingest. |
| **Maintenance** | **N/A — NiFi does not compact or expire.** A downstream engine (Spark/Trino) must run all of ch. 4. Plan this explicitly; NiFi-fed tables are a classic source of unmanaged small files. |

---

## 5.5 Apache Flink

The streaming writer of choice; naturally suited to MOR/CDC because it knows each
row's position (→ efficient position deletes / deletion vectors).

| Category | Guidance |
|---|---|
| **Table properties** | Set **MOR** modes for CDC/upsert tables; `write.distribution-mode=hash` to cut per-checkpoint fan-out; modest `target-file-size-bytes` (streaming won't fill 512 MB quickly). Define sort order but expect to **restore it via compaction**, not at write time. |
| **Ingestion** | **Checkpoint interval = commit cadence** (`execution.checkpointing.interval`) — the dominant knob; lengthen to the largest the SLA allows to fight small files. Exactly-once via checkpoint↔Iceberg-commit coordination. CDC/upserts via the Flink sink with equality/position deletes. **Pitfall:** Flink upsert pipelines can commit data files and equality deletes at the *same sequence number*, causing deletes not to apply — validate delete semantics and keep the Iceberg version current. |
| **Maintenance** | Flink does **not** self-maintain. **Pair Flink (writes) with periodic Spark compaction + expiration** — the standard streaming-lakehouse architecture. MOR demands frequent compaction (every 1–4 h, tighter for high-change) and frequent/hourly snapshot expiration. |

---

## 5.6 dbt

dbt is a **transformation/modeling** layer that emits warehouse-executed SQL; it
configures table shape but generally **doesn't do maintenance**.

| Category | Guidance |
|---|---|
| **Table properties** | Set in the model `config`: `table_format='iceberg'`, `external_volume`/catalog, `partition_by`, and (on Spark) the full range of Iceberg `tblproperties`, transforms, and write modes. `dbt-spark` is the most mature for full Iceberg control; `dbt-snowflake` (1.9+) supports Iceberg `table`/`incremental`/dynamic materializations and `partition_by` for Iceberg tables. |
| **Ingestion** | Models run as **batch** at warehouse cadence (your scheduler). **Incremental** models use `MERGE` — pick the `incremental_strategy` (`merge` / `append` / `insert_overwrite`) to match the mutation pattern (ch. 3.4). Each run = a snapshot; very frequent dbt runs create snapshot churn. |
| **Maintenance** | **Not dbt's job.** Either the platform automates it (Databricks Predictive Optimization, Snowflake Table Optimization Service) or you run a **separate maintenance job** (Spark procedures / `OPTIMIZE`). Don't assume `dbt run` compacts anything. A common pattern is a dbt post-hook or a sibling Airflow task that calls the maintenance procedures. |

---

## 5.7 Managed-ELT & streaming connectors (Fivetran, Qlik, Airbyte, Confluent Tableflow, Redpanda)

These **bundle ingestion + (often) maintenance**, trading control for low ops:

- **Fivetran / Qlik:** automate **compaction, snapshot/orphan cleanup, stale-metadata
  cleanup, and column stats** on the tables they own. You inherit maintenance —
  but **verify their defaults match your profile** (retention window, file size).
- **Confluent Tableflow:** Kafka→Iceberg with auto compaction and schema-registry
  evolution; **append-only** (no upsert/retract), one catalog per cluster.
- **Redpanda:** topic→Iceberg (spec v2), topic-level partitioning, DLQ on schema
  failure; you still arrange compaction/expiration for v2 delete buildup.
- **Airbyte:** Parquet→Iceberg via REST/Glue/Nessie; MOR equality-delete dedup on
  primary keys; best for periodic/batch syncs. Maintenance generally external.

> Rule: for managed connectors, your job shifts from *doing* maintenance to
> *auditing* that the managed maintenance matches your Stage 4 requirements
> (especially retention and time-travel).

→ Continue to [Decision matrices](06-decision-matrices.md).
