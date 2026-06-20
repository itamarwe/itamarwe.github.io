# Workload interview: derive first, ask only the gaps

The goal of Phase 2 is a complete picture of **how the table is written** and
**what it is for**. Most of the "how it is written" half is *derivable* from
metadata (Phase 2a) — never ask the user something `$snapshots`/`$files` already
answered. The "what it is for" half is *intent* and must be asked (Phase 2b).

For every item below: **(D)** = derive from metadata, then show the user and ask
them to confirm/correct. **(A)** = ask; metadata cannot know it.

---

## Part 1a — Ingestion pipeline identification (D then confirm)

These questions identify the *writer* so Group 2 actions can be targeted
correctly. Derive from the signal combinations in SKILL.md Phase 2a, then
confirm with the user before prescribing a fix.

| Question | How to derive | Confirm/ask |
|---|---|---|
| **Writer type** (Flink / Spark SS / Spark batch / Kafka Connect / NiFi / Beam+Dataflow / Airbyte / Fivetran / AWS DMS / CDC / unknown) | `write_cadence` + `avg_added_file_mb` + `thin_spread` + `operation_mix` pattern | (D) "This looks like [type] based on [evidence]. Is that right? What connector/framework writes to this table?" |
| **Distribution mode** (`none` / `hash` / `range`) | `thin_spread = true` → likely `none`; else unknown | (A) "Is `write.distribution-mode` set on the sink or as a table property? If yes, which value?" |
| **Checkpoint / trigger interval** (Flink or Spark SS only) | Median inter-commit gap as a proxy | (D) "Commits land ~every Xs. Is that the checkpoint interval? What is it configured to?" |
| **CDC write mode** (`mor` / `cow`) | Equality-delete presence → MOR; absence + overwrites → COW | (D) "We see equality-delete files accumulating → this looks like MOR (merge-on-read). Is the CDC sink configured for MOR or COW?" |
| **CDC connector / framework** (Debezium / DeltaStreamer / AWS DMS / Hudi-bridge / other) | `operation_mix` has high `merge` or `overwrite` | (A) "Which CDC connector or framework generates these writes?" |
| **Backfills / historical loads** | Large `append`/`overwrite` commits with old event-time bounds | (A) "Do you backfill or replay historical data into this table?" |

**Why this matters:** Group 2 (Ingestion) fixes are writer-specific. Flink needs
`write.distribution-mode=hash` and checkpoint interval tuning; Spark SS needs
trigger interval and fan-out settings; CDC pipelines may need MOR→COW switch.
Without knowing the writer, any ingestion recommendation is a guess.

---

## Part 1b — Ingestion semantics (mostly D)

| Dimension | How to derive | What to confirm / ask |
|---|---|---|
| **Write cadence** (real-time / micro-batch / batch / every N sec) | `snapshots` median inter-commit gap | (D) "Commits land ~every Xs → looks like <class>. Correct?" |
| **Buffering to target size vs flushing tiny files** | `summary['added-files-size'] / ['added-data-files']` | (D) "Each commit writes ~X MB files. Is the writer buffering, or is this one flush per micro-batch?" |
| **Partition fan-out per batch** (single partition vs thin spread) | `summary['changed-partition-count']`, files/partition/commit | (D) "Each commit touches ~N partitions. Does a batch target one partition or spread across many?" |
| **Ordered vs out-of-order / late events** | recent files' event-time `lower/upper_bounds` vs `committed_at` | (D/A) "Recent files contain data as old as T → late arrival. Expected? How late can data be?" |
| **Backfills / replays of past events** | large `append`/`overwrite` commits with old event-time bounds | (A) "Do you backfill or replay historical data into this table?" |
| **Mutation type** (append / update / delete) | `snapshots.operation`, delete files in `files` | (D) "We see only appends" / "We see deletes — confirm." |
| **Delete scope & frequency** | `files` WHERE `content IN (1,2)`: count and `record_count`; `snapshots.summary['added-delete-files']` rate over recent window; `eq_delete_pressure` ratio (equality delete records / data records) | (D) "We see N equality-delete / M position-delete files accumulating at ~X/day. Is this GDPR row-level purging, SCD/update-as-delete, or operational corrections?" |

These determine the *shape of the small-file problem* and whether "compact only
cold partitions" is safe (it is not, if late data keeps rewriting old partitions).

---

## Part 2 — Intent & SLAs (all A — the heart of the interview)

Ask these with `AskUserQuestion`. They decide which strategies are even on the
table and which axis Phase 4 optimizes.

