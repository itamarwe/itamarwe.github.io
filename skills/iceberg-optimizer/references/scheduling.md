# Scheduling maintenance

Two scheduling models. Pick per table based on the derived write cadence and the
chosen scenario.

1. **Fixed schedule** — cron/Airflow at a fixed cadence. Simple; fine for
   predictable batch tables.
2. **Threshold-triggered** — a cheap monitoring query reads the metadata tables;
   maintenance runs only when a threshold trips. Better for variable or streaming
   workloads; avoids paying for maintenance that isn't needed yet.

Always order operations: **compact → expire snapshots → remove orphans → rewrite
manifests.**

---

## Archetype → schedule matrix

| Table type | Compaction | Expire snapshots | Orphan cleanup | Rewrite manifests |
|---|---|---|---|---|
| Streaming (< 1 h lag) | every 1–4 h, bin-pack, **cold partitions only** | every 1–3 h, retain ~10 | weekly, ≥ 3-day safety | every 4–8 h |
| Hourly batch | after each load | daily, retain ~10 | weekly | daily |
| Daily batch | after each load | daily, retain ~5 | weekly | after load |
| Weekly batch | after each load | weekly, retain ~3 | monthly | weekly |
| Read-only / archive | one-off, then none | monthly/quarterly, retain ~2 | monthly | one-off |
| Write-heavy / mutated | 30–60 min, cold partitions | every 2 h | weekly | every 2–4 h |

Sizing the snapshot `retain`/age to **time-travel need** overrides the defaults
above — if replay/audit requires 30 days, keep 30 days regardless.

**Compaction after batch loads is conditional, not automatic.** Before
scheduling post-load compaction, check `avg_added_file_mb` from the `snapshots`
table. If the writer already produces near-target-size files, compaction adds
cost with no benefit. Only trigger it if small files accumulated or delete
pressure is building.

**CDC / high-frequency streaming tables:** `retain_last = N` is inadequate when
the table commits thousands of times per day — even `retain_last = 100` may
represent only minutes of history. For these tables, use **time-based
expiration** instead:
```sql
-- Prefer time-based window over count-based for CDC tables
ALTER TABLE cat.db.tbl SET TBLPROPERTIES (
  'history.expire.max-snapshot-age-ms' = '7200000'   -- retain last 2 hours
);
-- or via procedure:
CALL cat.system.expire_snapshots(
  table => 'db.tbl',
  older_than => TIMESTAMP '...',  -- now() - 2h
  retain_last => 1                -- safety floor, but time window governs
);
```
The 2-hour window is a starting point; size to your rollback SLA. CDC tables
should also compact MOR delete files every 5–30 minutes to prevent read-time
merge cost from compounding.

---

## Threshold triggers (metadata-driven)

Run a monitor (e.g. hourly) and fire the matching op when a threshold trips:

| Signal (from metadata tables) | Threshold | Action |
|---|---|---|
| `avg_file_mb` (`files`) | < 64 | bin-pack compaction |
| files under 64 MB in a partition (`partitions`) | > 100 | compact that partition |
| delete-file ratio (`files`) | > 10% | delete-file compaction |
| `snapshot_count` (`snapshots`) | > 1000 | expire snapshots |
| `manifest_count` (`manifests`) | > 500 | rewrite/optimize manifests |
| distinct `partition_spec_id` (`manifests`) | > 1 | `rewrite-all` compaction |

A common pattern: commit-count trigger — compact after every N commits
(e.g. default 10) rather than on a clock. Implementation:

```sql
-- Count new commits since last maintenance snapshot
SELECT COUNT(*) AS new_commits
FROM db.tbl.snapshots
WHERE committed_at > (
  SELECT MAX(committed_at) FROM db.tbl.snapshots
  WHERE summary['spark.app.id'] LIKE '%compaction%'  -- or filter by operation='replace'
)
AND operation IN ('append', 'overwrite');
-- If new_commits > N, trigger compaction
```
In practice, track last-compaction timestamp in a metadata table and compare to
current commit count from the `snapshots` table. Many Iceberg clients also
expose a commit-count trigger natively (e.g., Flink's `min-commits-required`
option in the Iceberg sink).

---

## Streaming: compact only cold partitions

Don't fight the writer for the hot partition. Compact partitions no longer
receiving writes:

```sql
CALL cat.system.rewrite_data_files(
  table => 'db.tbl', strategy => 'binpack',
  where => 'event_date < current_date()'
);
```

**Caveat from Phase 2a:** if `late_data = true`, "cold" partitions still receive
late writes — widen the exclusion window (e.g. `< current_date() - 2`) so you
don't conflict with late arrivals, and re-compact partitions that received late
data.

---

## Orchestration notes

- **Airflow / Dagster / cron** drive the jobs. Parameterize the table list and
  thresholds; emit per-table metrics so the schedule can be tuned.
- **dbt has no maintenance hooks** — it writes data but does not compact, expire
  snapshots, remove orphans, or optimize manifests. If the pipeline is
  dbt-based, maintenance must be a *separate* orchestrated job.
- **S3 Tables / managed catalogs** can run compaction (and sort/z-order on S3
  Tables) automatically — prefer the managed path over hand-rolled jobs when
  available, and only schedule the operations the platform doesn't cover.
- Emit the actual run cost back into the simulator's assumptions over time so the
  schedule converges on the user's real numbers rather than defaults.
