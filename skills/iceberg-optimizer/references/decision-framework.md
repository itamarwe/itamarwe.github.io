# Decision framework: profile + workload → ranked candidates

This combines the Phase 1 profile (physical state), Phase 2a workload (ingestion pipeline
analysis + access patterns), and Phase 2b intent into candidate actions organized in three
groups. An action is a candidate only when its **trigger** fires AND its **intent gate**
passes. Phase 4 simulates the survivors.

The cardinal rule: **a metadata trigger is necessary, not sufficient.** Small files on a
table nobody queries are not a problem worth paying to fix.

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
format_version            = 1 or 2 (from table properties / DESCRIBE EXTENDED)
has_sort_order            = bool (table has a persisted WRITE ORDERED BY / sorted_by)
```

From the ingestion analysis (`workload.json` ingestion signals):

```
write_cadence_class       = streaming | micro_batch | batch
avg_added_file_mb         = mean file size at write time
thin_spread               = bool (each commit scatters tiny files across many partitions)
late_data                 = bool (recently-committed files contain old event-times)
operation_mix             = {append, overwrite, merge, delete} frequencies
writer_type               = flink | spark_streaming | spark_batch | kafka_connect | cdc | nifi | beam_dataflow | airbyte | fivetran | aws_dms | unknown
distribution_mode         = none | hash | range | unknown (from table properties or user)
ingestion_write_mode      = mor | cow | append_only (from table properties or user)
checkpoint_interval_secs  = derived or asked (Flink / Spark SS checkpoint period)
```

From the workload and interview:

```
top_filter_cols [(col, count, predicate_type, cardinality_class), ...]
partition_prune_rate      = fraction of queries pruned to ≤10% of partitions
selectivity               = rows_scanned / rows_returned
query_frequency_class, latency_req, freshness_req, cost_priority
mutability_outlook, time_travel_need, lifecycle_class
retention_policy          = none | ttl | gdpr | regulatory_floor | mixed
current_sort_order, current_partition_spec
```

---

## Step 2 — Candidate actions (three groups)

A plan can combine actions from multiple groups. The groups are not mutually exclusive —
a complete plan often includes actions from all three simultaneously.

---

### GROUP 1: TABLE LAYOUT
*Configuration decisions about what the table is: partition spec, sort order, bloom filters,
and format version. Mostly metadata changes; they take effect immediately for future writes
and queries. Run before compaction — there is no point compacting into a layout you are
about to change.*

#### D. Partition evolution / repartition
- **Trigger:** `partition_prune_rate < 0.5` OR `partition_skew_ratio > 10` OR partition
  granularity mismatches query grain OR too many partitions (> ~10k spanning many queries).
- **Gate:** `query_frequency ∈ {constant, regular}`.
- **How:** metadata-only `ALTER TABLE … ADD/DROP/REPLACE PARTITION FIELD` — sub-second,
  zero downtime. Old data keeps its spec; optionally compact old partitions to migrate them.
- **Bucket vs identity:** prefer `bucket(N, col)` for high-cardinality or update-heavy
  columns. Bucket count `N` heuristic: `ceil(table_size_gb / 1)` up to ~1000; each bucket
  should hold 1–5 GB at steady state.
- **Rank override:** if `partition_prune_rate < 0.2` AND dominant filter column is NOT in
  partition spec, promote D above everything in Group 3 — partition evolution is metadata-only
  and permanently eliminates full-table scans; compaction only improves skipping within a
  scan that still touches all partitions.

#### K. Write-time sort order (free clustering, no rewrite cost)
- **Prerequisite check:** if `has_sort_order = true`, **skip K entirely** — state
  explicitly: "Write-time sort order is already configured." When `late_data = true`,
  the remedy is B (sort compaction on affected partitions, Group 3), not K.
- **Trigger:** `has_sort_order = false` AND `avg_added_file_mb ≥ 64` (writers buffer
  enough to sort meaningfully).
- **Gate:** `write_cadence ∈ {batch, micro_batch}` — streaming micro-batches benefit less.
- **Applies to both range and equality predicates:** sort on an equality column groups
  matching rows into contiguous file ranges, enabling file-level skipping even for point
  lookups. Low-cardinality equality columns (5–50 distinct values) still benefit.
- **Rank:** prefer K over B (Group 3) when the writer buffers well — K clusters all future
  writes for free; B rewrites existing data. Set K first, then run B once to retroactively
  sort the existing backlog.
- **Interaction with J (Group 2):** `distribution-mode=hash` (J) routes rows to the right
  partition task; K then orders rows within each file. Apply J first, then K — without hash
  distribution, the sort order is applied per-task and produces many small sorted files.

#### I. Bloom filters
- **Trigger:** high-cardinality columns used in **equality** predicates where min/max
  skipping is useless (e.g. UUID, product_id, user_id with millions of distinct values).
- **Gate:** `latency_req = interactive` AND those point-lookups are frequent.
- **Cost:** ~1 MB/column/file. Set `write.parquet.bloom-filter-enabled.column.<c>`.
- **Do NOT set on:** range-predicate columns (bloom filters are useless for ranges) or
  low-cardinality columns (< ~1000 distinct values — min/max skipping already works).

#### L. Format-version upgrade (prerequisite for row-level deletes)
- **Trigger:** `format_version = 1` AND table has or will have row-level deletes, OR
  `mutability_outlook ∈ {updates, deletes, gdpr}`.
- **Gate:** none — always run before E1/E2 (Group 3).
- **Action:** `ALTER TABLE … SET TBLPROPERTIES ('format-version' = '2')` — metadata-only,
  instant, backwards-compatible. Iceberg v1 tables cannot safely accumulate equality-delete
  files; upgrade to v2 unlocks native row-level delete support.
- **V3 note:** Iceberg v3 replaces position deletes with deletion vectors. Target v2 now;
  plan v3 as a follow-on when engine support is confirmed.

---

### GROUP 2: INGESTION
*Changes to how data enters the table — fixes the root cause rather than the symptom.*

**Loading note:** load `engines/ingestion.md` when any Group 2 action is recommended.

#### J. Write-time distribution and file-size tuning
- **Trigger:** `thin_spread = true` OR `avg_added_file_mb < 32` OR
  `distribution_mode ≠ hash` (inferred from table properties or user confirmation).
- **Gate:** none — fixing ingestion is always the right move when it is the root cause of
  small files. It prevents the small-file problem from recurring regardless of how often
  compaction runs.
- **Actions (by writer type):**
  - **Flink:** set `write.distribution-mode=hash`, `write.target-file-size-bytes=268435456`,
    increase checkpoint interval to 5–15 minutes.
  - **Spark Structured Streaming:** set `write.distribution-mode=hash`, increase
    `ProcessingTime` trigger interval to 5–15 minutes.
  - **Kafka Connect:** set `file.commit.mode=commit-based`, `iceberg.tables.dynamic.enabled=true`.
  - **Batch:** set `write.distribution-mode=hash` as a table property; it is respected by
    all writers at write time.
  - **Snowflake-managed:** set `TARGET_FILE_SIZE` on the table; Snowflake manages distribution.
- **Interaction with K (Group 1):** distribution mode controls *which partition a row goes
  to* (prevents thin spread). Write-time sort order (K, Group 1) controls *row order within
  each file*. Apply J first (stop thin spread), then K (add sort order). Both together
  produce well-sized, clustered files at zero extra maintenance cost.
- **CDC write-mode switch (COW):** if `ingestion_write_mode = mor` AND
  `eq_delete_pressure` is high, consider switching to COW. See `engines/ingestion.md`.

---

### GROUP 3: MAINTENANCE
*Operations on data already on disk: all compaction (bin-pack, sort, z-order, delete-file),
snapshot expiry, orphan cleanup, and manifest consolidation. These are recurring; the right
schedule and strategy depend on write cadence, query frequency, and lifecycle class.*

#### A. Bin-pack compaction
- **Trigger:** `avg_file_mb < 64` OR `files_under_64mb_pct > 0.3` OR `thin_spread`.
- **Gate:** `lifecycle ≠ cold` OR `query_frequency ∉ {rare, almost_never}`.
- **Note:** if `avg_added_file_mb` is already near target, the small files are historical,
  not ongoing — a one-off compaction suffices; no recurring job.

#### B. Sort compaction (single / hierarchical key)
- **Trigger:** `selectivity` high AND `len(top_filter_cols) ≥ 1` AND top filter column is
  **not** the current sort key OR `late_data = true` (sort order disrupted in old partitions).
- **Gate:** `latency_req = interactive` AND `query_frequency ∈ {constant, regular}`.
- **Pick key:** most frequent range-predicate filter column; add secondary columns
  hierarchically. Don't sort by the partition column.
- **Wide-table note:** for 100+ column or deeply-nested schemas, reduce
  `target-file-size-bytes` to 128–256 MB to avoid executor spill.
- **Late-data note:** if `late_data = true`, scope compaction to recently-modified
  partitions only via `WHERE`. Check `has_sort_order` — if true, K (Group 1) is already
  set; B is the fix for the existing backlog, not K.

#### C. Z-order compaction (multi-dimensional)
- **Trigger:** 2–4 columns in `WHERE` clauses in varying combinations (no dominant
  single column) AND **at least one column uses range predicates**.
- **Gate:** same as Sort, plus columns are high-cardinality (>1000 distinct values). Cap
  at 3–4 columns — locality degrades past that.
- **Predicate-type rule:** Z-order helps when you need to skip on an **equality AND a
  range** column simultaneously (e.g. `tenant_id = X AND event_time BETWEEN a AND b`).
  **If ALL filter columns use equality predicates only, do NOT recommend Z-order — choose
  Sort (B) or K (Group 1) instead.** Sort on the top equality column groups matching rows
  into contiguous files and achieves equivalent skipping at lower cost.

#### E1. Equality-delete compaction (urgent)
- **Trigger:** `eq_delete_pressure > 0.05` OR equality delete files growing (not stable).
- **Gate (performance):** `query_frequency ∉ {almost_never}`.
- **Gate (compliance):** `retention_policy = gdpr` → **no gate** — compact regardless of
  query frequency. GDPR requires physical removal: `DELETE` → compact → expire snapshots.
- **Format prerequisite:** table must be format v2 before running E1 — check L (Group 1).
- **COW note:** if update throughput is moderate and read frequency is high, switching to
  `write.merge.mode = copy-on-write` (Group 2, J action) eliminates future equality-delete
  accumulation entirely.

#### E2. Position-delete compaction (lower urgency)
- **Trigger:** `pos_delete_pressure > 0.2` OR `delete_file_pct > 0.1` with only position
  deletes.
- **Gate:** `query_frequency ∉ {almost_never}`.
- Use `rewrite_data_files` with `remove-dangling-deletes: true` for both E1 and E2.

#### F. Snapshot expiry
- **Trigger:** `snapshot_count` large OR storage growth from retained snapshots.
- **Gate:** retention floor = `time_travel_need`. Keep at least the required window;
  otherwise expire aggressively.
- **Time-based vs count-based:** for high-frequency tables (> 100 commits/day), use
  `max-snapshot-age-ms` not `retain_last` — count-based expiry at 1 commit/min gives
  only a 100-minute window at `retain_last=100`.
- **GDPR note:** snapshot expiry is part of the compliance posture — retained snapshots
  expose logically-deleted rows. Must run after E1 compaction.

#### G. Manifest rewrite / clustering
- **Trigger:** `manifest_count > ~500` OR `avg_files_per_manifest < 100` with many
  manifests OR `mixed_partition_specs` OR manifest pruning poor despite correct partition
  spec.
- **Gate:** none — cheap, safe; include when triggered.
- **Consolidate** (default): merges small manifests, reduces planning I/O.
- **Cluster** (`sort_by` option in Spark): reorders manifests so each covers a contiguous
  partition range — enables manifest-level pruning for narrow filters. Spark-only.
- **Trino:** `optimize_manifests` consolidates but does not cluster.

#### H. Orphan-file removal (destructive)
- **Trigger:** suspected failed writes / aborted jobs / external file operations.
- **Gate:** safety gate — `older_than ≥ longest possible write` (default 3 days; never
  shorter). Run *after* snapshot expiry. **Always `dry_run` first.**

#### I. Bloom filters
- **Trigger:** high-cardinality columns used in **equality** predicates where min/max
  skipping is useless (e.g. UUID, product_id, user_id with millions of distinct values).
- **Gate:** `latency_req = interactive` AND those point-lookups are frequent.
- **Cost:** ~1 MB/column/file. Set `write.parquet.bloom-filter-enabled.column.<c>`.
- **Do NOT set on:** range-predicate columns (bloom filters are useless for ranges) or
  low-cardinality columns (< ~1000 distinct values — min/max skipping already works).

#### Z. Do nothing / minimal
- **When:** `lifecycle = cold` AND `query_frequency ∈ {rare, almost_never}` AND no
  delete-file pressure AND no compliance requirement.
- **Rationale:** maintenance compute is a real, recurring cost. If the table is read a
  handful of times per year, the cheapest total-cost option is to pay at query time.
- **State this explicitly** rather than defaulting to a runbook. Phase 4 will quantify
  it as the "Do-nothing" baseline.

---

## Step 3 — Rank by ROI

Order surviving candidates by expected benefit per unit cost, conditioned on `cost_priority`.
Actions from different groups combine — a complete plan often looks like: Group 2 ingestion
fixes (J) + Group 1 table layout changes (D, K) + Group 3 compaction and housekeeping
(B or E1, A, F, G, H).

**Sequencing rule across groups:**
1. **Group 2 (Ingestion) first — always.** Fixing the writer prevents the problem from
   recurring. Compacting without fixing the writer is a treadmill.
2. **Group 1 (Table Layout) before Group 3 compaction.** Change partition spec, sort order,
   and format version before rewriting data. Compacting into a layout you are about to
   change wastes compute.
3. **Group 3 (Maintenance): compact → expire snapshots → remove orphans → rewrite manifests.**
   Never orphan-cleanup before snapshot expiry.

Default ranking within Group 1:
0. **L** (format upgrade) — prerequisite for E1/E2; metadata-only, zero cost. Run first.
1. **D** (partition evolution) — when `partition_prune_rate < 0.2`; metadata-only; elevate
   above all Group 3 compaction when dominant filter is not in the partition spec.
2. **K** (sort order) — free clustering for all future writes; set before running B.
3. **I** (bloom filters) — marginal except for frequent equality point lookups.

Default ranking within Group 2:
1. **J** (write-time distribution + file sizing) — root-cause fix for thin-spread / small
   files. CDC COW switch is part of J.

Default ranking within Group 3:
1. **E1** (equality-delete compaction) — urgent; GDPR tables have no opt-out.
2. **E2** (position-delete compaction) — high read win when deletes accumulate.
3. **B / C** (sort / z-order) — when selective + frequently read; B after K is set.
4. **A** (bin-pack) — pure small-file fix; lower urgency when B/C already covers it.
5. **F** (snapshot expiry) — almost always include; size to time-travel need. For GDPR,
   move to rank 1 after E1 (compact first, then expire).
6. **G / H** (manifest rewrite / orphan removal) — low cost; include when triggered.

Then hand the ranked candidates to `simulate.py`, which prices each bundle along the
four axes and re-orders by the user's chosen `cost_priority`.

---

## Worked mini-examples

- **Streaming events, interactive dashboards, filter by `tenant_id` + `event_time`
  (equality + range), Flink writer with thin spread:** J `distribution-mode=hash` +
  checkpoint interval (Group 2) → C z-order `(tenant_id, event_time)` + A on cold
  partitions (Group 3) → F aggressive expiry (Group 3).
- **Flink with equality-only filters (`event_type`, `region`), thin_spread=true:** J
  `distribution-mode=hash` (Group 2) → K write-time sort by `(event_type, region)`
  (Group 1) → A bin-pack cold partitions + G manifest rewrite (Group 3). **Do NOT
  recommend Z-order** — all filters are equality-only.
- **CDC MOR table, high `eq_delete_pressure`, frequent queries:** J → switch to COW
  (Group 2) to stop future accumulation; OR L upgrade to v2 (Group 1) + E1
  equality-delete compaction (Group 3) + F expiry (Group 3).
- **Batch ETL, daily loads, write-time sort order already set, 5% late data:**
  K already configured (`has_sort_order = true`) — skip it. B sort compaction on
  recently-modified partitions only (`WHERE event_date IN (recent N days)`) + F daily
  expiry (Group 3).
- **Cold archive, 3 queries/year:** Z do nothing (Group 3) — periodic snapshot expiry
  for storage only. No compaction, no sort.
- **GDPR table, any frequency:** L format upgrade if v1 (Group 1) → E1 compact first →
  F expire snapshots after (Group 3 compliance sequence). If already COW, snapshot expiry
  alone suffices after each deletion batch.
- **Snowflake-managed Iceberg, interactive BI, high `eq_delete_pressure`:** J → switch to
  COW write modes (Group 2) → `COMPACT` for the backlog (Group 3) → `EXPIRE_SNAPSHOTS`
  (Group 3). For sort/z-order, run via Spark; load `engines/snowflake.md` for
  refresh/coordination steps.
- **Partition misalignment (`partition_prune_rate = 0.0`):** D partition evolution (Group 1,
  metadata-only) → K write-time sort by dominant filter column (Group 1) → G manifest
  clustering (Group 3). Z-order is a valid but more expensive alternative to K+B if
  partition evolution is blocked.
