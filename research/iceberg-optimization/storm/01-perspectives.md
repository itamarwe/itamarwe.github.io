# Phase 1 — Multi-perspective scan

Five independent research agents scanned **Apache Iceberg optimization** through
distinct expert lenses, each with web retrieval and sources attached. Their
scans are reproduced verbatim below. The orchestrator's cross-perspective work
(contradictions, synthesis, peer review) follows in the next files.

> **A shared sourcing caveat.** Every agent reported that many authoritative
> sites (apache.org, vendor docs, arXiv/ACM/VLDB PDFs, HN item pages) returned
> **HTTP 403** to the page fetcher in this environment, so a number of specific
> figures come from search-result snippets rather than full-page reads. All URLs
> are real and were surfaced by search; **specific numbers (DBU rates, "99.4%
> pruned", "up to 90%", the $1–2B Tabular price, etc.) should be re-verified
> against the live source before being quoted as hard facts.** This is itself a
> Phase-4 peer-review finding.

---

## Practitioner perspective

### What this perspective notices

**Cross-cutting reality:** Iceberg's table format is excellent, but a freshly-created table is *not* a self-maintaining table. The format gives you snapshots, manifests, and ACID commits; it does *not* give you compaction, snapshot expiry, or orphan cleanup for free unless you're on a managed engine. The single biggest day-2 surprise for newcomers is that "small files" and "metadata bloat" are operational problems you own, not bugs.

**Table-properties:**
- Defaults are not production defaults. `write.distribution-mode` defaults to `none` (no shuffle) — fine for a single big partition, catastrophic for a high-cardinality partitioned table because every Spark task writes one small file per partition it touches. Practitioners flip this to `hash` early.
- `write.target-file-size-bytes` is a *target/ceiling*, not a guarantee. A single Spark task that produces less data than the target still emits a small file; a task with more produces multiple files. The property doesn't fix skew or fan-out.
- Format v2 vs v1, and copy-on-write vs merge-on-read, is the choice that quietly determines your entire maintenance burden. MoR makes writes cheap and reads expensive, and *requires* delete-file compaction to stay healthy.

**Ingestion:**
- The fundamental tension in every streaming sink (Flink, Kafka Connect, Spark Structured Streaming): commit frequency drives correctness/latency, and frequent commits *manufacture* small files. There is no streaming config that avoids this — you pair it with aggressive downstream compaction.
- Checkpoint interval is the real "files per minute" knob in Flink, more than any Iceberg property.
- MERGE-heavy ingestion (CDC, dbt incremental) is where reads silently rot: each merge writes delete files / rewrites, and without compaction your read amplification climbs.

**Maintenance:**
- Order matters and is non-obvious: expire snapshots → remove orphan files → rewrite manifests/data. Running manifest rewrite while old snapshots are retained only optimizes what the current snapshot references — wasted work.
- The scary procedure is `remove_orphan_files`: its 3-day default exists specifically so it doesn't delete files an in-flight write is still committing. Shortening it without understanding your longest job duration is a known way to corrupt a table.
- `rewrite_data_files` is the procedure most likely to OOM, run for hours, or fail with concurrent-write conflicts on a busy table — it's not "fire and forget."

### Key claims (each with a source)

1. **`write.target-file-size-bytes` defaults to 536870912 (512 MB), and it's a target/max, not a minimum** — a single Spark task under that size still produces a small file, and tasks over it split into multiple files. ([Apache Iceberg — Spark Writes](https://iceberg.apache.org/docs/latest/spark-writes/))
2. **`write.distribution-mode` defaults to `none` (no shuffle); switch to `hash` for evenly-partitioned tables to stop per-task-per-partition small-file explosions** — `none` is only appropriate when rows land in few partitions. ([Iceberg docs — distribution mode clarification](https://www.mail-archive.com/commits@iceberg.apache.org/msg10610.html))
3. **Practical target file size is 128 MB–512 MB; below ~128 MB you pay metadata/planning overhead, above ~1 GB you lose pruning effectiveness.** ([Dremio — Compaction in Apache Iceberg](https://www.dremio.com/blog/compaction-in-apache-iceberg-fine-tuning-your-iceberg-tables-data-files/))
4. **`rewrite_data_files` key options/defaults: `min-input-files`=5, `max-concurrent-file-group-rewrites`=5, `partial-progress.enabled`=false.** Partial-progress lets it commit file groups incrementally so a long compaction survives failure/races. ([Apache Iceberg — Spark Procedures](https://iceberg.apache.org/docs/latest/spark-procedures/))
5. **`rewrite_data_files` is the procedure most prone to OOM and concurrent-write conflicts** — cap `max-concurrent-file-group-rewrites`, compact per-partition, enable partial progress. ([apache/iceberg #13674](https://github.com/apache/iceberg/issues/13674), [#9521](https://github.com/apache/iceberg/issues/9521))
6. **`remove_orphan_files` defaults to a 3-day retention as a safety guard against deleting in-flight-write files; shortening it below your longest job can corrupt the table.** ([Apache Iceberg — Maintenance](https://iceberg.apache.org/docs/latest/maintenance/))
7. **Safe maintenance order is expire snapshots → remove orphan files → rewrite manifests.** ([IOMETE — Maintenance Runbook](https://iomete.com/resources/blog/iceberg-maintenance-runbook))
8. **MoR tables require mandatory regular compaction; position deletes are tied to data-file positions and become invalid when the base file is compacted, so they must be rewritten too.** ([OLake — MoR vs CoW](https://olake.io/iceberg/mor-vs-cow/))
9. **Streaming sinks create small files because they commit at every checkpoint** (a 30 s interval = a commit every 30 s); pair with aggressive compaction; `write.distribution-mode=hash` in the Flink sink reduces source-side small files. ([Apache Iceberg — Flink Writes](https://iceberg.apache.org/docs/latest/flink-writes/), [Streaming into Iceberg](https://iceberglakehouse.com/posts/2026-04-29-iceberg-masterclass-13/))
10. **dbt transforms but does not maintain Iceberg tables** — passes properties via `table_properties`, but compaction/expiry/orphan-cleanup run separately; use `incremental_predicates` to bound the MERGE scan. ([LakeOps — dbt Iceberg](https://lakeops.dev/blog/dbt-iceberg-optimization), [dbt — Athena configs](https://docs.getdbt.com/reference/resource-configs/athena-configs))
11. **Managed ingestion automates small files differently per vendor:** Confluent Tableflow auto-compacts and expires; Fivetran consolidates inline and expires snapshots daily on a configurable retention. ([Confluent — Tableflow GA](https://www.confluent.io/blog/tableflow-ga-kafka-snowflake-iceberg/), [Fivetran — Iceberg](https://www.fivetran.com/blog/get-started-with-iceberg-without-the-brain-freeze))
12. **Managed-engine maintenance is opaque and scoped to the managing engine:** Snowflake managed Iceberg auto-runs compaction/manifest-opt/snapshot-expiry (some non-disableable) but only for Snowflake-managed tables; Databricks Predictive Optimization auto-runs OPTIMIZE/VACUUM/ANALYZE on UC-managed tables. ([Snowflake — Managed Iceberg](https://www.snowflake.com/en/blog/engineering/managed-iceberg-tables/), [IOMETE — Maintenance Landscape](https://iomete.com/resources/blog/iceberg-maintenance-alternatives))

### Where this perspective is limited / blind spots
- Over-indexes on small files/compaction (the thing that pages you); under-weights schema/partition *design*, which often matters more.
- Published numbers ("256–512 MB", "min-input-files=5", "compact daily") are starting points, not universal truths — they get cargo-culted.
- Reaches for procedures over root cause (scheduling compaction instead of fixing checkpoint interval / distribution mode).
- Managed-platform behavior is largely unverifiable from outside (when it runs, how aggressive, what it costs).
- Under-weights cost and multi-engine governance; biased toward Spark/Trino tooling where the mature procedures live.

### Sources
- [Apache Iceberg — Maintenance](https://iceberg.apache.org/docs/latest/maintenance/) · [Spark Procedures](https://iceberg.apache.org/docs/latest/spark-procedures/) · [Spark Writes](https://iceberg.apache.org/docs/latest/spark-writes/) · [Flink Writes](https://iceberg.apache.org/docs/latest/flink-writes/)
- [Iceberg commits list — distribution mode defaults](https://www.mail-archive.com/commits@iceberg.apache.org/msg10610.html)
- [apache/iceberg #13674 — rewrite_data_files OOM](https://github.com/apache/iceberg/issues/13674) · [#9521 — concurrent write conflict](https://github.com/apache/iceberg/issues/9521)
- [Dremio — Compaction in Apache Iceberg](https://www.dremio.com/blog/compaction-in-apache-iceberg-fine-tuning-your-iceberg-tables-data-files/)
- [IOMETE — Maintenance Runbook](https://iomete.com/resources/blog/iceberg-maintenance-runbook) · [Maintenance Landscape](https://iomete.com/resources/blog/iceberg-maintenance-alternatives)
- [OLake — MoR vs CoW](https://olake.io/iceberg/mor-vs-cow/) · [Iceberg Lakehouse — Streaming into Iceberg](https://iceberglakehouse.com/posts/2026-04-29-iceberg-masterclass-13/)
- [LakeOps — dbt Iceberg Optimization](https://lakeops.dev/blog/dbt-iceberg-optimization) · [dbt — Athena configs](https://docs.getdbt.com/reference/resource-configs/athena-configs)
- [Confluent — Tableflow GA](https://www.confluent.io/blog/tableflow-ga-kafka-snowflake-iceberg/) · [Fivetran — Iceberg](https://www.fivetran.com/blog/get-started-with-iceberg-without-the-brain-freeze) · [Snowflake — Managed Iceberg Tables](https://www.snowflake.com/en/blog/engineering/managed-iceberg-tables/)

---

## Skeptic perspective

### What this perspective notices

**Table-properties**
- The canonical "target 128–512 MB files" advice is treated as a universal law, but `write.target-file-size-bytes` is **not reliably honored** by writers — people set 512 MB and get ~100 MB files, then cargo-cult the setting without verifying output. The "right" size is workload- and engine-dependent.
- Defaults are quietly contested and keep changing (e.g. default `write.distribution-mode` moving from `none` toward `hash`/`range`), so "best practice" copied from a 2022 blog can be actively wrong now — and `hash`/`range` trades small-file reduction for shuffle cost nobody benchmarks.
- Bloom filters, column metrics, and clustering are sold as free wins but carry write-time and metadata-size costs; "enable everything to be safe" is an anti-pattern.

**Ingestion**
- Iceberg was built at Netflix for petabyte-scale, slow-moving tables. Most shops run gigabytes, where the metadata indirection and mandatory maintenance are pure overhead — "your biggest table fits on a laptop" yet you run Spark OPTIMIZE on it.
- Streaming/CDC is where the format is weakest: frequent commits create small-file/metadata explosions; **MoR with equality deletes pushes unbounded cost onto every reader**; "real-time Iceberg" is gated on the writer finishing a Parquet upload and swapping the pointer.
- Non-JVM clients (PyIceberg, Rust, Go, C++) lag the Java reference and often lack compaction/maintenance, so "engine-agnostic" is aspirational; ClickHouse/DuckDB are read-only or write-experimental.

**Maintenance**
- "Just turn on auto-optimization" hides a serverless meter that bills whether or not anyone queries the table; managed compaction/clustering can cost more than the queries it accelerates.
- Maintenance is **destructive and order-sensitive**: snapshot expiration + orphan-file deletion can corrupt active Flink jobs and cause silent data loss if run wrong.
- The "set it and forget it lakehouse" pitch is false — without continuous compaction, manifest rewrites, and snapshot expiry, tables degrade; maintenance is a permanent tax.

### Key claims (each with a source)
1. **The target-file-size knob is not always respected** — users set 512 MB and still get ~100 MB files. ([apache/iceberg #8729](https://github.com/apache/iceberg/issues/8729))
2. **Optimal file size is contested, not canonical** — 128 vs 256 vs 512 MB all recommended for "most workloads." ([Dremio — Compaction](https://www.dremio.com/blog/compaction-in-apache-iceberg-fine-tuning-your-iceberg-tables-data-files/))
3. **MoR + equality deletes shifts unbounded cost onto readers** and is "almost the only choice" for streaming CDC — a structural, not incidental, problem. ([RisingWave — The Equality Delete Problem](https://risingwave.com/blog/the-equality-delete-problem-in-apache-iceberg/); [HN](https://news.ycombinator.com/item?id=44880081))
4. **"Iceberg is the new Hadoop" — overhyped and mismatched to most orgs' scale**, reintroducing small-file pain and demanding continuous tuning. ([Data Engineering Weekly](https://www.dataengineeringweekly.com/p/is-apache-iceberg-the-new-hadoop); [HN](https://news.ycombinator.com/item?id=43277214))
5. **Petabyte-scale design is friction at gigabyte scale** — extra indirection "worthwhile at petabyte scale but questionable at gigabyte scale." ([Quesma — Practical Limitations 2025](https://quesma.com/blog/apache-iceberg-practical-limitations-2025/))
6. **"Engine-agnostic" is overstated** — non-JVM clients lag and lack maintenance tooling; some engines are read-only. ([Quesma — Practical Limitations 2025](https://quesma.com/blog/apache-iceberg-practical-limitations-2025/))
7. **Managed auto-optimization can cost more than it saves** — Snowflake auto-clustering "racks up credits whether anyone's using the table or not." ([DataEngineer Hub — Snowflake Managed Iceberg](https://dataengineerhub.blog/articles/snowflake-managed-iceberg-tables-complete-guide-2026))
8. **Maintenance is destructive — can cause silent data loss in streaming** — expiring snapshots/removing orphans is coupled to active Flink writers; restoring from an old savepoint after cleanup "might trigger silent data loss." ([apache/iceberg #10892](https://github.com/apache/iceberg/issues/10892); [Conduktor](https://www.conduktor.io/glossary/maintaining-iceberg-tables-compaction-and-cleanup))
9. **Streaming writes structurally conflict with compaction** — high-frequency delete-file commits are "very likely to conflict with any ongoing compaction." ([Iceberg dev list — streaming upserts](https://www.mail-archive.com/dev@iceberg.apache.org/msg12513.html))
10. **Query *planning* itself can be the bottleneck** — on Trino with stats on, 5–10% of queries spent 1–10 min in planning; meta-table queries "too slow for practical use." ([trinodb/trino #26563](https://github.com/trinodb/trino/issues/26563))
11. **Unmaintained tables silently degrade** — metadata can grow larger than the data, requiring a full rewrite to recover. ([IOMETE — Maintenance Runbook](https://iomete.com/resources/blog/iceberg-maintenance-runbook))
12. **Partition evolution complicates compaction** — mixed specs yield inconsistent layouts and degraded pushdown; some engines fail to rewrite across spec conflicts. ([Alex Merced — Hidden Pitfalls](https://dev.to/alexmercedcoder/apache-iceberg-table-optimization-8-hidden-pitfalls-compaction-and-partition-evolution-in-13f1))
13. **Catalog choice is the real lock-in, not the file format** — "creating a table within a specific catalog locks you in… the catalog vendor [has] significant strategic power." ([Confluent/Medium — Table Format War](https://medium.com/confluent/will-apache-iceberg-win-the-table-format-war-01f6ff0d556d))

### Where this perspective is limited / blind spots
- Underweights genuine improvements (hidden partitioning, evolution, snapshot isolation); many cited pains are being actively fixed, so the critique ages fast.
- Over-indexes on small-scale orgs; the cost/benefit flips with scale, concurrency, and number of engines.
- Conflates operational immaturity (missing runbooks) with format defects.
- Survivorship/negativity bias: GitHub/HN over-represent breakage; "skeptic" vendors still sell competing products.
- Treats complexity as disqualifying when, for the right workload, it's essential.

### Sources
- [Data Engineering Weekly — Is Iceberg the New Hadoop?](https://www.dataengineeringweekly.com/p/is-apache-iceberg-the-new-hadoop) · [Quesma — Practical Limitations 2025](https://quesma.com/blog/apache-iceberg-practical-limitations-2025/) · [HN: Practical Limitations](https://news.ycombinator.com/item?id=44063370) · [HN: Hadoop of the modern stack?](https://news.ycombinator.com/item?id=43277214)
- [RisingWave — Equality Delete Problem](https://risingwave.com/blog/the-equality-delete-problem-in-apache-iceberg/) · [HN: equality delete](https://news.ycombinator.com/item?id=44880081) · [apache/iceberg #13000 — MoR indexing](https://github.com/apache/iceberg/issues/13000)
- [apache/iceberg #8729 — target-file-size not respected](https://github.com/apache/iceberg/issues/8729) · [#10892 — Flink savepoint data loss](https://github.com/apache/iceberg/issues/10892) · [#6679 — change default distribution mode](https://github.com/apache/iceberg/issues/6679)
- [trinodb/trino #26563 — slow planning with stats](https://github.com/trinodb/trino/issues/26563) · [Iceberg dev list — streaming upserts](https://www.mail-archive.com/dev@iceberg.apache.org/msg12513.html)
- [IOMETE — Maintenance Runbook](https://iomete.com/resources/blog/iceberg-maintenance-runbook) · [Conduktor — Maintaining Iceberg](https://www.conduktor.io/glossary/maintaining-iceberg-tables-compaction-and-cleanup) · [Alex Merced — Hidden Pitfalls](https://dev.to/alexmercedcoder/apache-iceberg-table-optimization-8-hidden-pitfalls-compaction-and-partition-evolution-in-13f1)
- [Dremio — Compaction](https://www.dremio.com/blog/compaction-in-apache-iceberg-fine-tuning-your-iceberg-tables-data-files/) · [DataEngineer Hub — Snowflake auto-clustering costs](https://dataengineerhub.blog/articles/snowflake-managed-iceberg-tables-complete-guide-2026) · [Confluent/Medium — catalog lock-in](https://medium.com/confluent/will-apache-iceberg-win-the-table-format-war-01f6ff0d556d)

---

## Economist perspective

### What this perspective notices
- **Optimization is spend-shifting, not a free win.** Every maintenance job converts a recurring *read* cost into a recurring *write/compute* cost. The question is never "is the table optimized?" but "does the compute I spend optimizing exceed the read compute I save?" — and the answer flips with query frequency.
- **Hidden cost centers don't show on storage dashboards.** Manifest/metadata bloat and small-file overhead surface on the *compute* bill (S3 GETs, planning time), so teams watching only storage under-manage them.
- **"Managed/auto" optimization is serverless compute with a markup** — billed continuously and opaquely; the vendor decides when to run it.
- **The open-format movement is a competitive maneuver over the storage layer** — commoditize storage (low margin) to compete on engines (high margin).
- **Egress and cross-engine reads are the lock-in that "no lock-in" reintroduces.**
- **Incentives differ by who owns the storage** (Snowflake-managed vs customer-managed vs pure object store).

### Key claims (each with a source)
1. **Compaction/clustering compute can exceed read savings on low-traffic or high-churn tables** — Snowflake auto-clustering "consumes credits continuously… can exceed the query savings." ([Revefi — Snowflake Cost Optimization](https://www.revefi.com/blog/snowflake-cost-optimization))
2. **Cadence is the core cost lever** — compaction/expiration "scheduled strategically to balance compute cost, data freshness, and operational safety." ([Dremio/Alex Merced — Cadence](https://medium.com/data-engineering-with-dremio/apache-iceberg-table-optimization-6-designing-the-ideal-cadence-for-compaction-and-snapshot-7354a94a61d1))
3. **Metadata bloat is a compute cost and the cheapest win** — "manifests… show up on your compute bill." ([overcast — Cost Reduction Strategies](https://overcast.blog/11-apache-iceberg-cost-reduction-strategies-you-should-know-8de7acb14151))
4. **Compaction strategy is a compute-cost decision** — binpack is cheaper CPU/memory; sort/z-order spends compute up front to buy pruning (capex vs opex). ([Amit Gilad — Sort vs Binpack](https://amitgilad.substack.com/p/cracking-the-ice-the-battle-between))
5. **Managed optimization is metered as serverless jobs** — Databricks PO billed under the serverless jobs SKU (`billing_origin_product=PREDICTIVE_OPTIMIZATION`). ([Databricks — serverless billing](https://docs.databricks.com/aws/en/admin/system-tables/serverless-billing))
6. **Serverless DBUs carry a premium over classic compute** (~$0.70–0.95 vs $0.40–0.55/DBU), so managed-serverless vs DIY-classic is a real markup tradeoff. ([Revefi — Databricks Cost Optimization](https://www.revefi.com/blog/databricks-cost-optimization))
7. **Vendors commoditize storage to compete on engines** — open formats let customers swap engines, shifting the battle to where vendors hold pricing power. ([Rill — Why Hyperscalers Bet on Managed Iceberg](https://www.rilldata.com/blog/the-open-table-format-revolution-why-hyperscalers-are-betting-on-managed-iceberg))
8. **The Tabular acquisition prices control of the open standard in the billions** — ~$1–2B for ~40-person Tabular in a bidding war vs Snowflake/Confluent. ([TechCrunch](https://techcrunch.com/2024/08/14/databricks-reportedly-paid-2-billion-in-tabular-acquisition); [TechTarget](https://www.techtarget.com/searchdatamanagement/news/366588032/Databricks-1B-plus-Tabular-acquisition-adds-Iceberg-support))
9. **Cross-engine reads reintroduce egress costs** — "your cloud storage provider bills you for egress when data files move across regions or cloud platforms." ([Snowflake — data transfer cost](https://docs.snowflake.com/en/user-guide/cost-understanding-data-transfer))
10. **Per-request (GET) charges compound on small-file layouts** — links file-sizing properties directly to the bill. ([Akave — egress economics](https://akave.com/blog/snowflake-adopted-iceberg-for-vendor-independence---akave-makes-it-financially-viable))
11. **Snapshot/orphan retention is a quiet storage-cost accrual** that maintenance reclaims. ([overcast — Cost Reduction Strategies](https://overcast.blog/11-apache-iceberg-cost-reduction-strategies-you-should-know-8de7acb14151))
12. **The platform owning compaction captures the savings** — Amazon S3 Tables markets managed compaction cutting costs "by up to 90%," moving the margin to the storage vendor. ([AWS — S3 Tables compaction](https://aws.amazon.com/about-aws/whats-new/2025/07/amazon-s3-tables-reduce-compaction-costs/))

### Where this perspective is limited / blind spots
- Over-weights dollar cost; under-weights correctness, freshness, latency (cost-per-query ≠ value-per-query).
- Assumes read savings are cleanly attributable to a maintenance job; in practice caching and shifting query patterns muddy the counterfactual.
- Cynical about vendor motives in ways that can miss genuine architectural value.
- Pricing is a moving target — cited figures are directional/date-stamped, not constants.
- Ignores people/TCO cost — "DIY is cheaper on the bill" omits engineering/on-call time.

### Sources
- [Revefi — Snowflake Cost Optimization](https://www.revefi.com/blog/snowflake-cost-optimization) · [Databricks Cost Optimization](https://www.revefi.com/blog/databricks-cost-optimization)
- [Dremio/Alex Merced — Cadence](https://medium.com/data-engineering-with-dremio/apache-iceberg-table-optimization-6-designing-the-ideal-cadence-for-compaction-and-snapshot-7354a94a61d1) · [Amit Gilad — Sort vs Binpack](https://amitgilad.substack.com/p/cracking-the-ice-the-battle-between) · [overcast — Cost Reduction](https://overcast.blog/11-apache-iceberg-cost-reduction-strategies-you-should-know-8de7acb14151)
- [Databricks — serverless billing](https://docs.databricks.com/aws/en/admin/system-tables/serverless-billing) · [Rill — Hyperscalers & Managed Iceberg](https://www.rilldata.com/blog/the-open-table-format-revolution-why-hyperscalers-are-betting-on-managed-iceberg)
- [TechCrunch — Tabular $2B](https://techcrunch.com/2024/08/14/databricks-reportedly-paid-2-billion-in-tabular-acquisition) · [TechTarget — Tabular acquisition](https://www.techtarget.com/searchdatamanagement/news/366588032/Databricks-1B-plus-Tabular-acquisition-adds-Iceberg-support)
- [Snowflake — data transfer cost](https://docs.snowflake.com/en/user-guide/cost-understanding-data-transfer) · [Akave — egress economics](https://akave.com/blog/snowflake-adopted-iceberg-for-vendor-independence---akave-makes-it-financially-viable) · [AWS — S3 Tables compaction](https://aws.amazon.com/about-aws/whats-new/2025/07/amazon-s3-tables-reduce-compaction-costs/) · [Flexera — Snowflake Iceberg 2026](https://www.flexera.com/blog/finops/snowflake-iceberg-table/)

---

## Historian perspective

### What this perspective notices
- Iceberg optimization is largely a re-implementation of 1980s–2000s analytical-database engineering on cheap object storage. Compaction, sort/clustering keys, multi-dimensional clustering, target file sizes — each has a named ancestor in MPP warehouses or the Hadoop/Hive era.
- The recurring cycle: physical data layout is the dominant lever for analytical performance, and every generation rediscovers it. Row groups → extents → blocks → micro-partitions → Iceberg data files are the same idea under new names.
- Iceberg's defining innovations are mostly reactions to specific Hive *mistakes*, not green-field invention (hidden partitioning, partition evolution, manifest metadata).
- The table-format wars recapitulate the COW-vs-MOR / read-vs-write-optimized tension C-Store framed in 2005.
- What's genuinely new is narrow: the **metadata layer** (snapshot/manifest tree enabling serializable commits, time travel, engine-agnostic tables over object stores) — not the layout optimizations.
- "Automatic/hidden/self-tuning" is the perennial marketing frontier (DB2 MDC 2003 → Snowflake auto-clustering ~2016 → managed compaction 2024–25).

### Key claims (each with a source)
1. **Compaction is the HDFS/Hadoop "small files problem" merge relocated to object storage.** ([Partition Management in Hadoop](https://adirmashiach.medium.com/partition-management-in-hadoop-9ec2a6b2e9f0); [Airbnb — On Spark, Hive, and Small Files](https://medium.com/airbnb-engineering/on-spark-hive-and-small-files-an-in-depth-look-at-spark-partitioning-strategies-a9a364f908))
2. **`rewrite_data_files` bin-pack is literally a small-files merge to a target size**, the direct descendant of Hadoop compaction. ([Dremio — Compaction](https://www.dremio.com/blog/compaction-in-apache-iceberg-fine-tuning-your-iceberg-tables-data-files/); [11 Compaction Optimizations](https://dev.to/jonisar/11-compaction-optimizations-for-iceberg-data-lakes-52h2))
3. **Hidden partitioning fixes Hive's mistake of making the partition column an explicit physical part of the schema/path.** ([Delta Lake — Pros/cons of Hive-style partitioning](https://delta.io/blog/pros-cons-hive-style-partionining/))
4. **Partition evolution is a band-aid for the same Hive wrong-key problem** — change strategy without rewriting history. ([Delta Lake — Hive-style partitioning](https://delta.io/blog/pros-cons-hive-style-partionining/))
5. **Iceberg was created at Netflix (Blue, Weeks) because Hive couldn't guarantee correctness/atomicity; open-sourced to Apache Nov 2018.** ([SE Daily — Iceberg at Netflix](https://softwareengineeringdaily.com/2024/03/07/iceberg-at-netflix-and-beyond-with-ryan-blue/); [Strata 2018](https://conferences.oreilly.com/strata/strata-ny-2018/public/schedule/detail/69503.html); [Wikipedia](https://en.wikipedia.org/wiki/Apache_Iceberg))
6. **The Hive Metastore's weaknesses are the named precedent the manifest/snapshot tree replaced.** ([lakeFS — Hive Metastore's Dilemma](https://lakefs.io/blog/hive-metastore-it-didnt-age-well/))
7. **Z-order predates Iceberg by decades** — Morton 1966, BIGMIN range-query algorithm Tropf & Herzog 1981. ([Wikipedia — Z-order curve](https://en.wikipedia.org/wiki/Z-order_curve))
8. **Multi-dimensional clustering shipped in IBM DB2 (MDC) at SIGMOD 2003** — block indexes for "partition elimination," conceptually identical to Z-order compaction. ([DB2 MDC, SIGMOD 2003](https://scispace.com/pdf/multi-dimensional-clustering-a-new-data-layout-scheme-in-db2-3o0gapyp0x.pdf); [Z-Order for Delta/Iceberg](https://ajaygupta-spark.medium.com/z-order-optimization-for-generic-multi-dimensional-predicates-cc316a50dcfd))
9. **Iceberg sort-order/clustering is the lakehouse re-invention of Vertica/C-Store projections and Teradata presorting** (C-Store, VLDB 2005). ([C-Store](https://scispace.com/papers/c-store-a-column-oriented-dbms-4q4ob7krcm); [Vertica Projections](https://docs.vertica.com/23.3.x/en/admin/projections/))
10. **Snowflake micro-partitions (50–500 MB immutable units + auto clustering metadata) are the immediate proprietary precedent** for the data-file + manifest min/max model; auto-clustering (~2016) is warehouse-native managed compaction. ([Snowflake — Micro-partitions & Clustering](https://docs.snowflake.com/en/user-guide/tables-clustering-micropartitions); [Automatic Clustering at Snowflake](https://www.snowflake.com/en/blog/engineering/automatic-clustering-at-snowflake/))
11. **COW vs MOR is the read-vs-write-optimized tradeoff from C-Store/LSM, resurfaced via Hudi.** ([DZone — Hudi vs Delta vs Iceberg](https://dzone.com/articles/hudi-vs-delta-vs-iceberg-table-format); [C-Store](https://scispace.com/papers/c-store-a-column-oriented-dbms-4q4ob7krcm))
12. **The format wars ended like prior standard fights — convergence/interop shims** (Delta UniForm, Apache XTable). ([The Register — final chapter?](https://www.theregister.com/software/2024/10/03/are-the-table-format-wars-entering-the-final-chapter/1112902); [End of Format Wars](https://medium.com/@parthiban.jaganathan/end-of-open-table-format-wars-delta-iceberg-and-hudi-towards-uniform-format-98593e7e67b0))

### Where this perspective is limited / blind spots
- Systematically underrates the genuinely novel metadata/commit layer (serializable, serverless-coordinated, engine-agnostic over object stores).
- Flattens context: object-store economics + storage/compute separation + multi-engine ecosystem make an old idea materially different.
- "It's all been done before" breeds false confidence — Z-order at petabyte scale with delete-file reconciliation raises new operational problems.
- Lineage claims risk over-tidiness (convergent invention ≠ direct descent).
- Under-weights the social/governance shift (open standard + multi-vendor catalogs).

### Sources
- [SE Daily — Iceberg at Netflix](https://softwareengineeringdaily.com/2024/03/07/iceberg-at-netflix-and-beyond-with-ryan-blue/) · [Strata 2018](https://conferences.oreilly.com/strata/strata-ny-2018/public/schedule/detail/69503.html) · [Wikipedia — Apache Iceberg](https://en.wikipedia.org/wiki/Apache_Iceberg)
- [Delta Lake — Hive-style partitioning](https://delta.io/blog/pros-cons-hive-style-partionining/) · [lakeFS — Hive Metastore](https://lakefs.io/blog/hive-metastore-it-didnt-age-well/) · [Partition Management in Hadoop](https://adirmashiach.medium.com/partition-management-in-hadoop-9ec2a6b2e9f0) · [Airbnb — Small Files](https://medium.com/airbnb-engineering/on-spark-hive-and-small-files-an-in-depth-look-at-spark-partitioning-strategies-a9a364f908)
- [Dremio — Compaction](https://www.dremio.com/blog/compaction-in-apache-iceberg-fine-tuning-your-iceberg-tables-data-files/) · [11 Compaction Optimizations](https://dev.to/jonisar/11-compaction-optimizations-for-iceberg-data-lakes-52h2)
- [Wikipedia — Z-order curve](https://en.wikipedia.org/wiki/Z-order_curve) · [Z-Order for Delta/Iceberg](https://ajaygupta-spark.medium.com/z-order-optimization-for-generic-multi-dimensional-predicates-cc316a50dcfd) · [DB2 MDC SIGMOD 2003](https://scispace.com/pdf/multi-dimensional-clustering-a-new-data-layout-scheme-in-db2-3o0gapyp0x.pdf) · [C-Store VLDB 2005](https://scispace.com/papers/c-store-a-column-oriented-dbms-4q4ob7krcm) · [Vertica Projections](https://docs.vertica.com/23.3.x/en/admin/projections/)
- [Snowflake — Micro-partitions](https://docs.snowflake.com/en/user-guide/tables-clustering-micropartitions) · [Automatic Clustering at Snowflake](https://www.snowflake.com/en/blog/engineering/automatic-clustering-at-snowflake/) · [DZone — Hudi vs Delta vs Iceberg](https://dzone.com/articles/hudi-vs-delta-vs-iceberg-table-format) · [The Register — format wars](https://www.theregister.com/software/2024/10/03/are-the-table-format-wars-entering-the-final-chapter/1112902) · [End of Format Wars](https://medium.com/@parthiban.jaganathan/end-of-open-table-format-wars-delta-iceberg-and-hudi-towards-uniform-format-98593e7e67b0)

---

## Academic perspective

### What this perspective notices
- The rigorous evidence base is thin and recent, and most of it benchmarks *formats against each other*, not *tuning knobs within a format*. Strongest peer-reviewed work (LST-Bench SIGMOD 2024, CIDR 2023 lakehouse study) compares Delta/Iceberg/Hudi as systems. Little isolates the marginal effect of a single Iceberg setting. Much day-to-day tuning advice rests on vendor blogs and folklore.
- Where the theory *is* solid, it predates Iceberg (min/max zone-map skipping, data-order dependence of pruning, space-filling-curve clustering). Iceberg inherits these results.
- The benefit of compaction is one of the few claims with direct, recent empirical backing (AutoComp SIGMOD 2025; LST-Bench).
- Clustering benefit is real but workload-dependent, and this nuance is empirically supported — locality degrades as you add columns to a Z-order key, contradicting "Z-order everything."
- The spec itself is the most reliable "academic-grade" artifact for the deletes story (v2 position/equality vs v3 deletion vectors).

### Key claims (each with a source)
1. **Small files measurably degrade performance/cost; compaction is the established remedy** — peer-reviewed, drawing on LinkedIn production. ([AutoComp, SIGMOD 2025](https://arxiv.org/abs/2504.04186))
2. **Maintenance must be evaluated *over time*, not one-shot** — LST-Bench adds degradation-rate metrics because LST performance drifts with mutations/small files. ([LST-Bench, SIGMOD 2024](https://dl.acm.org/doi/10.1145/3639314) / [arXiv](https://arxiv.org/abs/2305.01120))
3. **LST-Bench declines to crown a format winner** — the contribution is methodology, itself evidence that "format X is fastest" isn't robust. ([LST-Bench](https://arxiv.org/abs/2305.01120))
4. **Pruning effectiveness is dominated by *data order*, not just having stats** — poor ordering makes zone maps near-useless. ([Columnar Storage Formats, VLDB 2023](https://www.vldb.org/pvldb/vol17/p148-zeng.pdf) / [arXiv](https://arxiv.org/abs/2304.05028))
5. **Min/max pruning can be extremely effective when data is well-clustered** — Snowflake reports up to ~99.4% micro-partitions pruned; real queries more selective than synthetic benchmarks assume. ([Pruning in Snowflake, SIGMOD 2024](https://arxiv.org/abs/2504.11540))
6. **Well-clustered layout also unlocks LIMIT/top-k and join pruning, not only filter pruning.** ([Pruning in Snowflake](https://arxiv.org/abs/2504.11540))
7. **Z-order's advantage over linear sort is multi-dimensional but workload-dependent; locality decays with each added column** — basis for "don't Z-order columns you don't filter on." ([Space-filling Curves, arXiv](https://arxiv.org/pdf/2008.01684))
8. **Hilbert curves preserve locality better than Z-order for 2+ dims** — the reason Databricks Liquid Clustering uses Hilbert. ([Space-filling Curves](https://arxiv.org/pdf/2008.01684); [Hudi — Z-Order & Hilbert](https://hudi.apache.org/blog/2021/12/29/hudi-zorder-and-hilbert-space-filling-curves/))
9. **v3 deletion vectors bound delete-file growth vs v2 position deletes** — ≤1 DV (Roaring bitmap in Puffin) per data file per snapshot, superseding the old; design intent, end-to-end measurements still scarce. ([Iceberg Spec](https://iceberg.apache.org/spec/); [Puffin Spec](https://iceberg.apache.org/puffin-spec/))
10. **COW/MOR is a formal write-amp vs read-amp tradeoff** — MoR read amplification grows ~linearly with accumulated deletes until compaction, which is why MoR *requires* maintenance. ([Iceberg Spec](https://iceberg.apache.org/spec/); [Dremio — COW vs MOR](https://www.dremio.com/blog/row-level-changes-on-the-lakehouse-copy-on-write-vs-merge-on-read-in-apache-iceberg/))
11. **No universal "best" columnar layout** — Parquet vs ORC no clear winner; block compression can hurt end-to-end speed on modern hardware. ([Columnar Storage Formats, VLDB 2023](https://www.vldb.org/pvldb/vol17/p148-zeng.pdf))
12. **Lakehouse metadata design materially affects performance and is a first-class research subject** — differing manifest/metadata layers drive different planning/skipping. ([Lakehouse Storage Systems, CIDR 2023](https://www.cidrdb.org/cidr2023/papers/p92-jain.pdf))

### Where this perspective is limited / blind spots
- Benchmarks rarely match production (Snowflake's own finding: synthetic benchmarks understate selectivity). Numbers like "99.4% pruned" are environment-specific, not portable.
- The literature lags fast-moving tooling — v3 has little independent peer-reviewed evaluation yet.
- Format-vs-format studies under-serve within-format tuning (the actual knobs operators need).
- Engine coupling is often ignored — results entangled with Spark/Trino/Snowflake may not transfer.
- Cost and write-side amplification are under-measured (AutoComp a notable exception).
- Publication/source bias — many quantitative sources are vendor-authored.

### Sources
- [LST-Bench, SIGMOD 2024 (ACM DL)](https://dl.acm.org/doi/10.1145/3639314) / [arXiv 2305.01120](https://arxiv.org/abs/2305.01120) / [MSR blog](https://www.microsoft.com/en-us/research/blog/lst-bench-a-new-benchmark-tool-for-open-table-formats-in-the-data-lake/)
- [AutoComp, SIGMOD 2025 (arXiv 2504.04186)](https://arxiv.org/abs/2504.04186) · [Pruning in Snowflake, SIGMOD 2024 (arXiv 2504.11540)](https://arxiv.org/abs/2504.11540)
- [Columnar Storage Formats, VLDB 2023 (PDF)](https://www.vldb.org/pvldb/vol17/p148-zeng.pdf) / [arXiv 2304.05028](https://arxiv.org/abs/2304.05028) · [Lakehouse Storage Systems, CIDR 2023 (PDF)](https://www.cidrdb.org/cidr2023/papers/p92-jain.pdf)
- [Space-filling Curves (arXiv 2008.01684)](https://arxiv.org/pdf/2008.01684) · [Hudi — Z-Order & Hilbert](https://hudi.apache.org/blog/2021/12/29/hudi-zorder-and-hilbert-space-filling-curves/)
- [Apache Iceberg Spec](https://iceberg.apache.org/spec/) · [Puffin Spec](https://iceberg.apache.org/puffin-spec/) · [Dremio — COW vs MOR](https://www.dremio.com/blog/row-level-changes-on-the-lakehouse-copy-on-write-vs-merge-on-read-in-apache-iceberg/)

→ Continue to [Phase 2 · Contradiction map](02-contradiction-map.md).
