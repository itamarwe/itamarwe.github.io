---
name: iceberg-optimizer
description: >-
  Diagnoses an Apache Iceberg table and produces a ranked, cost-aware plan
  covering three domains: table layout (compaction, partition evolution, format
  upgrade), ingestion pipeline (write distribution, file sizing, sort order at
  write time), and maintenance (snapshot expiry, orphan cleanup, manifest
  rewrite). Use when asked to optimize, tune, speed up, shrink the cost of,
  clean up, repartition, compact, or design a maintenance schedule for an
  Iceberg table, or to decide whether a table is even worth optimizing.
  Engines: Spark, Trino, AWS Glue/EMR, Snowflake, Flink / Kafka Connect.
  Adapts to Direct mode (live catalog access), Ask-User mode (user runs queries),
  or Exported mode (pre-exported metadata files).
---

# Iceberg Optimizer

A maintenance plan is only as good as the workload it is tuned for. The wrong
move is to reach for the standard "compact + sort + expire snapshots" runbook
before knowing how the table is written, how it is read, and what the owner is
actually paying for. The same table can warrant aggressive daily sort compaction
or *no maintenance at all* depending on query frequency and cost priorities.

**Observe before you ask. Ask before you decide. Simulate before you recommend.**

**CRITICAL — gradual loading:** Do NOT read any file beyond SKILL.md itself
until the engine and access mode are identified in Phase 0. Load reference
files only at the phase boundary where they are first needed, and only the
specific sections that are relevant. Loading everything up front pollutes
context with information that may never apply to this table or engine.

## The flow

```
0. Scope        identify table(s), engine, catalog; stay read-only until Phase 5
1. Profile      derive the table's physical state from metadata
2. Workload     2a derive ingestion signals from metadata & query logs
                2b interview the owner for intent metadata cannot reveal
3. Decide       joint scoring → candidate action groups (incl. "do nothing")
4. Simulate     model perf / query-cost / maintenance-cost / storage scenarios
5. Plan         emit exact engine commands + schedule + monitoring thresholds
```

### Phase 0 — Scope & safety

Establish (ask if not stated):

- **Which table(s)** — fully-qualified: `catalog.schema.table`.
- **Which engine** — Spark, Trino, AWS Glue/EMR, Snowflake, or Flink/Kafka Connect.
  Syntax and capabilities differ significantly across engines.
- **Read-only until Phase 5.** Never run `expire_snapshots`, `remove_orphan_files`,
  `rewrite_data_files`, or any `ALTER TABLE` until the user has approved a specific
  plan. `remove_orphan_files` and `expire_snapshots` *delete files* — treat them
  as destructive.

**Detect access mode** (in this order):

1. Check whether an Iceberg-capable SQL CLI is reachable: `trino`, `spark-sql`,
   `beeline`, or env vars `TRINO_URL`, `SPARK_HOME`, `DATABRICKS_HOST`,
   `SNOWFLAKE_ACCOUNT`. If found → **Direct mode**.
2. Check whether the user already provided exported files (profile.json or metadata
   CSVs) → **Exported mode**.
3. Otherwise, ask: *"Can I run SQL directly against your catalog, or should I give
   you queries to run and paste back?"* → Direct or **Ask-User mode**.

| Mode | Who runs queries | When to use |
|---|---|---|
| Direct | Skill autonomously | Live catalog reachable |
| Ask-User | User pastes output back | No direct access (default) |
| Exported | Skill reads provided files | Files already on disk |

> **Load (Phase 0):** Nothing beyond SKILL.md. Detect mode and engine only.

---

### Phase 1 — Profile (metadata)

> **Load (Phase 1):** `Grep references/metadata-tables.md` for only the signal
> sections you need (e.g. `$files`, `$snapshots`, `$manifests`). Do NOT read the
> full file.

Read the table's physical state. Signal queries live in
`references/metadata-tables.md`.

**Mode branch:**
- **Direct / Ask-User**: Run or request the diagnostic queries; collect output;
  feed to `scripts/profile_table.py`.
- **Exported**: Feed the exported files directly to `scripts/profile_table.py`.

```
scripts/profile_table.py --snapshots S --files F [--partitions P] [--manifests M] --out profile.json
```

Emits: file-size health, small-file pressure, delete-file pressure,
snapshot/manifest bloat, mixed partition specs, total size and file count.
This phase alone answers "is this table healthy?" and is safe on any table.

---

### Phase 2 — Reconstruct the workload

> **Load (Phase 2a):** Grep `references/metadata-tables.md` for workload-signal
> sections. Grep `references/workload-interview.md` for the derive-then-ask bank.

#### 2a — Derive what metadata already knows

