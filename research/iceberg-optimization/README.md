# The Iceberg Optimization Playbook

A research "book" on optimizing Apache Iceberg tables across engines and platforms.

It is organized the way the work actually happens: **analyze first, then
recommend.** You don't pick a target file size or a clustering key in a vacuum —
you derive it from how the table is *written* and *read*. So Part I is a
methodology for turning four evidence streams (query logs, table metadata,
ingestion logs, user interviews) into a per-table **optimization profile**, and
Part II turns that profile into concrete settings, split three ways — **table
properties**, **ingestion**, **maintenance** — and then mapped onto each platform
(Databricks, Snowflake, bespoke Spark/Trino/PyIceberg, NiFi, Flink, dbt).

## How to use this book

1. Read **Part I** once to internalize the workflow. It is engine-agnostic.
2. For a given table, run the analysis in [`01-methodology-and-analysis.md`](01-methodology-and-analysis.md)
   and fill in an **optimization profile** (the template at the end of that file).
3. Pull the matching recommendations from the three category chapters
   ([table properties](02-recommendations-table-properties.md),
   [ingestion](03-recommendations-ingestion.md),
   [maintenance](04-recommendations-maintenance.md)).
4. Translate them to your platform with the
   [platform playbooks](05-platform-playbooks.md).
5. Use the [decision matrices](06-decision-matrices.md) as the one-page cheat
   sheet once you know the workflow.

## Table of contents

**Part I — Analysis (the workflow)**

- [01 · Methodology & analysis](01-methodology-and-analysis.md) — the four
  evidence streams, what to query, what each signal implies, and the synthesis
  step that produces an optimization profile.

**Part II — Recommendations**

- [02 · Table-properties optimization](02-recommendations-table-properties.md) —
  partitioning, sort/clustering, file size, write distribution, COW vs MOR,
  compression, metadata hygiene knobs.
- [03 · Ingestion optimization](03-recommendations-ingestion.md) — batch vs
  streaming, commit cadence, the small-file problem at the source, upserts/CDC,
  fanout, write-side distribution.
- [04 · Maintenance optimization](04-recommendations-maintenance.md) —
  compaction, snapshot expiration, orphan-file removal, manifest rewriting,
  scheduling and the safe order of operations.

**Part II (continued) — by platform**

- [05 · Platform playbooks](05-platform-playbooks.md) — Databricks, Snowflake,
  bespoke (Spark/Trino/PyIceberg), NiFi, Flink, dbt; each mapped to the three
  categories above, including what the platform automates for you.
- [06 · Decision matrices](06-decision-matrices.md) — workload → settings,
  platform × category cheat sheet, and an anti-pattern catalog.

**Research provenance — the STORM layer**

- [`storm/`](storm/00-method.md) — the research record behind the playbook,
  produced with the **Stanford STORM method** (multi-perspective scan →
  contradiction map → synthesis → peer review) run as a five-agent workflow
  (Practitioner · Skeptic · Economist · Historian · Academic). It stress-tests the
  playbook's claims from five angles; the peer-review corrections are folded back
  into the chapters above. Start at [`storm/00-method.md`](storm/00-method.md).

## Scope & honesty notes

- This is a **methodology framework**, not a report on a specific dataset. Where
  it shows SQL, the queries are real and runnable against Iceberg metadata tables
  or a query-history store; there are **no fabricated result numbers**.
- Numeric recommendations (e.g. "target 128–512 MB files") are the documented
  community/vendor defaults and rules of thumb current as of mid-2026, with
  sources listed in [`SOURCES.md`](SOURCES.md). Treat them as starting points to
  validate against your own profile, not laws.
- Iceberg moves fast. Spec **v3** (row lineage, deletion vectors, the `variant`
  and `geo` types) reached GA/preview across the major platforms in early 2026;
  where a recommendation depends on the format version, this is called out.
