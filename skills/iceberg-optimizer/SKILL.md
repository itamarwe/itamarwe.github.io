---
name: iceberg-optimizer
description: >-
  Diagnoses an Apache Iceberg table and produces a ranked, cost-aware maintenance
  and layout plan — compaction (bin-pack / sort / z-order), partition evolution,
  snapshot expiry, orphan-file and manifest cleanup, sort orders and bloom filters,
  plus a run schedule. Use when asked to optimize, tune, speed up, shrink the cost
  of, clean up, repartition, compact, or design a maintenance schedule for an
  Iceberg table, or to decide whether a table is even worth optimizing. It reads
  everything it can from table metadata and query logs first, then asks only what
  metadata cannot reveal (latency/freshness SLAs, query frequency, cost priority,
  mutability and time-travel needs), and simulates query-performance / query-cost /
  maintenance-cost / storage trade-offs so the user can optimize for the axis they
  care about. Engines: Spark, Trino, AWS Glue, Flink.
---

# Iceberg Optimizer

A maintenance plan is only as good as the workload it is tuned for. The wrong
move is to reach for the standard "compact + sort + expire snapshots" runbook
before knowing how the table is written, how it is read, and what the owner is
actually paying for. The same table can warrant aggressive daily sort compaction
or *no maintenance at all* depending on query frequency and cost priorities.

This skill follows one rule: **observe before you ask, ask before you decide,
simulate before you recommend.**

## The flow

Work through these phases in order. Do not skip Phase 4 (simulation) — a
recommendation without a trade-off is a guess.

```
0. Scope        identify table(s), engine, catalog; stay read-only until Phase 5
1. Profile      derive the table's physical state from metadata
2. Workload     2a derive ingestion + access patterns from metadata & query logs
                2b interview the owner for intent metadata cannot reveal
3. Decide       joint scoring → candidate strategies (incl. "do nothing")
4. Simulate     model perf / query-cost / maintenance-cost / storage scenarios
5. Plan         emit exact engine commands + schedule + monitoring thresholds
```

### Phase 0 — Scope & safety

Establish, by asking if not stated:

- **Which table(s)** (fully-qualified: `catalog.schema.table`).
- **Which engine** runs maintenance: Spark, Trino, AWS Glue, or Flink. Syntax
  and capabilities differ — see `references/procedures.md`.
- **Read-only until Phase 5.** Profiling only reads metadata tables. Never run
  `expire_snapshots`, `remove_orphan_files`, `rewrite_data_files`, or any
  `ALTER TABLE` until the user has approved a specific plan. `remove_orphan_files`
  and `expire_snapshots` *delete files* — treat them as destructive.

This skill does not have a connection to the user's warehouse. Operate in one of
two modes:

- **Guided** (default): hand the user the exact diagnostic SQL from
  `references/metadata-tables.md`, have them run it and paste back the output,
  then feed it to the scripts.
- **Exported**: the user exports the metadata tables and query log to files;
  the scripts process them offline.

### Phase 1 — Profile (metadata)

Read the current physical state. The signals and the exact SQL live in
`references/metadata-tables.md`. Then run:

```
scripts/profile_table.py --snapshots S --files F [--partitions P] [--manifests M] --out profile.json
```

It emits a structured profile: file-size health, small-file pressure, delete-file
pressure, snapshot/manifest bloat, mixed partition specs, total size and file
count. This phase alone answers "is this table healthy?" and is safe to run on
any table — it is the part that could later become a standalone profiler skill.

### Phase 2 — Reconstruct the workload

**2a — Derive what metadata already knows.** Most "interview" questions about
ingestion are answerable from `$snapshots` and `$files` without asking the user.
`references/metadata-tables.md` gives the queries; the profiler reports:

- **Write cadence** — median inter-commit gap → streaming / micro-batch / batch.
- **File size at write** — are writers buffering to target size, or flushing
  tiny files every commit?
- **Partition fan-out** — does each commit land in ~1 partition, or spray thin
  files across many? (the classic small-file amplifier)
- **Late / out-of-order arrival** — do freshly-committed files contain old
  event-times? (breaks "compact only cold partitions" and time-clustering
  assumptions)
- **Mutability seen so far** — append / overwrite / delete mix and delete-file
  presence.

For access patterns, run:

```
scripts/parse_query_log.py --spark-eventlog LOG   # or: --trino-queries QUERIES
                           --table catalog.schema.table --out workload.json
```