Most ingestion and access questions are *answerable from metadata* — never ask
the user something `$snapshots` and `$files` already answered.

**Ingestion signals to derive:**

| Signal | Source | Derived value |
|---|---|---|
| `write_cadence` | median inter-commit gap | `streaming` / `micro_batch` / `batch` |
| `avg_added_file_mb` | `added-files-size` / `added-data-files` | number |
| `thin_spread` | files/partition/commit ratio | bool |
| `late_data` | event-time bounds vs `committed_at` | bool |
| `eq_delete_pressure` | equality-delete records / data records | ratio |
| `pos_delete_pressure` | position-delete files / data files | ratio |
| `operation_mix` | `snapshots.operation` distribution | append / overwrite / merge counts |

**Ingestion pipeline identification** — derive from the signal combination above,
then confirm with the user (see `references/workload-interview.md` Part 1a):

| Signal pattern | Likely writer |
|---|---|
| `streaming`, `avg_added_file_mb < 5`, `thin_spread = true` | Flink (default config) or Spark Structured Streaming, short trigger |
| `streaming`, `avg_added_file_mb ≥ 50` | Flink with large checkpoint interval |
| `micro_batch` (5s–5min commits) | Spark Structured Streaming |
| `batch`, large commits, `late_data = false` | Spark batch ETL or dbt |
| `batch`, small-to-medium commits, irregular intervals | Apache NiFi (`PutIcebergRecord`) or Beam batch |
| `streaming`, small files, `thin_spread = false`, low parallelism | Apache Beam / Dataflow streaming with low `numShards` |
| `operation_mix` dominated by full partition `overwrite`, regular cadence | Airbyte full-refresh or Fivetran managed sync |
| high `overwrite` + `append` in `operation_mix` | CDC connector (Debezium, DeltaStreamer, Airbyte merge) |
| `eq_delete_pressure > 0.05`, `merge` in `operation_mix` | MOR CDC — equality deletes accumulating |
| `pos_delete_pressure > 0.2`, no equality deletes | COW CDC or MOR with position deletes |
| `batch`, very large one-off commits then silence | AWS DMS migration or historical backfill |

Always show the derived writer type and ask the user to confirm:
*"Based on commit patterns (~Xs gaps, ~Y MB files, spread across N partitions),
this looks like [writer type]. Is that right? What connector/framework writes to this table?"*

**Determine ingestion fix eligibility** — add these to the signal set:
- `distribution_mode`: if the user knows whether `write.distribution-mode` is set
  (`none` / `hash` / `range`). Derive from thin_spread; ask to confirm.
- `ingestion_write_mode`: `mor` / `cow` / `append_only`. Derive from delete file
  presence; ask to confirm.
- `checkpoint_interval_secs`: relevant for Flink/Spark SS. Derive from inter-commit
  gap; ask to confirm.

**Access pattern signals:**

```
scripts/parse_query_log.py --spark-eventlog LOG   # or: --trino-queries QUERIES
                           --table catalog.schema.table --out workload.json
                           [--explain-analyze explain.txt]
```

Extracts per-table: ranked WHERE-clause columns, range vs equality predicate type,
partition-pruning effectiveness, query selectivity (rows scanned ÷ rows returned),
query frequency.

| Source | Flag | What the script reads |
|---|---|---|
| Trino `system.runtime.queries` export (JSON/CSV) | `--trino-queries` | `physical_input_bytes` |
| Trino JSON event-listener log (NDJSON) | `--trino-queries` | `physicalInputDataSize` |
| Spark event log | `--spark-eventlog` | "size of files read" metric |
| Trino `EXPLAIN ANALYZE` output | `--explain-analyze` | `Physical Input Data Size:` lines |

If none available, ask the user to run `EXPLAIN ANALYZE` on 3–5 representative
queries and paste the output.

#### 2b — Interview for intent

> **Load (Phase 2b):** Read `references/workload-interview.md` Part 2 only if 2a
> didn't already load it.

Walk `references/workload-interview.md` Part 2. For each item, present what you
derived in 2a; ask the user to confirm or correct; ask only the genuinely
unknowable parts. Use `AskUserQuestion` — these are real decisions only the
owner can make:

- Query **latency** requirement (interactive vs batch-tolerant)
- Query **frequency** and number of consumers
- **Freshness** SLA
- **Cost priority** (the `--priority` flag for `simulate.py`)
- **Mutability outlook** (append-only vs updates/deletes/GDPR)
- **Time-travel / replay / audit** need
- **Lifecycle / worth** (hot / warm / cold / not worth optimizing)
- **Retention / compliance** (only if deletes were observed in 2a)

---

### Phase 3 — Decide

> **Load (Phase 3):** Read `references/decision-framework.md` in full.

