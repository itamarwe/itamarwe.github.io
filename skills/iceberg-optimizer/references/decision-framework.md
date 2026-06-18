# Decision framework: profile + workload → ranked candidates

This combines the Phase 1 profile (physical state) with the Phase 2 workload
(ingestion + access + intent) into candidate actions. Each action carries a
**trigger** (when the metadata says it is needed) and an **intent gate** (when it
is actually worth doing). An action is a candidate only if its trigger fires
*and* its gate passes. Phase 4 then simulates the survivors.

The cardinal rule: **a metadata trigger is necessary, not sufficient.** Small
files on a table nobody queries are not a problem worth paying to fix.

---

## Step 1 — Compute signals

From the profile (`profile.json`):

```
avg_file_mb, median_file_mb, files_under_64mb_pct, total_files, total_gb
delete_file_pct           = delete_files / total_files
eq_delete_pressure        = equality_delete_records / data_records  # >0.05 = urgent
pos_delete_pressure       = position_delete_records / data_records
delete_rate_per_day       = added_delete_files / observation_span_days
partition_skew_ratio      = max_partition_rows / min_partition_rows
snapshot_count, manifest_count, avg_files_per_manifest, mixed_partition_specs (bool)
write_cadence_class, avg_added_file_mb, thin_spread (bool), late_data (bool)
operation_mix
format_version            = 1 or 2 (from table properties / DESCRIBE EXTENDED)
has_sort_order            = bool (table has a persisted WRITE ORDERED BY / sorted_by)
```

From the workload (`workload.json` + interview):

```
top_filter_cols [(col, count, predicate_type, cardinality_class), ...]
partition_prune_rate      = fraction of queries pruned to ≤10% of partitions
selectivity               = rows_scanned / rows_returned (higher = more selective)
query_frequency_class, latency_req, freshness_req, cost_priority
mutability_outlook, time_travel_need, lifecycle_class
retention_policy          = none / ttl / gdpr / regulatory_floor / mixed
current_sort_order, current_partition_spec
```

---

## Step 2 — Candidate actions

### A. Bin-pack compaction
- **Trigger:** `avg_file_mb < 64` OR `files_under_64mb_pct > 0.3` OR thin_spread.
- **Gate:** `lifecycle ≠ cold` OR `query_frequency ∉ {rare, almost_never}`.
  (If cold *and* rarely read, skip — see "Do nothing".)
- **Note:** if `avg_added_file_mb` is already near target, the small files are
  historical, not ongoing — a one-off compaction suffices, no recurring job.

### B. Sort compaction (single / hierarchical key)
- **Trigger:** `selectivity` high AND `len(top_filter_cols) ≥ 1` AND the top
  filter column is **not** the current sort key.
- **Gate:** `latency_req = interactive` AND `query_frequency ∈ {constant, regular}`.
- **Pick key:** the most frequent filter column used in **range** predicates;
  add secondary columns hierarchically. Don't sort by the partition column.
- **Wide/nested table note:** Tables with many columns (>100) or deeply nested
  structs put more memory pressure during sort. Consider using a smaller
  `target-file-size-bytes` (128–256 MB instead of 512 MB) to avoid executor
  spill during compaction and to keep row groups below ~128 MB in the output
  files — oversized row groups limit parallelism since row groups are not
  splittable within a file.

### C. Z-order compaction (multi-dimensional)
- **Trigger:** 2–4 high-cardinality columns appear in `WHERE` clauses in varying
  combinations (no single dominant column).
- **Gate:** same as Sort, plus columns are high-cardinality. Cap at 3–4 columns;
  locality degrades past that.
- **Sort vs Z-order:** one dominant filter column → Sort. Several co-equal
  high-cardinality filters → Z-order.

### D. Partition evolution / repartition
- **Trigger:** `partition_prune_rate < 0.5` (queries scan most partitions) OR
  `partition_skew_ratio > 10` OR partition granularity mismatches query grain
  (e.g. partitioned monthly but filtered by day) OR too many partitions
  (> ~10k with queries spanning many).
- **Gate:** `query_frequency ∈ {constant, regular}` (otherwise not worth it).
- **How:** metadata-only `ALTER TABLE … ADD/DROP/REPLACE PARTITION FIELD`
  (sub-second, zero downtime). Old data keeps its spec; optionally `rewrite-all`
  compact old partitions to migrate them. Skew on identity transform → switch to
  `bucket(N, col)`.
