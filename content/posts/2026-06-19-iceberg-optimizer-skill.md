---
layout: post
title: "An Iceberg Table Optimizer as a Claude Code Skill"
comments: true
date: 2026-06-19
categories: ai, data
image: /img/iceberg-optimizer/social.png
---

Apache Iceberg tables degrade quietly. Small files accumulate as streaming
writers commit every 30 seconds. Delete files pile up against data files until
every scan is doing merge-on-read against hundreds of position deletes. Snapshot
history grows until it buries the metadata layer. None of this produces an error
message — the table just gets slower and more expensive.

The standard answer is a blanket maintenance runbook: compact daily, sort by the
top filter column, expire snapshots weekly. The problem is that this can be the
wrong answer for a specific table, and getting it wrong isn't just wasteful — it
can be actively harmful. Compacting a cold archive that gets three queries a year
costs more than the query savings will ever justify. Running orphan file removal
*before* snapshot expiry can silently skip files that should have been deleted.
Applying an equality-delete compaction to a Format v1 table produces undefined
behavior. Wrong order, wrong action, or wrong timing — any of them can negate
the work or make things worse.

So I built an Iceberg optimizer as a **Claude Code skill** — a structured agent
that reads table metadata, derives what it can, asks only what it can't, simulates
the trade-offs, and produces a ranked, engine-specific maintenance plan.

## What a skill is

Claude Code skills are context files that live alongside your code and are loaded
into the model's context when you invoke them. They can include instructions,
reference documents, decision frameworks, and pointers to scripts — effectively
encoding expert knowledge as structured text that the model reads before responding.

The iceberg-optimizer skill is about 12,000 words of structured knowledge: a main
instruction file (`SKILL.md`), a decision framework that maps table signals to
candidate actions, procedure templates for six different engines, scheduling
patterns, and a workload interview guide. When you invoke it, Claude reads all of
that before touching your table.

## The core principle: observe before you ask

The skill follows one rule: **observe before you ask, ask before you decide,
simulate before you recommend.**

Most tools ask you for configuration upfront. This one reads first. It runs a
profiling script against your table's metadata — file sizes, delete pressure,
snapshot count, partition fan-out, manifest statistics — before asking you a
single question. Then it parses query logs (Spark event logs, Trino query logs)
to derive filter columns, write cadence, and small-file patterns without
requiring any manual input.

Only after all of that does it ask about the things metadata genuinely cannot
reveal: latency requirements, query frequency, cost priorities, time-travel
compliance windows.

The result is that the interview is very short — usually four or five questions —
because most of the relevant signals were already in the metadata.

![Six-phase execution flow — phases 0–1 are fully automatic, phase 2b asks the user only what metadata cannot reveal, phases 3–4 reason and simulate, phase 5 emits the plan](/img/iceberg-optimizer/phase-flow.png)

## Three execution modes

The skill detects which mode it's in before any other work:

- **Direct mode** — a Trino URL, Spark session, or Databricks host is present.
  The skill connects and runs everything without asking.
- **Ask-User mode** — no live connection. The skill guides you through running
  the profiling scripts and exports them as JSON.
- **Exported mode** — you already have the script outputs from a previous run.
  The skill reads those files and proceeds.

This matters for production tables where you might not want to run profiling on a
live cluster mid-day, or where the person doing the analysis isn't the one with
cluster access.

## Thirteen candidate actions

The decision framework defines thirteen candidate actions (A through L, plus Z
for "do nothing"):

| Code | Action |
|------|--------|
| A | Bin-pack compaction — resize small files to target |
| B | Sort compaction — cluster by a leading key |
| C | Z-order compaction — multi-dimensional clustering (2–4 high-cardinality cols max) |
| D | Partition evolution — zero-downtime metadata-only re-partitioning |
| E1 | Equality-delete compaction — physically remove logically deleted rows |
| E2 | Position-delete compaction — merge position deletes into data files |
| F | Snapshot expiry — always include; size to intent |
| G | Manifest rewrite — consolidate manifests after data rewrites |
| H | Orphan file removal — always after F, always dry-run first |
| I | Bloom filters — high-cardinality equality lookups only |
| J | Write-time tuning — fix ingest distribution before compacting its output |
| K | Write-time sort order — free clustering for future writes; no rewrite cost |
| L | Format-version upgrade — one-time prerequisite for v2 row-level delete features |
| Z | Do nothing — explicit outcome for cold or rarely-queried tables |

The framework evaluates each action against the table's signals and produces a
ranked list. Actions have gates (prerequisites that must be true) and triggers
(signals that make the action relevant). A few non-obvious rules:

**J ranks above everything else.** If the root cause is bad write-time behavior
(tiny files from streaming writers with no distribution mode set), fixing that
first is more important than any amount of compaction. Compacting the output of
a broken writer is a treadmill — you'll be back next week.

**Z is a first-class outcome.** A cold archive with 3 queries a year and no
delete pressure genuinely warrants no maintenance. The simulator makes this
explicit by showing that maintenance cost exceeds lifetime query savings.

