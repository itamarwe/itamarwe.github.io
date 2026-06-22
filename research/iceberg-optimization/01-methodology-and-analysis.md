# Part I — Methodology & Analysis

> Optimize from evidence, not vibes. Every knob in Part II is downstream of a
> fact you can measure. This chapter is how you gather those facts.

The mistake most teams make is starting from the answer ("we should compact" /
"we should partition by day") instead of the workload. Iceberg gives you an
unusually rich, queryable record of how a table behaves — its metadata tables
expose every file, partition, snapshot, and delete — and the engines that read
and write it keep logs. Combine those with what users actually need, and the
right settings mostly fall out.

The workflow has five stages:

```
                          ┌─────────────────────────────────────────┐
                          │  0. Frame: what is this table FOR?        │
                          │     (workload taxonomy)                   │
                          └───────────────────┬───────────────────────┘
                                              │
        ┌──────────────┬─────────────────────┼────────────────────┬──────────────┐
        ▼              ▼                     ▼                    ▼              ▼
  1. Query logs   2. Table metadata   3. Ingestion logs   4. User interviews
  (how it's read) (current physical   (how it's written)  (requirements &
                   layout & health)                        future read paths)
        └──────────────┴─────────────────────┬────────────────────┴──────────────┘
                                              ▼
                          ┌─────────────────────────────────────────┐
                          │  5. Synthesize → Optimization Profile     │
                          │     → feeds Part II recommendations       │
                          └─────────────────────────────────────────┘
```

Stages 1–4 are independent — run them in parallel — but they cross-check each
other. Query logs tell you what *should* be cheap; metadata tells you why it
*isn't*; ingestion logs tell you what *created* the problem; interviews tell you
what's about to change. A recommendation supported by only one stream is a guess;
one supported by three is a decision.

---

## Stage 0 — Frame the table: the workload taxonomy

Before measuring anything, classify the table. The classification narrows the
search space for every later decision. Five axes matter:

| Axis | Buckets | Why it drives optimization |
|---|---|---|
| **Read pattern** | Point lookups · selective range scans · full scans/aggregations · ML feature reads | Decides partitioning + sort/cluster keys and COW-vs-MOR. |
| **Write pattern** | Append-only · upsert/CDC · overwrite/backfill · slowly-changing | Decides write distribution, MOR vs COW, commit cadence. |
| **Latency SLA** | Real-time (sec) · near-real-time (min) · batch (hourly/daily) | Trades small files & MOR (low latency) against read cost. |
| **Mutability** | Immutable facts · mutable dimensions · GDPR/delete-heavy | Decides delete strategy and compaction frequency. |
| **Scale & growth** | Rows/day, total size, partition cardinality, retention | Decides partition granularity and maintenance budget. |

A *clickstream events* table (append-only, full-scan analytics, batch, immutable,
huge) lands in a completely different corner of Part II than a *customer
dimension* (upsert, point-lookup, near-real-time, mutable, small). Write the
bucket down for each axis — it's the first line of the profile.

---

## Stage 1 — Query log analysis (how the table is read)

**Goal:** learn the real predicates, the columns that filter, the join keys, the
selectivity, and which queries are slow and why. This is the single most
important input to *layout* decisions (partitioning, sort order, clustering).

### Where the logs live

| Platform | Source of truth |
|---|---|
| Snowflake | `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` + `ACCESS_HISTORY` (column-level) |
| Databricks | `system.query.history`, `system.access.column_lineage`, query profiles |
| Trino/Starburst | event listener → query-events table; `EXPLAIN ANALYZE` |
| Spark | Spark SQL UI / event logs (`spark.eventLog`), `EXPLAIN FORMATTED` |
| Flink | Flink SQL plans (less relevant — Flink is usually the writer) |
| dbt | `manifest.json` + `run_results.json`; warehouse query history for the compiled SQL |

### What to extract

For every recurring query against the table, capture:

1. **Filter columns and operators** — `WHERE event_date >= … AND country = …`.
   Tally frequency per column. *The most-filtered columns are your partition and
   sort candidates.*
2. **Filter selectivity** — what fraction of rows/partitions survive each
   predicate. High-selectivity equality filters (e.g. `user_id = …`) want
   sort/cluster locality, not partitioning (too high cardinality to partition on).
3. **Join keys** — columns repeatedly joined want clustering so the engine reads
   contiguous files.
4. **Projected columns** — which columns are actually `SELECT`ed. Wide tables
   read narrowly benefit from column-level layout and from *not* over-indexing on
   unread columns.
5. **Scan volume vs returned volume** — the ratio (bytes scanned / bytes
   returned) is the headline inefficiency metric. A query that scans 2 TB to
   return 10 MB is a pruning failure.
6. **Time-of-day / concurrency** — when reads spike, so you can schedule
   maintenance in the troughs.