- **Hidden partitioning note:** Iceberg's `bucket(N, col)` and `truncate(N, col)`
  transforms are *hidden* — query engines pass plain predicates (e.g.,
  `WHERE col = X`); Iceberg applies the transform invisibly for pruning. Writers
  distribute rows by hash bucket, avoiding hotspots. Identity partitions expose
  raw values and can cause skew on high-cardinality columns or uneven data
  distributions. Prefer `bucket` transforms for update-heavy or high-cardinality
  partition columns; use identity only for natural, low-cardinality dimensions
  (e.g., date, region). Bucket count `N`: start at `ceil(table_size_gb / 1)` up to
  ~1000; a good heuristic is that each bucket should hold 1–5 GB of data at steady
  state. Too few buckets → skew; too many → metadata overhead.
- **Rank override:** if `partition_prune_rate < 0.2` AND the dominant filter column
  is **not** in the current partition spec, promote D *above* B/C in ROI ranking.
  Partition evolution is a metadata-only operation (zero data rewrite) that
  eliminates full-table scans permanently; sort/z-order is a full data rewrite
  that only improves data skipping within a scan that still touches all partitions.

### E. Delete-file compaction

Equality deletes (content=2) and position deletes (content=1) require different
urgency: equality deletes are applied as a join against **every data file** on
every scan until compacted — their cost grows with table size, not delete count.
Position deletes are a row-level seek per file and are far cheaper.

**E1 — Equality delete compaction (urgent):**
- **Trigger:** `eq_delete_pressure > 0.05` (equality_delete_records / data_records)
  OR `equality_delete_files > 0` AND `delete_accumulating` (growing, not stable).
- **Gate (performance path):** `query_frequency ∉ {almost_never}`.
- **Gate (compliance path):** `retention_policy ∈ {gdpr}` → **no gate** — compact
  regardless of query frequency. GDPR tables must physically remove data; logical
  deletion (the delete file) is not sufficient. The compliance sequence is:
  `DELETE row` → `rewrite_data_files(remove-dangling-deletes)` → `expire_snapshots`
  → verify no snapshot older than the deletion predates expiry retention.
- **Write-mode note:** equality deletes indicate merge-on-read (MOR) mode. If the
  workload is update-heavy, consider switching to copy-on-write
  (`write.merge.mode = copy-on-write`) — it rewrites at write time instead of
  accumulating delete files. COW trades higher write cost for lower read cost.

**E2 — Position delete compaction (lower urgency):**
- **Trigger:** `pos_delete_pressure > 0.2` OR `delete_file_pct > 0.1` with only
  position delete files.
- **Gate:** `query_frequency ∉ {almost_never}` (position deletes have milder
  per-scan cost than equality deletes, so the threshold is higher).
- Position deletes are typical for `MERGE INTO` CDC pipelines and streaming upserts.

**For both:** use `rewrite_data_files` with `remove-dangling-deletes: true`.

### F. Snapshot expiry
- **Trigger:** `snapshot_count` large OR storage growth from retained snapshots.
- **Gate:** retention floor = `time_travel_need`. If replay/audit is relied on,
  keep at least the required window; otherwise expire to a small N.
- **Always low-cost** (metadata-only) — include in almost every plan, but size
  the retention to intent.

### G. Manifest rewrite / clustering
- **Trigger:** `manifest_count > ~500` OR `avg_files_per_manifest < 100` with
  many manifests OR `mixed_partition_specs` OR manifest-level pruning is poor
  (planner reads all manifests for narrow partition queries).
- **Gate:** none meaningful — cheap, safe; include when triggered.
- **Two goals — choose per situation:**
  1. **Consolidation** (default): `rewrite_manifests(table => '...')` merges many
     small manifests into fewer large ones → reduces planning I/O.
  2. **Clustering** (when `partition_prune_rate` is poor despite partition match):
     `rewrite_manifests(table => '...', sort_by => array('<partition_col>'))` (Spark)
     reorders manifests so each covers a contiguous partition range → the planner
     can skip entire manifests for narrow filters without reading their file lists.
     Use this when the partition spec is correct but queries still read many
     manifests (common after many small streaming commits scatter files across
     manifests randomly). Trino `optimize_manifests` consolidates but does not
     sort — use Spark for clustering.
- **Planning cost proxy:** `manifest_count × avg_manifest_mb` is proportional to
  planning I/O per query. Reducing either shrinks latency for all queries
  regardless of data skipping.

