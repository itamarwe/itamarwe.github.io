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
snapshot_count, manifest_count, mixed_partition_specs (bool)
write_cadence_class, avg_added_file_mb, thin_spread (bool), late_data (bool)
operation_mix
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

### G. Manifest rewrite
- **Trigger:** `manifest_count > ~500` OR `mixed_partition_specs` OR many small
  manifests from high commit frequency.
- **Gate:** none meaningful — cheap, safe; include when triggered.

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

1. **Equality delete compaction** (E1) — highest urgency: equality deletes penalize
   every scan regardless of which rows are actually queried. Compliance tables
   (GDPR) have no opt-out.
2. **Position delete compaction** (E2) — high read win when position deletes
   accumulate, but lower urgency than equality deletes.
3. **Sort / Z-order** (B/C) — when selective + frequently read.
4. **Partition evolution** (D) — when pruning is poor.
5. **Bin-pack** (A) — pure small-file latency/planning fix.
6. **Write-time tuning** (J) — stops the bleeding; pairs with A.
7. **Bloom filters** (I) — marginal outside frequent point lookups.
8. **Metadata cleanup** (F/G/H) — low cost, almost always worth it; size to intent.
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
  expiry (retain ~10) → J `distribution-mode=hash`.
- **Daily batch fact table, BI queries by `date`, append-only, monthly reports:**
  B sort by `date` after each load → F daily expiry (retain to reporting window)
  → G after load. No streaming compaction.
- **Cold archive, queried a few times a year:** Z do nothing except quarterly
  snapshot expiry for storage. No compaction, no sort — the scan is cheaper than
  the maintenance.
- **GDPR table with user_id deletes, any query frequency:** E1 equality-delete
  compaction → F snapshot expiry (≥ deletion date), in that order, on a schedule
  that honors the 30-day regulatory clock. COW (`write.merge.mode = copy-on-write`)
  considered if delete rate is high (eliminates delete-file accumulation entirely).
  **State explicitly:** snapshot expiry is part of the compliance posture — retained
  snapshots expose the deleted rows. Never size expiry to "nice to have" here.
- **High-churn SCD/CDC table (position deletes, merge-on-read):** E2 position-delete
  compaction with `remove-dangling-deletes` → optionally switch to COW if write
  throughput permits. Sort by the merge key if scans are selective on it.