### The pruning diagnosis

The core question for read optimization is **"is the engine pruning?"** Pull the
query profile / `EXPLAIN ANALYZE` and read three numbers:

- **files scanned vs files matched** — if a query that filters one day reads the
  whole table, partitioning/clustering isn't aligned to the predicate, or the
  predicate can't be pushed down (e.g. a function wrapping the column, or a type
  mismatch defeating partition transforms).
- **delete files applied per scan** — high counts on a MOR table mean read
  amplification from accumulated deletes → a compaction signal, not a layout one.
- **manifest scan time** — large planning time before any data is read points at
  *metadata* bloat (too many manifests/snapshots), addressed in maintenance.

> Example signal → implication: 80% of queries filter `event_date` and 30% also
> filter `tenant_id`; lookups by `user_id` are frequent but `user_id` has
> millions of distinct values. → **Partition by `day(event_date)`** (low
> cardinality, near-universal filter), **sort/cluster by `tenant_id, user_id`**
> (locality without partition explosion). Do *not* partition by `user_id`.

A reusable Snowflake query-history starting point (real, runnable):

```sql
-- Most-filtered tables and the columns queried against an Iceberg table,
-- last 30 days. Pair with ACCESS_HISTORY for column-level filter attribution.
select  query_type,
        count(*)                                   as execs,
        avg(bytes_scanned)/1e9                      as avg_gb_scanned,
        avg(rows_produced)                          as avg_rows_out,
        avg(bytes_scanned) / nullif(avg(rows_produced),0) as scan_per_row,
        avg(partitions_scanned)                     as avg_parts_scanned,
        avg(partitions_total)                       as avg_parts_total
from    snowflake.account_usage.query_history
where   start_time > dateadd('day', -30, current_timestamp())
  and   query_text ilike '%<schema>.<table>%'
group by 1
order by avg_gb_scanned desc;
```

The `partitions_scanned / partitions_total` ratio is the pruning score: close to
1.0 means no pruning is happening.

---

## Stage 2 — Table metadata analysis (the current physical layout)

**Goal:** measure the table's *current* health and layout directly from Iceberg's
own metadata. This is unique to Iceberg — you don't have to guess, you can
`SELECT`. Everything here is engine-agnostic; the metadata tables are part of the
spec and exposed by Spark, Trino, Dremio, Snowflake, Athena, PyIceberg, etc.

### The metadata tables you'll use

| Metadata table | Tells you |
|---|---|
| `<table>.files` (`data_files` / `delete_files`) | Every file: size, record count, partition, column-level value bounds, null counts. |
| `<table>.partitions` | Per-partition file count, record count, total size, delete-file count. |
| `<table>.snapshots` | Commit history: timestamp, operation, added/deleted files & records, summary. |
| `<table>.history` | Lineage of snapshots and which are current/ancestors. |
| `<table>.manifests` | Manifest files and how many data files each tracks. |
| `<table>.metadata_log_entries` | Successive `metadata.json` versions (metadata growth). |
| `<table>.refs` | Branches and tags (WAP, time-travel anchors). |
| `<table>.all_entries` | Low-level manifest entries (advanced debugging). |

### The five health checks

**1. File-size distribution (the small-file problem).** The most common pathology.

```sql
-- Spark/Trino. Buckets the data files of a table by size.
select case
         when file_size_in_bytes <  8*1024*1024  then '  <8MB (tiny)'
         when file_size_in_bytes < 32*1024*1024  then ' 8-32MB (small)'
         when file_size_in_bytes <128*1024*1024  then '32-128MB (ok)'
         when file_size_in_bytes <512*1024*1024  then '128-512MB (good)'
         else '>512MB (large)'
       end                                   as bucket,
       count(*)                              as files,
       round(sum(file_size_in_bytes)/1e9, 2) as gb,
       round(avg(record_count))              as avg_rows
from   db.schema.table.files
where  content = 0            -- data files only
group by 1 order by 1;
```

If most files are `<32 MB`, query planning and open cost dominate → compaction +
a write-side fix. The target band is **128–512 MB** (see Part II for the exact
property).

**2. Partition skew & cardinality.**

```sql
select  partition,
        count(*)                              as files,
        sum(record_count)                     as rows,
        round(sum(file_size_in_bytes)/1e9, 2) as gb
from    db.schema.table.partitions
order by gb desc;
```