### H. Orphan-file removal
- **Trigger:** suspected failed writes / aborted jobs / external file ops.
- **Gate:** **safety, not intent** — `older_than` ≥ longest possible write
  (default 3 days; never shorter). Run *after* snapshot expiry. Deletes files —
  always `dry_run` first.

### I. Bloom filters
- **Trigger:** high-cardinality columns used in **equality** predicates where
  min/max skipping is useless.
- **Gate:** `latency_req = interactive` AND those point-lookups are frequent.
- **Cost:** ~1 MB/column/file; set `write.parquet.bloom-filter-enabled.column.<c>`.

### J. Write-time tuning (often the real fix)
- **Trigger:** thin_spread OR tiny `avg_added_file_mb` at write.
- **Action:** set `write.distribution-mode = hash`, honor
  `write.target-file-size-bytes`, define a table sort order
  (`ALTER TABLE … WRITE ORDERED BY …`) so writers cluster up front and downstream
  compaction shrinks. Fixing ingestion beats perpetually compacting its output.
- **Interaction with K (write-time sort order):** `distribution-mode = hash`
  controls *which partition a row goes to* (prevents thin spread — rows for the
  same sort key landing in different tasks). Write-time sort order (K) controls
  *the order of rows within each file*. Apply J first (stop the thin spread) then
  K (add the sort order). Both together produce well-sized, clustered files at
  zero extra maintenance cost. Without `hash` distribution, a sort order may have
  limited effect because rows destined for the same sort-key range are still spread
  across many small files in different tasks.

### K. Write-time sort order (free clustering, no rewrite)
- **Trigger:** `has_sort_order = false` AND top filter column is used in range
  predicates AND `avg_added_file_mb` is near-target (writer already buffers — so
  adding a sort order will produce well-sized, sorted files at zero extra cost).
- **Gate:** `write_cadence ∈ {batch, micro_batch}` — writers must buffer enough
  rows to sort meaningfully. Streaming writers with tiny micro-batches benefit
  less (sort within a 1 MB file has limited skip value).
- **Action (Spark):** `ALTER TABLE cat.db.tbl WRITE ORDERED BY <col> [ASC|DESC] NULLS LAST`
  — persisted as the table sort order; all future writes cluster by `<col>`.
  **Action (Trino):** `ALTER TABLE cat.db.tbl SET PROPERTIES sorted_by = ARRAY['<col>']`
- **Why this ranks above B (compaction sort) in many cases:** Compaction sort
  rewrites existing data (full I/O cost, paid once or periodically). Write-time
  sort order clusters *all new data for free* — no rewrite, no maintenance job.
  The correct sequence is K first (stop writing unsorted data), then B once to
  retroactively sort the existing backlog if selectivity justifies it.
- **Does not help:** tables with late-arriving out-of-order data (`late_data =
  true`) — sort order at write time only clusters data written in a single batch;
  late files arriving into old partitions remain unsorted relative to what's
  already there.

### L. Format-version upgrade (one-time prerequisite)
- **Trigger:** `format_version = 1` AND the table has or will have row-level
  deletes (equality or position delete files), OR `mutability_outlook ∈
  {updates, deletes, gdpr}`.
- **Gate:** none — always upgrade before E1/E2 compaction or any merge-on-read
  workload. V2 enables row-level deletes, merge-on-read, and Puffin statistics
  (bloom filters, column-level NDV). V1 tables can have equality deletes *written*
  by Spark but the format is technically non-compliant; upgrade to v2 first.
- **Action:** `ALTER TABLE cat.db.tbl SET TBLPROPERTIES ('format-version' = '2')`
  — metadata-only, instant, zero downtime, backwards-compatible (all existing
  files remain valid).
- **Rank:** Execute before E1/E2 in the plan. It is a prerequisite, not a
  performance action — list it as "Step 0" in any plan that involves delete-file
  compaction.
- **V3 note:** Iceberg v3 replaces position delete files with **deletion vectors**
  (compact per-file bitmaps). This reduces delete-file count, simplifies retention,
  and lowers per-scan merge overhead. Upgrade from v2 to v3 when your engine
  supports it. Compaction semantics (`rewrite_data_files`) are the same; the
  output delete format is just more efficient. For current-generation deployments
  target v2; plan v3 as a follow-on upgrade once engine support is confirmed.

