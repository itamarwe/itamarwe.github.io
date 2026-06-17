# Workload interview: derive first, ask only the gaps

The goal of Phase 2 is a complete picture of **how the table is written** and
**what it is for**. Most of the "how it is written" half is *derivable* from
metadata (Phase 2a) — never ask the user something `$snapshots`/`$files` already
answered. The "what it is for" half is *intent* and must be asked (Phase 2b).

For every item below: **(D)** = derive from metadata, then show the user and ask
them to confirm/correct. **(A)** = ask; metadata cannot know it.

---

## Part 1 — Ingestion semantics (mostly D)

| Dimension | How to derive | What to confirm / ask |
|---|---|---|
| **Write cadence** (real-time / micro-batch / batch / every N sec) | `snapshots` median inter-commit gap | (D) "Commits land ~every Xs → looks like <class>. Correct?" |
| **Buffering to target size vs flushing tiny files** | `summary['added-files-size'] / ['added-data-files']` | (D) "Each commit writes ~X MB files. Is the writer buffering, or is this one flush per micro-batch?" |
| **Partition fan-out per batch** (single partition vs thin spread) | `summary['changed-partition-count']`, files/partition/commit | (D) "Each commit touches ~N partitions. Does a batch target one partition or spread across many?" |
| **Ordered vs out-of-order / late events** | recent files' event-time `lower/upper_bounds` vs `committed_at` | (D/A) "Recent files contain data as old as T → late arrival. Expected? How late can data be?" |
| **Backfills / replays of past events** | large `append`/`overwrite` commits with old event-time bounds | (A) "Do you backfill or replay historical data into this table?" |
| **Mutation type** (append / update / delete) | `snapshots.operation`, delete files in `files` | (D) "We see only appends" / "We see deletes — confirm." |

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
- `freshness = instant` → no long maintenance windows on hot partitions.
- `cost_priority` → the objective `simulate.py` ranks scenarios by.