Look for: (a) thousands of partitions with a handful of tiny files each
(over-partitioning); (b) a few partitions holding most of the data (skew — the
partition key doesn't spread writes); (c) huge partition *count* relative to the
predicates in Stage 1 (partitioned on a column nobody filters).

**3. Delete-file accumulation (MOR read amplification).**

```sql
select  count(*)                              as delete_files,
        round(sum(file_size_in_bytes)/1e6, 1) as mb,
        sum(record_count)                     as deleted_rows
from    db.schema.table.files
where   content in (1,2);     -- 1=position deletes, 2=equality deletes
```

Compare delete-file count and rows to live data files. A high ratio means every
read pays a merge tax → compaction (which re-applies and drops deletes) is
overdue, and you may need to switch delete strategy or COW/MOR.

**4. Snapshot & metadata growth.**

```sql
select  count(*)                                   as snapshots,
        min(committed_at)                          as oldest,
        max(committed_at)                          as newest,
        datediff('day', min(committed_at), max(committed_at)) as span_days
from    db.schema.table.snapshots;
```

Thousands of retained snapshots (especially from a high-frequency streaming
writer) bloat `metadata.json` and slow planning → snapshot expiration. Also check
`metadata_log_entries` row count and `manifests` count.

**5. Manifest fragmentation.**

```sql
select  count(*)                                 as manifests,
        round(avg(added_data_files_count +
                  existing_data_files_count))    as avg_files_per_manifest,
        sum(added_data_files_count +
            existing_data_files_count)           as total_tracked_files
from    db.schema.table.manifests;
```

Many manifests each tracking few files (the signature of frequent small commits)
→ `rewrite_manifests`.

> Metadata analysis tells you **what is wrong now**; query logs tell you **whether
> it matters** for how the table is read. A table with 50k tiny files that is only
> ever read by a nightly full scan is less urgent than one with 5k tiny files hit
> by thousands of selective lookups.

---

## Stage 3 — Ingestion log analysis (how the table is written)

**Goal:** understand the write side, because *most physical problems are created
at write time* and the cheapest fix is usually to stop creating them rather than
to clean up after.

### Where the logs live

| Writer | Source of truth |
|---|---|
| Spark batch | Spark event logs, job run history, number of write tasks/partitions. |
| Flink | Checkpoint interval & history, committer logs, files-per-commit. |
| NiFi | `PutIceberg` provenance events, batch sizes, flowfile cadence. |
| Kafka Connect (Iceberg sink) | Connector commit interval, tasks, records/commit. |
| dbt | `run_results.json` timings; whether models full-refresh or merge. |
| Snowpipe / Snowflake | `COPY_HISTORY`, pipe usage, `INSERT`/`MERGE` history. |

### What to extract

The `<table>.snapshots` metadata table *is* an ingestion log — every commit is a
row, and `summary` carries `added-data-files`, `added-records`,
`added-files-size`, and the engine. Mine it:

```sql
-- Commit cadence and per-commit file production over the last 7 days.
select  date_trunc('hour', committed_at)            as hr,
        count(*)                                    as commits,
        sum(cast(summary['added-data-files'] as int))   as files_added,
        sum(cast(summary['added-records']    as bigint))as rows_added,
        round(sum(cast(summary['added-files-size'] as bigint))
              / nullif(sum(cast(summary['added-data-files'] as int)),0)
              / 1e6, 1)                              as avg_added_file_mb
from    db.schema.table.snapshots
where   committed_at > current_timestamp - interval '7' day
group by 1 order by 1;
```

Read it for:

1. **Commit frequency** — a Flink job checkpointing every 30 s makes 2,880
   commits/day, each producing ≥1 file *per partition written*. This is the #1
   small-file generator. → tune checkpoint/commit interval, or accept it and lean
   on compaction.
2. **Files per commit vs partitions touched** — if each commit writes a file to
   many partitions (fanout), the small-file problem multiplies by partition
   count. → write distribution mode (`hash`/`range`) or pre-shuffle.
3. **Average added-file size** — directly comparable to the 128–512 MB target.
   Tiny added files = the write is the problem, not just history.
4. **Operation mix** — ratio of `append` vs `overwrite` vs `delete`. Lots of
   `delete`/`overwrite` (CDC) flags the COW/MOR decision and delete-file growth.
5. **Backfills/full-refresh** — large `overwrite` snapshots that rewrite whole
   partitions; coordinate these with maintenance windows.
6. **Failed/retried commits** — commit conflicts (multiple writers) show as
   retries; orphan files are their residue. → concurrency settings + orphan
   cleanup.

> Cross-check with Stage 2: if `files` shows 40k tiny files and `snapshots` shows
> a 30 s commit cadence with ~13 files/commit, you've found the cause. The fix is
> ingestion-side (Part II ch. 3) first, maintenance (ch. 4) second.

---

## Stage 4 — User interviews (data-access requirements)

**Goal:** capture what logs can't — intent, future workloads, and the
cost/latency/freshness tradeoffs only humans can rank. Logs are a rear-view
mirror; interviews are the windshield. A layout optimized purely on history will
be wrong the moment a new dashboard ships.

Interview the **consumers** (analysts, BI owners, ML/data-science, downstream
pipeline owners) and the **producers** (the team running ingestion). A compact
question set, grouped by what it unlocks:

**Access patterns & filters**
- "When you query this, what do you almost always filter by?" (confirms/long-tails
  the Stage 1 partition/sort candidates — and surfaces *planned* filters not yet
  in the logs).
- "Point lookups, dashboards, or big scans? Roughly what split?"
- "Which columns do you actually need? Any you never use?"

**Freshness & latency**
- "How fresh does this need to be — seconds, minutes, hours?" (sets the ingestion
  latency SLA and therefore the small-file/MOR tolerance).
- "What's an acceptable query latency at p95?"

**Mutability & correctness**
- "Do records get updated or deleted after they land? How often, by what key?"
  (drives COW vs MOR and delete strategy).
- "Do you need time travel / as-of queries? How far back?" (sets snapshot
  retention — overrides aggressive expiration).
- "Any GDPR/right-to-erasure obligations?" (forces delete capability + retention
  limits).

**Cost & ownership**
- "Who pays for compute, and is this cost- or latency-sensitive?" (ranks the
  speed-vs-cost knobs, e.g. `write.distribution-mode=none` for cheap fast writes
  vs `hash` for read-optimized layout).
- "What's changing in the next two quarters?" (new consumers, schema evolution,
  volume growth — pre-empts re-partitioning churn).

The deliverable of this stage is a short **requirements memo** per table:
SLA (freshness, p95 latency), retention/time-travel window, mutability profile,
top filter columns (confirmed by a human), and cost posture. These become hard
constraints that can *override* a log-derived recommendation — e.g. logs say
"expire snapshots after 1 day" but compliance needs 90-day time travel.

---

## Stage 5 — Synthesis: the Optimization Profile

Collapse the four streams into one structured profile per table. This is the
single artifact that Part II consumes. Resolve conflicts with this precedence:

1. **Hard requirements** (compliance, SLA, time-travel) from interviews — never
   violated.
2. **Read evidence** (query logs) — primary driver of *layout* (partition, sort,
   COW/MOR).
3. **Write evidence** (ingestion logs) — primary driver of *ingestion* settings
   and the *root cause* of file/metadata problems.
4. **Current state** (metadata) — primary driver of *maintenance* (what to clean
   up now) and the baseline you'll measure improvement against.

### Profile template

```yaml
table: db.schema.events
owner: growth-data
# --- Stage 0: workload taxonomy ---
read_pattern:   selective-range-scan        # + occasional full scan
write_pattern:  append-only                  # CDC? no
latency_sla:    near-real-time (~5 min)
mutability:     immutable (GDPR delete only, by user_id)
scale:          ~1.2B rows/day, 40 TB, retention 18 mo

# --- Stage 1: read evidence ---
top_filters:        [event_date (92%), tenant_id (34%), user_id (point lookups)]
typical_selectivity: 1 day of N days; tenant high-selectivity
join_keys:          [user_id]
pruning_score:      poor (partitions_scanned/total ~0.8)   # not pruning

# --- Stage 2: current state ---
file_size_p50:      11 MB         # tiny → small-file problem
partition_scheme:   day(event_date)/hour(event_date)   # over-partitioned (hour)
delete_files:       low
snapshots_retained: 9,400         # bloated
manifests:          3,100 (avg 9 files each)   # fragmented

# --- Stage 3: write evidence ---
writer:             Flink
commit_cadence:     ~30s checkpoints (2,880/day)
files_per_commit:   ~13, avg 11 MB           # root cause of tiny files
operation_mix:      99% append

# --- Stage 4: requirements ---
freshness:          5 min ok (NOT seconds)   # room to slow commits
time_travel:        7 days
cost_posture:       cost-sensitive

# --- Stage 5: decisions (→ Part II) ---
decisions:
  table_properties: [ "partition: drop hour, keep day(event_date)",
                      "sort/cluster by tenant_id,user_id",
                      "target-file-size 256MB" ]
  ingestion:        [ "raise Flink checkpoint to 2-5 min",
                      "write.distribution-mode=hash on event_date" ]
  maintenance:      [ "compact every 1-4h (bin-pack + sort)",
                      "expire snapshots >7d",
                      "rewrite_manifests weekly",
                      "remove_orphan_files >3d" ]
```

With a filled profile, Part II is mostly lookup: each `decisions` line maps to a
specific property, command, or platform feature in the next chapters.

> **Iterate.** Optimization is a loop, not a one-shot. After applying Part II,
> re-run Stages 1–3 and compare against the profile baseline (pruning score, file
> p50, delete ratio, planning time). Keep the profile in version control next to
> the table's definition so the *why* travels with the table.

→ Continue to [Part II · Table-properties optimization](02-recommendations-table-properties.md).