### Z. Do nothing / minimal
- **When:** `lifecycle = cold` AND `query_frequency ∈ {rare, almost_never}` AND
  no delete-file pressure. Recommend at most periodic snapshot expiry for storage.
- **Rationale:** maintenance compute is a real, recurring cost. If the table is
  read a handful of times, the cheapest total-cost option is to leave it and let
  queries pay the scan. **State this outcome explicitly** rather than defaulting
  to a runbook. Phase 4 will quantify it as the "Do-nothing" baseline.

---

## Step 3 — Rank by ROI

Order surviving candidates by expected benefit per unit cost, conditioned on
`cost_priority`:

0. **Format-version upgrade** (L) — one-time prerequisite; execute before any
   delete-related action. Zero cost, zero downtime.
1. **Equality delete compaction** (E1) — highest urgency: equality deletes penalize
   every scan regardless of which rows are actually queried. Compliance tables
   (GDPR) have no opt-out.
2. **Position delete compaction** (E2) — high read win when position deletes
   accumulate, but lower urgency than equality deletes.
3. **Write-time sort order** (K) — free clustering for all future writes; no
   rewrite cost. Prefer over compaction sort (B) when the writer buffers well.
   Exception: rank D above K when `partition_prune_rate < 0.2` and the dominant
   filter column is not in the partition spec (see D rank override).
4. **Partition evolution** (D) — when pruning is poor. Ranked above sort/z-order
   when `partition_prune_rate < 0.2` and dominant filter column is not a partition
   key (metadata-only fix that eliminates full scans; z-order only improves skipping
   within a scan that already touches all partitions).
5. **Sort / Z-order** (B/C) — when selective + frequently read + K alone is insufficient
   (e.g. need to retroactively sort the existing backlog).
6. **Bin-pack** (A) — pure small-file latency/planning fix.
7. **Write-time tuning** (J) — stops the bleeding; pairs with A.
8. **Bloom filters** (I) — marginal outside frequent point lookups.
9. **Metadata cleanup** (F/G/H) — low cost, almost always worth it; size to intent.
   Note: for GDPR tables, F (snapshot expiry) moves to rank 1 alongside E1 — they
   must run together in sequence (compact first, then expire) to physically remove data.

Then hand the ranked candidates to `simulate.py`, which prices each bundle along
the four axes and re-orders by the user's chosen `cost_priority`. The framework
proposes; the simulation decides.

---

## Worked mini-examples

- **Streaming events, interactive dashboards, queried constantly, filter by
  `tenant_id` + `event_time`, no replay need:** E (if deletes) → C z-order
  `(tenant_id, event_time)` → A on cold partitions every 1–4 h → F aggressive
  expiry (retain ~10) → J `distribution-mode=hash` → G manifest clustering
  (`sort_by tenant_id`) if manifest scatter is high.
- **Daily batch fact table, BI queries by `date`, append-only, monthly reports:**
  K write-time sort order by `date` (free, applies to all new loads) → B sort
  compaction once on existing backlog → F daily expiry (retain to reporting window)
  → G after load.
- **Cold archive, queried a few times a year:** Z do nothing except quarterly
  snapshot expiry for storage. No compaction, no sort — the scan is cheaper than
  the maintenance.
- **GDPR table with user_id deletes, any query frequency:** L upgrade to v2 (if
  on v1) → E1 equality-delete compaction → F snapshot expiry (≥ deletion date),
  in that order, on a schedule that honors the 30-day regulatory clock. COW
  (`write.merge.mode = copy-on-write`) considered if delete rate is high (eliminates
  delete-file accumulation entirely). **State explicitly:** snapshot expiry is part
  of the compliance posture — retained snapshots expose the deleted rows.
- **High-churn SCD/CDC table (position deletes, merge-on-read):** E2 position-delete
  compaction with `remove-dangling-deletes` → optionally switch to COW if write
  throughput permits. K write-time sort by the merge key; B compaction sort on
  the backlog if scans are selective.
- **Partition-misalignment (partitioned by `event_date`, queried 98% by `tenant_id`,
  `partition_prune_rate = 0.0`):** D partition evolution (add `bucket(N, tenant_id)`
  as leading field — metadata-only, zero downtime) → G manifest clustering
  (`sort_by tenant_id`) → K write-time sort by `tenant_id`. Z-order is a valid
  but more expensive alternative if partition evolution is blocked (e.g. very large
  table with no maintenance window for `rewrite-all`).
