# Part II · Chapter 6 — Decision matrices

> The one-page cheat sheet. Use these *after* you've internalized Part I — they
> compress the workflow into lookups. Each cell still traces back to a profile
> signal; if a recommendation surprises you, go re-read the relevant analysis
> stage rather than applying it blindly.

---

## 6.1 Workload archetype → settings

Four common archetypes and the settings that fall out. Find the nearest match to
your [Stage 0 taxonomy](01-methodology-and-analysis.md#stage-0--frame-the-table-the-workload-taxonomy),
then adjust from your own profile.

| Setting | **A. Append-only event/log** (full-scan analytics, batch/µbatch, immutable, huge) | **B. CDC dimension** (point-lookup, streaming, mutable, small–med) | **C. BI mart / aggregate** (selective scans, batch, low-mutation, med) | **D. Real-time telemetry** (range scans + dashboards, streaming, append, huge) |
|---|---|---|---|---|
| **Partition** | `day(ts)` (`hour` only if huge) | low/none; `bucket(N, key)` | `day`/`month(ts)` + a dim | `hour(ts)` or `day(ts)` |
| **Sort / cluster** | by 2nd filter (e.g. `tenant`) | by primary key | linear by top filter | by dashboard filter cols |
| **Target file size** | 256–512 MB | 128–256 MB | 256–512 MB | 128–256 MB |
| **Distribution mode** | `hash` (`none`+compact if cost-led) | `hash` | `hash`/`range` | `none` + compact |
| **COW / MOR** | COW (rare deletes) | **MOR** (+ deletion vectors v3) | COW | append → COW |
| **Commit cadence** | minutes–hourly | seconds–minutes | per batch | seconds (SLA-bound) |
| **Compaction** | after load / few×day | **1–4 h** (sawtooth) | after load | **1–4 h** |
| **Snapshot expiry** | daily | **hourly** | daily | hourly |

---

## 6.2 Signal → action (the diagnostic index)

What you observe in analysis → what to change, and where.

| Observed signal (stage) | Likely cause | Action | Chapter |
|---|---|---|---|
| `partitions_scanned/total` ≈ 1 (S1) | layout not aligned to predicate | re-partition / add sort key; check pushdown | [2.1](02-recommendations-table-properties.md#21-partitioning)/[2.2](02-recommendations-table-properties.md#22-sort-order--clustering) |
| file p50 `<32 MB` (S2) | small files | compaction + fix write cadence/distribution | [4.2](04-recommendations-maintenance.md#42-compaction-the-highest-impact-operation) + [3.2](03-recommendations-ingestion.md#32-commit-cadence-the-small-file-root-cause) |
| high delete-files/scan (S1/S2) | MOR delete buildup | compact more often; `remove-dangling-deletes`; v3 vectors | [4.2](04-recommendations-maintenance.md#42-compaction-the-highest-impact-operation) |
| thousands of snapshots (S2) | no/loose expiration | expire (time-window for streaming) | [4.3](04-recommendations-maintenance.md#43-snapshot-expiration) |
| storage ≫ live files (S2) | orphans / unexpired history | orphan removal + expiration | [4.4](04-recommendations-maintenance.md#44-orphan-file-removal) |
| high planning time (S1) | manifest fragmentation | `rewrite_manifests` | [4.5](04-recommendations-maintenance.md#45-manifest-rewriting) |
| 13 tiny files/commit @ 30 s (S3) | commit cadence + fan-out | lengthen checkpoint/trigger; `distribution-mode=hash` | [3.2](03-recommendations-ingestion.md#32-commit-cadence-the-small-file-root-cause)/[3.3](03-recommendations-ingestion.md#33-control-write-distribution--fan-out-at-the-source) |
| many over-partitioned dirs (S2) | granularity too fine | partition evolution → coarser | [2.1](02-recommendations-table-properties.md#21-partitioning) |
| writer retries / conflicts (S3) | overlapping concurrent writes | disjoint partitions; raise commit retries | [3.5](03-recommendations-ingestion.md#35-concurrency--commit-conflicts) |
| delete-file count only grows (S2) | compaction not keeping up | raise compaction frequency/scope | [4.2](04-recommendations-maintenance.md#42-compaction-the-highest-impact-operation) |

---

## 6.3 Platform × category: who owns the work

| Platform | Table properties | Ingestion | Maintenance |
|---|---|---|---|
| **Databricks (UC-managed)** | `CLUSTER BY` (Liquid Clustering) | Spark/DLT, trigger cadence | **Auto** (Predictive Optimization) ✅ |
| **Snowflake (managed)** | `CLUSTERING KEY` | Snowpipe/`COPY`/`MERGE` | **Auto** (Table Optimization Service) ✅ |
| **Snowflake (external)** | read-only | n/a (external writer) | **You** (owning engine) ⚠️ |
| **Bespoke (Spark/Trino/PyIceberg/Dremio)** | full manual control | full control | **You** (procedures + scheduler) ⚠️ |
| **NiFi** | ❌ (use Spark first) | `PutIceberg` to existing table | ❌ (downstream engine) ⚠️ |
| **Flink** | MOR + distribution knobs | checkpoint = commit cadence | ❌ (pair with Spark) ⚠️ |
| **dbt** | model `config` (props/partition) | batch runs, incremental `MERGE` | ❌ (platform or separate job) ⚠️ |
| **Managed ELT (Fivetran/Qlik)** | connector-managed | connector-managed | **Auto** (audit defaults) ✅ |

✅ automated · ⚠️ you/another engine must own it · ❌ not supported by this tool

---

## 6.4 Anti-pattern catalog

The recurring mistakes, each a violation of "drive it from evidence":

1. **Partitioning on a high-cardinality column** (`user_id`) → partition
   explosion. Use `bucket[N]` or sort instead.
2. **Over-partitioning** (`hour` on a low-volume table) → *causes* small files.
   Match granularity to partition size, not the calendar.
3. **Choosing COW to "avoid maintenance"** → write amplification on mutable
   tables. Choose on workload; manage MOR with compaction.
4. **Committing every few seconds when the SLA is 5 minutes** → self-inflicted
   small files. Confirm the real freshness need in interviews.
5. **Expiring by snapshot count on a streaming table** → `retain_last=N` is
   minutes of history. Use a time window.
6. **Aggressive orphan removal with a tiny window** → can delete in-flight
   writes. Keep ≥3-day safety window.
7. **Assuming the platform compacts an externally-managed/foreign table** → it
   doesn't. Know managed vs external; assign the owner.
8. **Forgotten branches/tags** → silently pin snapshots and block all cleanup.
   Audit `<table>.refs`; set `max-ref-age-ms`.
9. **Partitioning/sorting on columns nobody filters** → pure overhead. Verify
   against query-log frequencies.
10. **NiFi-fed table with no downstream maintainer** → unmanaged small-file growth.
    Always assign a Spark/Trino maintenance job.

---

## 6.5 The loop, in one line

> **Profile → set properties → shape ingestion → schedule maintenance →
> re-profile.** Keep the profile in version control beside the table definition so
> the *why* travels with the table, and revisit it whenever interviews (Stage 4)
> say the workload is changing.

← Back to [README / table of contents](README.md).
