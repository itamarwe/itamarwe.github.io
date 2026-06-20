---
layout: post
title: "I Codified Two Years of Iceberg Optimization Experience Into a Claude Skill"
comments: true
date: 2026-06-20
categories: ai, data
image: /img/iceberg-optimizer/social2.png
---

![Apache Iceberg Optimizer — two years of optimization patterns, encoded as a Claude Code skill](/img/iceberg-optimizer/social2.png)

Over the last two years I've spent a lot of time helping data-heavy organizations adopt and optimize Apache Iceberg — at companies running petabytes of event data on Flink, at teams migrating from Hive with hundreds of CDC pipelines, at organizations where the data engineers are firefighting instead of building because their tables just keep getting slower.

After a while you start to see the same patterns. A Flink job writing 0.5 MB files every 30 seconds because no one set `write.distribution-mode=hash`. A CDC pipeline accumulating thousands of equality-delete files because the team didn't realize that MOR mode requires regular compaction to be readable. A table that's been compacted aggressively for two years but gets three queries a month — the maintenance bill exceeds the query savings by a factor of ten.

The patterns aren't hard. But getting them right requires asking the right questions in the right order, and the "right questions" depend heavily on what the table actually is and who uses it.

So I built an [Apache Iceberg Optimizer](https://github.com/itamarwe/iceberg-optimizer-skill/) as a Claude Code skill. It automates the diagnosis and produces a ranked, engine-specific maintenance plan — one that accounts for what the table is for, not just what it looks like.

## The problem with generic runbooks

The standard advice for Iceberg maintenance goes something like: compact daily, sort by your top filter column, expire snapshots weekly. That advice is wrong for most tables.

A cold data archive that gets queried three times a year doesn't need daily compaction. It needs periodic snapshot expiry and nothing else. Running bin-pack compaction on a cold table costs more compute than you'll ever save in query performance.

A streaming table ingesting 500 MB/min needs the writer fixed before you touch compaction. You can compact as aggressively as you want, but if the Flink job writes 500 files per checkpoint because the distribution mode is wrong, you'll be back compacting next week. The treadmill never ends.

A GDPR compliance table needs a specific sequence: rewrite the data files, *then* expire the snapshots. Do it the other way and the deleted rows remain physically present in snapshot history. That's not optional, and the right order is not obvious.

The right answer depends on four things the table metadata doesn't tell you: how often it's queried, who's querying it, what they're willing to pay, and what they need to preserve. That's the interview.

## What the skill does

It follows one rule: **observe before you ask, ask before you decide, simulate before you recommend.**

It starts by reading the table's metadata — file sizes, delete-file accumulation rates, snapshot count, partition fan-out, manifest statistics. Then it parses the query logs (Spark event logs, Trino query logs) to derive which columns appear in filter predicates, what the write cadence looks like, and whether the writer is producing small files. Most of what you'd normally ask a data engineer can be derived from the metadata without asking anyone anything.

Only after that does it ask about intent: latency requirements, query frequency, cost priorities, time-travel windows. This part is short — usually four or five questions — because the metadata answered everything else already.

![How the skill moves from raw table state to a maintenance plan — the first two steps are fully automated, the interview is short, and the plan is engine-specific](/img/iceberg-optimizer/how-it-works.png)

Then it simulates the alternatives. Before recommending a strategy, it models the cost and performance trade-offs across several scenarios — do nothing, snapshot expiry only, targeted sort compaction, aggressive full rewrite — against the table's actual numbers. The user sees which scenario wins on their chosen axis (query cost, latency, storage, maintenance cost) and can adjust the inputs if the model's assumptions don't match reality.

## Not all tables are the same

Different table archetypes need fundamentally different treatment.

![The four main table archetypes and their dominant optimization strategy — each quadrant has different levers](/img/iceberg-optimizer/archetypes.png)

A **streaming event table** (Flink or Spark Structured Streaming writing continuously) almost always has a write-time problem first. The file size and distribution mode on the writer need to be fixed before compaction makes sense. Once the writer is healthy, sort compaction or z-order on the dominant filter columns is usually the right layout strategy.

A **high-frequency analytical table** (queried constantly, written in batches) benefits most from sort compaction on the top filter column and bloom filters on high-cardinality equality lookup columns. These tables amortize the maintenance cost over many queries.

A **cold archive** (historical data, queried rarely) often warrants doing almost nothing. Periodic snapshot expiry to keep metadata clean, nothing more. Running compaction on a cold table is waste — you pay the compute cost and recover almost nothing in query performance because the queries are rare.

A **CDC or compliance table** (equality deletes accumulating from an upstream write stream) has the tightest constraints. If the table is Format v1, the first action is always the format upgrade. Then it depends on the update rate and query pattern — whether to switch to copy-on-write mode (eliminates future delete accumulation at higher write cost) or stay merge-on-read with regular compaction (lower write cost, ongoing maintenance requirement).

## Three groups of actions

The skill organizes everything into three groups, and a complete plan typically draws from more than one.

**Group 1 — Table Layout:** compaction strategy (bin-pack, sort, z-order), partition evolution, delete-file compaction, format version upgrade. These run on the data that's already on disk.

**Group 2 — Ingestion:** write-time distribution mode, file-size buffering, write-time sort order, CDC write-mode switch (merge-on-read → copy-on-write). These fix the writer so the problem doesn't recur. Group 2 always runs before Group 1 — there's no point optimizing the output of a broken writer.

**Group 3 — Maintenance:** snapshot expiry, manifest rewrite, orphan file removal, bloom filters, scheduling. These are ongoing and run in a specific order (compact → expire → orphan cleanup — never orphan cleanup before expire).

## How to use it

The skill is at [github.com/itamarwe/iceberg-optimizer-skill](https://github.com/itamarwe/iceberg-optimizer-skill/). Install it with:

```bash
npx skills add github:itamarwe/iceberg-optimizer-skill
```

Then invoke it in any Claude Code session:

```
/iceberg-optimizer optimize prod.analytics.events
```

Or just describe the problem: *"the events table is getting slow, help me tune it."* The skill is triggered by keywords like optimize, compact, tune, shrink, maintenance schedule.

It supports Spark, Trino, AWS Glue/EMR, Snowflake, Flink, Kafka Connect, Apache Beam/Dataflow, NiFi, and managed connectors like Airbyte and AWS DMS. If it can connect to your catalog directly it runs the diagnostics itself; if not, it guides you through the queries and works from the output you paste back.

The skill loads context progressively — it only pulls in engine-specific procedure files when it knows which engine you're using. A Trino-only session never touches the Snowflake or Flink documentation.

If you've been fighting Iceberg table health and want something that actually reasons about your specific table instead of handing you a generic runbook, give it a try.
