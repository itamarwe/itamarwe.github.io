# Part II · Chapter 4 — Maintenance optimization

> Ingestion creates entropy; maintenance removes it. Unlike a classic warehouse
> that tidies itself, an open Iceberg table puts this on you (unless a platform
> automates it — see [ch. 5](05-platform-playbooks.md)). The four operations are
> **compaction, snapshot expiration, orphan-file removal, and manifest
> rewriting.** Drive cadence and scope from the
> [Stage 2 metadata analysis](01-methodology-and-analysis.md#stage-2--table-metadata-analysis-the-current-physical-layout).

The mantra: **measure from metadata → act with the right procedure → scope it →
schedule it in read troughs → re-measure.** Maintenance is itself a workload; it
costs compute and can contend with writers, so scope and timing matter.

---

## 4.1 The four operations at a glance

| Operation | Fixes | Spark procedure | Trigger signal (Stage 2) |
|---|---|---|---|
| **Compaction** | small files, poor colocation, MOR delete buildup | `rewrite_data_files` | file p50 small; many `<32 MB`; high delete-file ratio |
| **Snapshot expiration** | metadata bloat, storage cost, time-travel window | `expire_snapshots` | thousands of snapshots; `metadata.json` growth |
| **Orphan-file removal** | unreferenced files from failed/retried writes | `remove_orphan_files` | storage > sum of live files; many writer retries |
| **Manifest rewriting** | manifest fragmentation, slow planning | `rewrite_manifests` | many manifests, few files each; high planning time |

---

## 4.2 Compaction (the highest-impact operation)

**What it does:** rewrites data files to (a) bin-pack small files into target-sized
ones, (b) optionally **sort/Z-order** to restore colocation, and (c) **apply
delete files** into clean base files (removing the MOR read tax). It can also
consolidate manifests in the same pass.

### Strategy

- **`binpack`** (default): just merges to target size. Fast, cheap, fixes the
  small-file problem. Use when layout (sort) is already fine.
- **`sort` / `zorder`**: bin-pack *and* reorder by the table's sort keys
  ([§2.2](02-recommendations-table-properties.md#22-sort-order--clustering)).
  More expensive; use when Stage 1 shows pruning failures from poor colocation, or
  to restore order on streaming tables written unsorted.

```sql
-- bin-pack only, scoped to the hot partition
CALL system.rewrite_data_files(
  table => 'db.events',
  strategy => 'binpack',
  where => 'event_date = current_date',
  options => map('target-file-size-bytes','268435456', 'min-input-files','5'));

-- sort/zorder to restore colocation
CALL system.rewrite_data_files(
  table => 'db.events', strategy => 'sort',
  sort_order => 'zorder(tenant_id, country)');
```

### Key options

| Option | Effect |
|---|---|
| `target-file-size-bytes` | output size (mirror the table property). |
| `min-input-files` | min files in a group before it's worth rewriting (controls granularity/parallelism). |
| `min-file-size-bytes` / `max-file-size-bytes` | which files are eligible (small ones to merge, oversized ones to split). |
| `where` | **scope to a partition/filter** — the key to cheap incremental compaction. |
| `rewrite-job-order` | order file groups (smallest-first to cut file count fast, etc.). |
| `remove-dangling-deletes` | drop delete files no longer matching live data. |
| `max-concurrent-file-group-rewrites` | parallelism / resource ceiling. |

### Scoping & cadence

- **Scope with `where`** to hot/recent partitions rather than full-table rewrites —
  short jobs, bounded cost, no SLA disruption. Drive the filter from Stage 2
  partition-level file counts.
- **Cadence by ingestion pattern:**
  - Streaming / high-churn MOR: **every 1–4 h**, sometimes every few minutes for
    very high-change CDC, to keep delete files in check.
  - Micro-batch: a few times a day or after N commits.
  - Daily batch: **right after each load completes.**
- **Incremental, narrow-threshold jobs run often** beat occasional full rewrites —
  they keep the table converged without long, contention-heavy jobs.
- **MOR health is a sawtooth:** delete-file count should rise (ingest) and fall
  (compaction) repeatedly. **Monotonic growth = compaction isn't keeping up** →
  raise frequency or widen scope. For position-delete buildup specifically, use
  `rewrite_position_delete_files` (v2); v3 deletion vectors largely obviate this.

---

## 4.3 Snapshot expiration

**What it does:** removes old snapshots and the data/metadata files *uniquely*
referenced by them. Iceberg never deletes a file still needed by a retained
snapshot, so it's safe — but it does set the time-travel horizon.

**Drive it from:** Stage 4 time-travel/compliance window (a hard requirement that
*overrides* aggressive expiration) and Stage 2 snapshot count.

```sql
CALL system.expire_snapshots(
  table => 'db.events',
  older_than => TIMESTAMP '2026-06-13 00:00:00',
  retain_last => 50,
  max_concurrent_deletes => 8);
```

**Rules of thumb:**

- **COW tables:** **daily** expiration is usually enough.
- **MOR / high-frequency CDC:** expire **hourly** (or tighter) — frequent commits
  bloat history fast, and lingering delete files keep base files alive.
- **Prefer a time window over a snapshot count** for high-frequency writers: with
  thousands of commits/day, `retain_last => N` may represent only minutes of
  history. Use `older_than` to express the real retention intent
  (e.g. "keep 7 days").
- Combine with `clean_expired_metadata => true` to drop unreferenced partition
  specs/schemas; use `stream_results => true` on large tables to spare driver
  memory.
- **Branches/tags pin snapshots** and block expiration — audit `<table>.refs` and
  set `history.expire.max-ref-age-ms` on stale refs.
- Always pair expiration with **orphan-file removal** (next) to physically reclaim
  storage.

---

## 4.4 Orphan-file removal

**What it does:** deletes files in the table's storage location that no snapshot
references — the residue of failed/aborted/retried writes and concurrent-commit
conflicts. (Distinct from expiration, which removes files that *were* referenced.)

```sql
CALL system.remove_orphan_files(
  table => 'db.events',
  older_than => TIMESTAMP '2026-06-17 00:00:00');   -- ≥3-day safety window
```

**Rules of thumb:**

- **Always use a safety window (≥3 days, default).** Orphan detection compares the
  storage listing to live metadata; an in-flight long write looks like an orphan.
  Too-aggressive cleanup can delete a live write's files. Never run it with a tiny
  `older_than`.
- Run **weekly** for most tables; more often for tables with many writer retries
  (Stage 3) or heavy concurrent writers.
- Run **after** expiration so newly-unreferenced files are also cleaned.

---

## 4.5 Manifest rewriting

**What it does:** consolidates many small manifests (the signature of frequent
small commits) into fewer, larger ones aligned to partition boundaries — cutting
query *planning* time, which is pure overhead paid by every read.

```sql
CALL system.rewrite_manifests('db.events');
```

**Rules of thumb:**

- Trigger from Stage 2: many manifests each tracking few files, or high planning
  latency in query profiles (Stage 1).
- **Weekly** for high-frequency-commit tables; rarely needed for batch tables.
- Often folded into the compaction pass.

---

## 4.6 Regulatory deletion (GDPR / CCPA)

Logical delete ≠ physical erasure. Iceberg defers physical removal until snapshots
expire and files are rewritten/cleaned. To *actually* erase a subject's data, run
the full chain:

1. **`delete`** the rows (logical).
2. **Compact** affected partitions so base files are rewritten without the rows —
   essential for **MOR**, where deletes are only pointers until compaction
   materializes them.
3. **Expire every snapshot** that still references the original files (a snapshot
   anywhere in history keeps them readable).
4. **Remove orphan files** to purge the now-unreferenced data from storage.
5. **Beware branches/tags** pinning old snapshots — audit and expire them
   (`max-ref-age-ms`).

Automate and **log** this chain to demonstrate compliance in an audit; map the
retention window from Stage 4 onto the expiration schedule.

---

## 4.7 The safe order of operations & scheduling

Run as a pipeline, in this order, in a **read-trough window** (from Stage 1
time-of-day):

```
compact ─► expire snapshots ─► remove orphan files ─► rewrite manifests
   │            │                    │                      │
 fixes files  trims history     reclaims storage      speeds planning
```

- Compaction first so expiration/cleanup operate on the consolidated state.
- Expiration before orphan removal so the just-unreferenced files get swept.
- **Automate by health, not blanket schedule at scale:** a daily metadata scan
  (Stage 2 queries) across all tables, computing health metrics, then triggering
  only the operations a given table needs. This scales to hundreds of tables
  without per-table babysitting.
- **Always re-measure** against the Stage 2 baseline (file p50, delete ratio,
  snapshot count, planning time) — close the loop and tune cadence.

→ Continue to [Platform playbooks](05-platform-playbooks.md).