It extracts, per table: the ranked columns that appear in `WHERE` clauses,
whether each is used in range vs equality predicates, partition-pruning
effectiveness, query selectivity (rows scanned ÷ rows returned), and query
frequency. SQL-text parsing is approximate — say so to the user.

**2b — Interview for intent.** Metadata cannot tell you what the table is *for*.
Walk `references/workload-interview.md`. For each item, present what you already
derived in 2a, ask the user to confirm or correct it, and ask only the genuinely
unknowable parts:

- Query **latency** requirement (interactive vs batch-tolerant).
- Query **frequency** and number of consumers.
- **Freshness** SLA — must rows be queryable the instant they land, or is
  once-a-day optimization fine?
- **Cost priority** — what are they optimizing: storage \$, query \$, query
  latency, or maintenance \$? (this picks the simulation's objective)
- **Mutability outlook** — append-only forever, or expect updates / GDPR deletes?
- **Time-travel / replay** — is snapshot history a feature (replay, audit) or
  just exhaust (only the latest state matters)?
- **Lifecycle / worth** — hot, warm, or cold archive? Possibly not worth
  optimizing at all.

Use `AskUserQuestion` for these — they are real decisions only the owner can make.

### Phase 3 — Decide

Apply `references/decision-framework.md`: it combines the Phase 1 profile with
the Phase 2 workload into a ranked set of candidate actions, each gated by intent.
Key gates that prevent over-engineering:

- **Low query frequency + cold table → recommend doing little or nothing.** If
  the table is read rarely, maintenance compute can cost more than it ever saves;
  pay at query time instead. Surface this explicitly rather than defaulting to a
  full runbook.
- **Sort / z-order only when** queries are selective *and* read often enough to
  amortize the rewrite.
- **Aggressive snapshot expiry only when** replay/time-travel is not needed.
- **Bloom filters only for** high-cardinality equality lookups.

### Phase 4 — Simulate

Never present a single plan as obviously correct. Build the candidate scenarios
and run:

```
scripts/simulate.py --profile profile.json --workload workload.json
                    [--assumptions a.json] --priority <storage|query_cost|latency|maintenance_cost>
```

It produces a comparison across **Do-nothing**, **Light**, **Targeted-sort**,
**Aggressive**, and **Storage-min** scenarios, scoring each on query latency,
query cost, maintenance cost, and storage cost. The model is transparent and
driven by the table's *real* numbers; every constant (scan price, compaction
cost per TB, file-skip factors) is printed and overridable via `--assumptions`.
Present results as directional estimates with ranges, never as precise figures.
Then highlight the scenario that wins on the user's chosen priority.

### Phase 5 — Plan

Emit the concrete plan for the chosen scenario:

- **Commands** — exact, engine-specific, with parameters filled from the profile.
  See `references/procedures.md` (Spark `CALL`, Trino `ALTER TABLE EXECUTE`,
  Glue, Flink) and double-check engine capabilities there (e.g. Trino *does*
  support `expire_snapshots`, `remove_orphan_files`, and `optimize_manifests`).
- **Order** — always compact → expire snapshots → remove orphans → rewrite
  manifests. Never remove orphans before expiring snapshots.
- **Schedule** — from `references/scheduling.md`, matched to the derived write
  cadence and the chosen scenario (fixed cron vs metadata-threshold triggers;
  "cold-partition-only" compaction for live streaming tables).
- **Monitoring** — the metadata-table threshold queries that should trigger the
  next maintenance run.

Restate the safety note before any destructive command, and get explicit
approval to run anything that deletes files or rewrites data.

## Files in this skill

- `references/metadata-tables.md` — every Iceberg metadata table, its schema, and
  the diagnostic queries that derive the profile and the ingestion signals.
- `references/workload-interview.md` — the derive-then-ask question bank for
  Phase 2b, with what metadata can vs cannot answer.
- `references/decision-framework.md` — the joint scoring rules and intent gates.
- `references/procedures.md` — verified Spark / Trino / Glue / Flink maintenance
  syntax, parameters, and table properties.
- `references/scheduling.md` — archetype→schedule matrix and threshold triggers.
- `scripts/profile_table.py` — metadata → structured profile (stdlib only).
- `scripts/parse_query_log.py` — Spark event log / Trino queries → access profile.
- `scripts/simulate.py` — transparent scenario cost/performance model.