**L is a blocking prerequisite, not an optional step.** A Format v1 Iceberg
table cannot safely process equality delete files. If a v1 table is accumulating
equality deletes from a CDC pipeline, the first action is the format upgrade —
before any compaction.

**E1 ≠ E2.** Equality deletes and position deletes are different file types
requiring different compaction procedures (`rewrite_data_files` with
`delete-file-threshold` vs `rewrite_position_delete_files`). The action
discrimination matters.

## The simulator

One of the more useful components is the cost simulator. Before producing any
recommendation, the skill runs `simulate.py` against the table's profile —
modeling four maintenance strategies across four cost axes:

- **Do-nothing** — baseline
- **Light** — snapshot expiry only
- **Targeted** — sort or bin-pack on the hot partitions, plus expiry
- **Aggressive** — full data rewrite with sort or z-order

For each strategy, it estimates query performance improvement, query cost change,
maintenance cost, and storage change. This lets the user optimize for whichever
axis they care about — a cost-sensitive team picks the strategy that minimizes
query costs per dollar of maintenance; a latency-sensitive team picks the one
that maximizes query performance.

![Table signal to recommended action — illustrative subset of the 22 benchmark scenarios. Cyan = primary action, gold = secondary action](/img/iceberg-optimizer/action-map.png)

## Benchmarking it

I benchmarked the skill against 22 scenarios covering the full breadth of
production Iceberg anti-patterns. Each scenario has a pre-computed fixture
(profile.json, workload.json, simulator output) and scripted interview answers,
and is evaluated by an LLM judge that scores 1–5 against a written expected
outcome.

Some scenarios test straightforward knowledge — the right answer is in the table
metadata and is unambiguous. Others are designed to be genuinely tricky:

**Format version mismatch.** A v1 table with accumulating equality deletes from
a CDC pipeline. The naive response is to compact the delete files. The correct
response is to upgrade to Format v2 first, then compact. Running E1 on a v1 table
is unsafe.

**Flink micro-commit scatter with equality-only filters.** A Flink streaming table
writing 0.5 MB files every 30 seconds, scattered across 50 partitions per commit.
The filter columns are `event_type` and `region` — both equality predicates, low
cardinality. The naive response is to throw z-order at it (because the table has
multiple filter columns and is hard to read). But z-order only helps when filter
columns include *range* predicates that need multi-dimensional locality. For
equality-only columns, sorting on the leading column is enough and cheaper. The
correct first action is fixing the distribution mode (`write.distribution-mode=hash`)
so future writes land in the right partitions, then a write-time sort order.

**Late-arriving data.** A batch ETL table with a write-time sort order already
configured on `(event_date, customer_id)`. About 5% of events arrive 7–30 days
late, which disrupts the sort order in old partitions when they're re-opened.
The naive response is to recommend re-establishing the sort key. But `has_sort_order`
is already `true` in the profile — the write-time sort order is fine. The remedy
is sort compaction targeted at recently-modified partitions, not touching the sort
key configuration.

**Streaming death spiral.** An emergency scenario: 180,000 files at 1.2 MB average,
with 500 MB/min ingest and nightly compaction already taking 8 hours on a 2 TB table.
Compaction cannot keep up. The instinct is to add more compaction resources. The
correct response is to fix the write-time behavior first — setting `distribution-mode`
and `target-file-size-bytes` so that future writes produce correctly-sized files.
Without that, any amount of compaction is a treadmill.

The benchmark also catches ordering bugs: orphan file removal before snapshot expiry
(orphans get skipped that should have been cleaned), GDPR compaction after instead
of before snapshot expiry (deleted rows may remain physically present in files that
were expired before compaction removed them).

![22-scenario benchmark results — all scenarios score 5/5 on LLM-as-judge evaluation](/img/iceberg-optimizer/benchmark-results.png)

Final scores: **22/22 PASS, average 5.0/5.** Two scenarios initially scored below
5 (flink scatter at 3/5, late-arriving data at 4/5) and were fixed by improving
the decision framework — adding a z-order predicate-type rule and an explicit
K prerequisite check — rather than patching the scenarios themselves.

## Using it

The skill lives in its own repository at
[github.com/itamarwe/iceberg-optimizer](https://github.com/itamarwe/iceberg-optimizer).
To install it in a project:

```bash
npx skills add github:itamarwe/iceberg-optimizer
```

Then in any Claude Code session where your project is open:

```
/iceberg-optimizer optimize my table prod.analytics.events
```

Or just describe the problem: *"the events table is getting slow, help me tune it"* —
the skill is triggered by keywords like optimize, compact, tune, shrink, or maintenance
schedule.

If you don't have a live Spark/Trino connection, the skill will guide you through
exporting the profile manually and will work from the exported files.

The benchmark harness is included in the repository if you want to evaluate the
skill on your own scenarios or extend it for your stack.