1. **Query latency requirement.**
   Interactive (sub-second/seconds, dashboards, user-facing) · Responsive
   (seconds–minutes) · Batch-tolerant (minutes+ is fine).
   → Interactive justifies sort/z-order/bloom; batch-tolerant rarely does.

2. **Query frequency & consumers.**
   Constantly (many queries/hour, many consumers) · Regularly (daily/weekly
   reports) · Rarely (occasional ad-hoc) · Almost never (archival).
   → The amortization denominator. Rare reads can make maintenance compute cost
   *more than it ever saves* — then the right answer is to pay at query time.

3. **Freshness SLA.**
   Must be queryable the instant it lands · Minutes is fine · Hours/once-a-day is
   fine.
   → Tight freshness forbids long compaction windows on hot partitions and
   pushes toward cold-partition-only or write-time tuning.

4. **Cost priority (the optimization objective).**
   Storage \$ · Query \$ (compute scanned) · Query latency · Maintenance \$.
   → This is the `--priority` flag for `simulate.py`. If the user can only pick
   one, this is the one to pin down.

5. **Mutability outlook.**
   Append-only forever · Occasional corrections/updates · Regular updates ·
   Deletes required (e.g. GDPR "right to be forgotten").
   → Drives copy-on-write vs merge-on-read, delete-file compaction urgency, and
   whether equality deletes will accumulate.

6. **Time-travel / replay / audit.**
   Snapshot history is a feature we rely on (replay, audit, rollback) — keep N
   days/versions · Nice to have a little · Only the latest state matters,
   history is just storage cost.
   → Gates how aggressively to expire snapshots. Do **not** expire aggressively
   if replay/audit is a requirement.

7. **Lifecycle & worth.**
   Hot (actively used, optimize for speed/cost) · Warm (used periodically) ·
   Cold archive (rarely touched, optimize for cheap storage) · Possibly not worth
   optimizing at all.
   → Explicitly allow the "do little / nothing" outcome. A small, cold,
   rarely-queried table often warrants only periodic snapshot expiry for storage,
   and no compaction at all.

8. **Retention policy & compliance** (ask only if deletes were observed in 2a).
   - **Data TTL**: is there a rule deleting rows older than N months (e.g. 90-day
     event retention, 7-year regulatory floor)?
   - **GDPR / right-to-be-forgotten**: individual row deletions triggered by user
     requests (typically: `DELETE WHERE user_id = ?`, one at a time, on a
     regulatory clock — 30 days in the EU)?
   - **Regulatory floor**: must *some* data be retained for N years regardless
     (finance, healthcare, audit)?
   - **Snapshot history after deletion**: does old snapshot history expose
     "deleted" rows? (If yes, snapshot expiry is not optional — it is part of the
     compliance posture.)
   → A GDPR table must compact equality deletes and expire snapshots to physically
   remove data, not just logically mark it. This is non-optional regardless of
   query frequency — make it the first item in the plan when `equality_delete_pressure`
   is flagged and the user confirms a compliance motive.

---

## How to run Part 2

Batch related questions. A good first `AskUserQuestion` round covers the four
that most change the recommendation: **latency**, **frequency**, **cost
priority**, and **time-travel need**. Follow up on freshness and mutability only
if the first answers leave them open. Always lead with what you derived: e.g.
"Metadata says ~2 commits/min of ~3 MB files spread across ~40 partitions, i.e.
streaming with heavy thin-spread small files. Before I plan, I need to know what
you're optimizing for and how often it's read."

## Turning answers into gates

The decision framework consumes these as switches:

- `latency ∈ {interactive}` AND `frequency ∈ {constant, regular}` → sort/z-order/bloom eligible.
- `frequency ∈ {rare, almost_never}` AND `lifecycle ∈ {cold}` → bias to **do-nothing / storage-only**.
- `time_travel = relied_on` → cap snapshot expiry at the required retention.
- `mutability ∈ {regular_updates, deletes}` → prioritize delete-file compaction; consider copy-on-write.
- `equality_delete_pressure > 0.05` → delete-file compaction is urgent; if compliance-driven, it is non-optional regardless of query frequency.
- `retention_policy = gdpr` → compact + expire snapshots as a compliance sequence, not a performance optimization. Old snapshots expose logically-deleted rows.
- `retention_policy = ttl` → partition-level deletes (overwrite the old partitions) leave no delete files; prefer this over row-level deletes where the data model allows.
- `freshness = instant` → no long maintenance windows on hot partitions.
- `cost_priority` → the objective `simulate.py` ranks scenarios by.
