# Part II · Chapter 2 — Table-properties optimization

> These are the settings baked into the table definition. They govern *layout*
> and *write behavior* and are the most leveraged decisions you make — they shape
> every read and write that follows. Drive each one from the
> [optimization profile](01-methodology-and-analysis.md#stage-5--synthesis-the-optimization-profile).

The decisions, in dependency order: **partitioning → sort/cluster order → file
size → write distribution → COW vs MOR → format/compression → metadata
hygiene.** Earlier choices constrain later ones, so resolve them in that order.

---

## 2.1 Partitioning

**What it does:** physically segregates files by a partition value so the engine
can skip whole directories of files (partition pruning) when a query filters on
that value. Iceberg's *hidden partitioning* applies a transform
(`day`, `month`, `hour`, `bucket[N]`, `truncate[W]`, `identity`) to a column and
tracks it in metadata — queries filter the raw column and pruning happens
automatically, no extra predicate needed.

**Drive it from:** Stage 1 top-filter columns + their cardinality, Stage 2
partition skew, Stage 4 confirmed/planned filters.

**Rules of thumb:**

- Partition on the **most-filtered low-to-moderate-cardinality column**, almost
  always **time** via a transform: `day(ts)` for most analytics, `hour(ts)` only
  for very high-volume near-real-time tables, `month(ts)` for slow/archival.
- **Match granularity to partition size, not to the calendar.** Aim for
  partitions large enough to hold healthy files (hundreds of MB to a few GB).
  Thousands of tiny partitions (the classic `hour` over a low-volume table) is
  over-partitioning — it *causes* the small-file problem rather than helping.
- **Never partition on a high-cardinality column** (`user_id`, `order_id`). Use
  `bucket[N]` if you need to spread a high-cardinality key evenly
  (`bucket(64, user_id)`), which caps the partition count at N while preserving
  join/lookup locality.
- A second partition field is justified only when a second column appears in a
  large share of queries *and* keeps partitions healthily sized (e.g.
  `day(event_date)` + `bucket(16, tenant_id)` for a multi-tenant table where most
  queries are tenant-scoped).
- **Don't partition on a column nobody filters** — it's pure overhead. Cross-check
  the candidate against Stage 1 frequencies.

**Partition evolution:** Iceberg can change the partition spec *without rewriting
history* — old data keeps its old layout, new data uses the new spec, and split
planning handles both. So an early wrong choice is recoverable: evolve the spec,
then let compaction re-lay-out the hot/recent partitions. This is a major reason
not to over-engineer partitioning up front.

```sql
ALTER TABLE db.events ADD PARTITION FIELD bucket(16, tenant_id);
ALTER TABLE db.events DROP PARTITION FIELD hour(event_ts);   -- de-granularize
```

---

## 2.2 Sort order & clustering

**What it does:** orders rows *within* files (and across files written together)
so that values of the sort columns are contiguous. This tightens the per-file
min/max stats Iceberg stores, which powers **file-level and row-group skipping**
for columns that are too high-cardinality to partition on. It also improves
compression.

**Drive it from:** Stage 1 high-selectivity equality/range filters and join keys
that are *not* partition columns; Stage 2 "poorly colocated data" signal.

**Rules of thumb:**

- Set a **table sort order** so every writer (and compaction) maintains locality:
  ```sql
  ALTER TABLE db.events WRITE ORDERED BY tenant_id, user_id;
  ```
- **Linear sort** (`a, b, c`) when there's a clear primary filter column —
  pruning is excellent on the leading column, weaker on later ones.
- **Z-order** (multi-dimensional) when several columns are filtered with similar
  frequency and no single one dominates. Z-order trades a little single-column
  pruning for balanced multi-column pruning. **But its locality decays with each
  column you add, and it only helps queries that filter the clustered columns** —
  don't Z-order "to be safe." For 2+ dimensions a **Hilbert** curve preserves
  locality better than Z-order (the reason Databricks Liquid Clustering uses
  Hilbert). Apply it at compaction time:
  ```sql
  CALL system.rewrite_data_files(
    table => 'db.events',
    strategy => 'sort',
    sort_order => 'zorder(tenant_id, country)');
  ```
- Sorting is only *maintained* if writers respect it (cheap for batch, costly for
  streaming) — for streaming tables it's common to write unsorted fast and
  **restore sort during compaction** (see [maintenance](04-recommendations-maintenance.md)).
- **Platform note:** on Databricks, **Liquid Clustering** supersedes both
  partitioning and Z-order — you declare `CLUSTER BY` keys and the platform
  maintains layout incrementally. On Snowflake-managed tables, a `CLUSTERING KEY`
  drives automatic clustering. See the [platform playbooks](05-platform-playbooks.md).

---

## 2.3 Target file size

**What it does:** `write.target-file-size-bytes` tells writers and compaction the
size to aim for per data file. It's the central lever on the small-file problem.

**Drive it from:** Stage 2 file-size distribution, Stage 0 read pattern, Stage 3
writer type.

**The guidance, with the nuance that matters:**

- Iceberg's **default is 512 MB**. The widely-used safe band for analytical tables
  is **128–512 MB**; **256 MB** is a good general default that balances pruning
  granularity against read parallelism.
- **Parallelism is driven by row-group size, not file size** — files are
  splittable, row groups are not. So "bigger files = better" has limits: oversized
  row groups cause memory pressure and spill at read time, and oversized files
  slow compaction. Keep an eye on row-group size (`write.parquet.row-group-size-bytes`,
  ~128 MB default) alongside file size.
- **Lower the target (128–256 MB)** for: wide/nested tables, executors with
  limited memory, engines that prefer smaller files, and **streaming tables**
  where waiting to fill a 512 MB file would blow the latency SLA.
- Some practitioners deliberately target **much smaller files** in specific
  engines/workloads; treat that as an *engine-validated exception*, not the
  default. Confirm with query plans (scan parallelism, spill), not just metadata.

```sql
ALTER TABLE db.events SET TBLPROPERTIES (
  'write.target-file-size-bytes'='268435456'      -- 256 MB
);
```

> The target *guides* but doesn't strictly enforce output size — and writers
> don't always honor it well (you can set 512 MB and still get ~100 MB files,
> e.g. apache/iceberg #8729). **Verify actual output file sizes from the Stage 2
> distribution after writing/compacting — don't assume the knob worked.** Record
> boundaries, compression, and partition fan-out cause variation. Validate
> against the Stage 2 distribution after a compaction cycle.

---

## 2.4 Write distribution mode

**What it does:** `write.distribution-mode` controls whether the engine shuffles
data before writing so that rows destined for the same partition land in the same
task/file. It's the difference between "every task writes a sliver to every
partition" (fan-out → many small files) and "each partition is written by one
task" (fewer, larger files).

| Mode | Behavior | Use when |
|---|---|---|
| `none` | No shuffle; write as data arrives. Fast writes, **many small files** when tasks span partitions. | Latency-critical streaming where each task already targets one partition, or cost-sensitive writes you'll compact later. |
| `hash` | Shuffle by hashed partition key; one task per partition. Fewer files. | The default choice for **partitioned batch** and most read-optimized tables. |
| `range` | Range-partition the shuffle (also respects sort order). Best file sizing + global ordering, most expensive shuffle. | Sorted/Z-ordered tables where layout quality matters most. |

**Drive it from:** Stage 3 fan-out (files-per-commit vs partitions-touched) and
Stage 4 cost-vs-latency posture. High fan-out + read-optimized table → `hash` or
`range`. Latency-critical + cost-sensitive → `none` + aggressive compaction.

```sql
ALTER TABLE db.events SET TBLPROPERTIES ('write.distribution-mode'='hash');
```

---

## 2.5 Copy-on-Write vs Merge-on-Read

**What it does:** decides *when* the cost of an update/delete is paid. This is set
per operation: `write.update.mode`, `write.delete.mode`, `write.merge.mode`, each
`copy-on-write` (default) or `merge-on-read`.

- **COW** rewrites whole data files at write time with the change applied. Reads
  are clean (no merge), writes are expensive. Best for **read-heavy, low-mutation**
  tables and batch overwrites.
- **MOR** writes small **delete files** (position or equality) and merges them at
  read time. Writes are cheap and fast, reads pay a merge tax that **grows with
  accumulated deletes**. Best for **high-frequency updates/CDC** and streaming.

**Drive it from:** Stage 0 write pattern + mutability, Stage 3 operation mix,
Stage 1 delete-files-per-scan, Stage 4 freshness SLA.

```
   write frequency of updates/deletes ──►
   low                          high
   ┌──────────────┬──────────────────────────┐
   │   COW        │          MOR              │
   │ (clean reads)│ (cheap writes + compact)  │
   └──────────────┴──────────────────────────┘
   read sensitivity ▲ favors COW   ▲ favors MOR + frequent compaction
```

**Delete-type sub-decision (MOR, spec v2):**

- **Position deletes** — point at exact row positions; efficient to read, the
  natural output of engines that know the row position (Flink, Spark MERGE). The
  default and preferred type.
- **Equality deletes** — match on column values; cheap to write (no need to find
  the row), expensive to read. Common in CDC/upsert pipelines that don't know the
  position. Accumulate fast → compact aggressively.

> **Don't pick COW just to "avoid maintenance."** COW shifts cost to writes; on a
> large, frequently-changed table that can be ruinous. The MOR read tax is real
> but is *managed by compaction*, which re-applies deletes into clean base files.
> Choose on workload, not as a maintenance shortcut.

**Spec v3 (GA/preview across platforms in early 2026):** position deletes are
superseded by **deletion vectors** (compact binary, one per data file, stored in
Puffin files) — faster to apply, simpler retention. If your engine and catalog
support v3, prefer it for MOR tables; it narrows the MOR read penalty
substantially.

---

## 2.6 File format & compression

- **Parquet** is the default and right answer for analytics (columnar, great
  pushdown). ORC and Avro exist; Avro suits row-oriented/streaming-write cases but
  is rarely the analytics choice.
- **Compression** via `write.parquet.compression-codec`: **`zstd`** is the modern
  default — better ratio than `snappy` at comparable speed, which means fewer
  bytes scanned. `snappy` only if a downstream consumer mandates it.
- Tune `write.parquet.row-group-size-bytes` (read parallelism unit, see §2.3) and
  enable dictionary encoding (default) for low-cardinality string columns.
- **Column-level stats:** Iceberg stores min/max/null/count per column up to
  `write.metadata.metrics.max-inferred-column-defaults` (default 100 columns).
  For very wide tables, queries filter on columns beyond that cutoff get no
  skipping → set `write.metadata.metrics.column.<col>=full` for the columns that
  actually filter (from Stage 1), and `none` for large free-text columns you never
  filter (storing their min/max is wasted metadata).

---

## 2.7 Metadata-hygiene properties

Set-and-forget knobs that keep metadata from bloating; complements the active
work in [maintenance](04-recommendations-maintenance.md).

| Property | Recommended | Why |
|---|---|---|
| `write.metadata.delete-after-commit.enabled` | `true` | Auto-expire old `metadata.json` files on commit. |
| `write.metadata.previous-versions-max` | `50–100` | Cap retained `metadata.json` versions (pairs with above). |
| `commit.retry.num-retries` | `4–10` (higher for multi-writer) | Survive optimistic-concurrency commit conflicts. |
| `commit.retry.min-wait-ms` | tune up under contention | Backoff between retries. |
| `history.expire.max-ref-age-ms` | set on non-`main` refs | Auto-expire stale **branches/tags** so they don't pin old snapshots/files. |
| `write.spark.fanout.enabled` | `true` for unsorted streaming writes | Avoids per-partition sort buffering in fan-out writes (at the cost of more open files). |

> Branches and tags **block snapshot expiration** by design — a forgotten WAP
> branch or audit tag will silently prevent file cleanup. Audit `<table>.refs`
> periodically and set `max-ref-age-ms` where appropriate.

→ Continue to [Ingestion optimization](03-recommendations-ingestion.md).