Apply `references/decision-framework.md`: it combines profile + workload signals
into a ranked set of actions across **three groups**. A complete plan typically
draws from more than one group.

**Group 1 — Table Layout:** partition spec, write-time sort order (table property),
bloom filters, format version. Metadata changes — run before compaction, since there
is no point compacting into a layout you are about to change.

**Group 2 — Ingestion:** write-time distribution mode, file-size buffering,
CDC write-mode (MOR→COW). Run these *first* — fixing the writer before compacting
its output prevents the problem from recurring.

**Group 3 — Maintenance:** all compaction (bin-pack, sort, z-order, delete-file),
snapshot expiry, manifest rewrite, orphan file removal. These are ongoing operations
on data already on disk; run *after* Groups 1 and 2.

Key gates that prevent over-engineering:
- **Low query frequency + cold table → do little or nothing.** Maintenance compute
  can cost more than it ever saves; pay at query time instead.
- **Sort / z-order only when** queries are selective *and* read often enough to
  amortize the rewrite.
- **Aggressive snapshot expiry only when** replay/time-travel is not needed.
- **Bloom filters only for** high-cardinality equality lookups.

> **Load (Group 2 only):** If any Group 2 actions are recommended, load
> `engines/ingestion.md` now — it has the writer-specific configuration blocks.

---

### Phase 4 — Simulate

> **Load (Phase 4):** No reference files — run `scripts/simulate.py` directly.

Build candidate scenarios and run:

```
scripts/simulate.py --profile profile.json --workload workload.json
                    [--assumptions a.json] --priority <storage|query_cost|latency|maintenance_cost>
```

Produces comparison across **Do-nothing**, **Light**, **Targeted-sort**,
**Aggressive**, and **Storage-min** scenarios. Present results as directional
estimates with ranges, never as precise figures. Highlight the scenario that wins
on the user's chosen priority.

**Baseline bytes**: If `workload.json` has `selectivity.median_bytes_scanned`
(from logs or EXPLAIN ANALYZE), that measured number is used directly. Otherwise
falls back to `total_gb × (1 − prune_rate)`.

Override `scan_fraction` when you have a post-compaction measurement:

```bash
--assumptions '{"scan_fraction": {"targeted_sort": 0.18}}'
```

---

### Phase 5 — Plan

> **Load (Phase 5):** Read ONLY the engine file matching the detected engine:
> - Spark or AWS Glue/EMR → `engines/spark.md` (for Glue also read `engines/glue.md`)
> - Trino → `engines/trino.md`
> - Snowflake → `engines/snowflake.md`
> - Ingestion Group 2 actions → `engines/ingestion.md` (may already be loaded)
>
> Do NOT load engine files for engines not in scope. Grep
> `references/scheduling.md` only if the user requests a schedule.

Emit the concrete plan for the chosen scenario:

**Operation order — always:**
1. Group 2 (Ingestion fixes) — change writer config; takes effect on next run
2. Group 1 (Table Layout) — compact → expire snapshots → remove orphans → rewrite manifests
3. Group 3 (Maintenance) — schedule ongoing tasks

Never remove orphans before expiring snapshots.

**Commands** — exact, engine-specific, with parameters filled from the profile.
Double-check engine capabilities in the loaded engine file (e.g. Trino does NOT
support sort/z-order compaction or manifest clustering — use Spark for those).

**Schedule** — from `references/scheduling.md`, matched to the write cadence
and the chosen scenario.

**Monitoring** — metadata-table threshold queries that should trigger the next run.

Restate the safety note before any destructive command, and get explicit approval
before running anything that deletes files or rewrites data.

---

## Files in this skill

**Base (always loaded):** `SKILL.md` only.

**Loaded on demand during phases:**

| File | Loaded when |
|---|---|
| `references/metadata-tables.md` | Phase 1 (grep specific sections) |
| `references/workload-interview.md` | Phase 2a/2b (grep or read Part 2) |
| `references/decision-framework.md` | Phase 3 (read in full) |
| `references/scheduling.md` | Phase 5, only if schedule requested |
| `engines/spark.md` | Phase 5, Spark or Glue/EMR engine |
| `engines/glue.md` | Phase 5, Glue/EMR (supplement to spark.md) |
| `engines/trino.md` | Phase 5, Trino engine |
| `engines/snowflake.md` | Phase 5, Snowflake engine |
| `engines/ingestion.md` | Phase 3/5, when Group 2 actions recommended |

**Scripts (invoked directly, not loaded as context):**

| Script | Purpose |
|---|---|
| `scripts/profile_table.py` | metadata → structured profile JSON |
| `scripts/parse_query_log.py` | Spark event log / Trino queries → access profile |
| `scripts/simulate.py` | scenario cost / performance model |
