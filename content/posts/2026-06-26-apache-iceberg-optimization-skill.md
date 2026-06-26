---
layout: post
title: "Codifying a Year of Apache Iceberg Pain into a Claude Code Skill"
comments: true
date: 2026-06-26
categories: data, ai
image: /img/iceberg-optimizer/social.png
---

![Claude Code and Apache Iceberg icons — the iceberg optimization skill codifies deployment patterns from large-scale real-world usage.](/img/iceberg-optimizer/social.png)

I spent the last year working closely with one of the most data-intensive organizations in Israel, deploying Apache Iceberg at scale. Petabytes of data, multiple ingestion pipelines, constant schema evolution, several query engines reading the same tables. Exactly the kind of environment that stress-tests every assumption you had about the format.

Most of the problems weren't about scale. They were about **not knowing what Iceberg is actually doing under the hood**.

## The pattern that kept repeating

Here's how it goes. A team discovers Iceberg, reads the getting-started docs, wires up the connector, and ships it. Everything looks fine — data is landing, queries are returning results. Six months later, a query that used to finish in seconds is taking minutes. The metadata layer is bloated. Compaction jobs run for hours without finishing. A partition strategy that made sense at ingestion time is now the read-time bottleneck.

The root cause is almost always the same: **Iceberg has a lot of knobs, and the defaults were chosen for correctness, not for your workload**. Partition specs, sort orders, file size targets, snapshot retention policies, manifest sizing, V1 vs V2 table format — most teams never touch any of them. They accept the defaults, the problems accumulate invisibly, and the first sign anything is wrong is a data engineer firefighting at 2am.

What makes it worse is that the wrong choices interact. A poor partition strategy amplifies the cost of unoptimized file sizes. Unbounded snapshot accumulation slows partition pruning. Too many small files and the wrong delete mode turn a trivially fast CDC table into a read-time disaster. The problems compound before they're visible.

## What I kept doing over and over

Every engagement, the analysis followed the same shape. Look at the partition spec — does it actually match the query patterns, or did someone copy it from a tutorial? Check the file size distribution. Query the `files` metadata table to see the split between data files and delete files. Check the manifest count. Ask whether equality or positional deletes are accumulating. Review the compaction policy. Ask what write pattern is driving this table and whether the layout was designed for it.

This is specialized knowledge. It took time to build, and it isn't well-documented in one place. The official docs tell you *what* each option does. They rarely tell you *when* to use it, or what the footgun looks like when you don't.

## The skill

I codified everything I kept doing into a **[Claude Code skill](https://github.com/itamarwe/iceberg-optimizer-skill)** — a reusable, promptable assistant that knows the bits and bytes of Iceberg and guides you through the decisions that actually matter for your workload.

The design philosophy is deliberate: *observe before you ask, ask before you decide, simulate before you recommend*. Rather than firing off generic best-practice advice, the skill runs through a structured five-phase flow:

1. **Profile** — extract the physical state from your metadata tables: file-size health, snapshot bloat, delete-file pressure, manifest count.
2. **Reconstruct** — derive your ingestion patterns and access profile from the metadata, then fill in whatever's missing with targeted questions about your write cadence, latency requirements, and cost priorities.
3. **Decide** — apply a decision framework that combines the profile and workload data to rank actions across table layout, ingestion tuning, and maintenance scheduling.
4. **Simulate** — model candidate scenarios across latency, query cost, maintenance cost, and storage — so you can pick the tradeoff that actually fits your priorities, not just the one that sounds right in a doc.
5. **Plan** — generate engine-specific commands with exact parameters, implementation schedules, and monitoring thresholds.

The output isn't "consider tuning your file sizes." It's which target file size fits this write volume, whether you should be using V2 merge-on-read or copy-on-write for your CDC pattern, and at what commit frequency to run compaction — with the actual SQL or Spark calls to make it happen.

The skill works with **Spark, Trino, AWS Glue/EMR, Snowflake, and Flink/Kafka Connect**, and it operates on exported metadata tables and query logs — it never connects directly to your warehouse.

## This is v0.1

I want to be direct about what this version is and isn't. It covers the most common failure modes I've encountered: partition strategy, compaction, file layout, snapshot management, and schema evolution edge cases. The five platforms listed above are supported with engine-specific syntax. The benchmark suite runs 22 scenarios and passes cleanly.

There's still a lot of room to grow: more ingestion edge cases, deeper multi-engine write coordination, large-scale migration scenarios, Z-ordering tradeoffs at higher cardinalities, and more efficient token usage as the prompts mature. **This is a starting point**, not a complete reference.

As it gets used on more real deployments, the patterns will sharpen and the coverage will expand.

## A call to the community

If you've been in the trenches with Iceberg — if you've hit the manifest bloat, the equality delete performance cliff, the partition evolution footguns — your hard-won knowledge is exactly what makes something like this useful. The difference between a generic best-practices checklist and a tool you actually trust is lived experience encoded into it.

**We're inviting the Iceberg community to collaborate.** Head to [github.com/itamarwe/iceberg-optimizer-skill](https://github.com/itamarwe/iceberg-optimizer-skill) and open a PR with a pattern you've hit, a recommendation you'd add, or a scenario where the current guidance gets it wrong. The more real-world knowledge goes in, the more useful it gets for everyone who comes after.

The format is designed to be extended — new platforms, new ingestion patterns, new maintenance scenarios slot in cleanly. If your team has specific experience with a particular engine or cloud provider, that expertise belongs in here.

## Why this matters more than it might seem

Most "AI for data" projects I see hit a wall that has nothing to do with the AI. The model is fine. The queries are reasonable. But the underlying tables are so poorly maintained that the data they're reading is stale, slow, or subtly wrong.

Iceberg is foundational infrastructure. How you design and maintain those tables shapes everything that reads from them — dashboards, analytics, AI agents. Getting it right isn't glamorous, but getting it wrong silently poisons everything above it.

That's the thing most teams learn too late. I'd rather they learn it earlier, from a tool, than the hard way at 2am.
