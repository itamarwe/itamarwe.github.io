# Phase 4 — Peer review

A self-critique of the [synthesis briefing](03-synthesis-briefing.md) and the
[main playbook](../README.md): strong claims, weak claims, biases, missing angles,
and what still needs source verification — followed by the concrete corrections
that were folded back into the playbook.

## Strong claims (well-supported, keep)

- **Compaction is the highest-impact, evidence-backed optimization.** Backed by
  peer-reviewed work (AutoComp SIGMOD 2025, LST-Bench SIGMOD 2024) *and* every
  practitioner source. Safe to state plainly.
- **Pruning is dominated by data order, not just statistics.** VLDB 2023 columnar
  study + Snowflake SIGMOD 2024. Strong.
- **MoR defers cost to reads and mandates compaction.** Formalized (write-amp vs
  read-amp) and observed across sources.
- **Analysis-first is the right frame.** The five perspectives independently
  converge on "it depends on the workload," which is precisely what the Part I
  profile operationalizes. The method survives multi-perspective scrutiny.

## Weak / over-stated claims (hedged or corrected)

1. **Numeric defaults stated too confidently.** "128–512 MB", "256 MB default",
   "compact every 1–4 h", "expire hourly" are *informed defaults*, not validated
   optima — the Academic confirms no controlled study isolates them, and the
   Skeptic shows the file-size knob isn't even reliably honored. → **Corrected:**
   [§2.3](../02-recommendations-table-properties.md#23-target-file-size) now says
   verify actual output and don't assume the knob worked; the synthesis reliability
   ranking labels these as "validate, don't adopt."
2. **"Z-order for multi-column pruning" presented as a clean win.** Locality decays
   per added column and only helps queried columns; Hilbert is better for 2+ dims.
   → **Corrected:** [§2.2](../02-recommendations-table-properties.md#22-sort-order--clustering)
   now states the decay and the Hilbert/Liquid-Clustering point.
3. **"Compact aggressively" for streaming, stated without the conflict caveat.**
   High-frequency commits can conflict with in-flight compaction. → **Corrected:**
   [§4.2](../04-recommendations-maintenance.md#42-compaction-the-highest-impact-operation)
   adds the conflict + mitigations + the Flink savepoint data-loss warning.
4. **Maintenance implied as unconditionally good.** It's a cost shift that only
   pays off on hot tables. → **Corrected:** a **cost/scale gate ("when *not* to
   optimize")** added to the [maintenance chapter intro](../04-recommendations-maintenance.md)
   and a serverless-cost caveat to the
   [Snowflake managed cell](../05-platform-playbooks.md).

## Likely biases in the research

- **Vendor-source skew.** Many quantitative claims trace to vendors (Snowflake,
  Databricks, AWS, Microsoft, LinkedIn) who benchmark their own systems and choose
  baselines. The Economist and Academic both flagged this.
- **Negativity/survivorship bias in the Skeptic stream.** GitHub issues and HN
  over-represent breakage; they don't quantify how often tables run fine.
- **Recency skew.** The fetch environment blocked many primary pages (403s), so
  some specifics rest on search snippets — a bias toward whatever the search index
  surfaced, not the full text.
- **JVM/Spark-tooling skew.** The mature maintenance procedures live in Spark, so
  the advice leans Spark/Trino; PyIceberg and non-JVM clients are under-covered.

## Missing angles (acknowledged, partly out of scope)

- **Catalog choice & cross-engine egress** — the deepest lock-in/cost is the
  *catalog* and *egress*, not the file format (Skeptic, Economist). Out of the
  three optimization categories, but **flagged** in the synthesis "recommended
  actions" so it isn't silently omitted.
- **Concurrency/multi-writer correctness** beyond the basics — the playbook covers
  optimistic concurrency and commit retries, but distributed multi-engine write
  coordination is deeper than this book goes.
- **v3 deletion vectors' *measured* impact** — design intent is clear; independent
  end-to-end numbers are scarce. The book points to v3 as promising without
  over-claiming, which the Academic supports.
- **Security/governance (FGAC), schema-design-as-optimization** — touched only
  lightly; arguably partition/schema *design* prevents more pain than any
  post-hoc tuning (Practitioner blind-spot note).

## Claims that still need source verification

These are quoted in the perspectives but should **not** be republished as hard
facts without re-checking the primary source (many came from search snippets after
403s):

- Specific cost figures: Amazon S3 Tables "up to 90%", serverless DBU rates
  ($0.70–0.95 vs $0.40–0.55), GET pricing "$0.0004/1k", the "$4,500–7,000/mo"
  example, the **$1–2B Tabular** price, Snowflake "~0.5–2 credits/GB/day."
- Snowflake "**99.4%** micro-partitions pruned" (real paper, snippet-sourced).
- Exact procedure defaults (`min-input-files=5`, `max-concurrent=5`,
  `partial-progress=false`, **512 MB** target, **3-day** orphan window) — these are
  corroborated across multiple sources and match the Apache docs, but worth a
  final docs check before being treated as current.

→ Noted in [`../SOURCES.md`](../SOURCES.md).

### Verification replay (what was re-checked with real reads)

A follow-up pass attempted to re-fetch the flagged sources in full. The session's
environment only reaches an **allowlisted set of domains** — GitHub works; arXiv,
AWS, Snowflake/Databricks docs, VLDB, RisingWave, HN, and `api.firecrawl.dev` all
return HTTP 403 — so only the **GitHub-sourced** claims could be verified by direct
read. All four checked out exactly as cited (#8729 512 MB→~100 MB; #10892 Flink
savepoint silent data loss; #13674 `rewrite_data_files` OOM + partial-progress/
max-concurrent=1 mitigation; trinodb/trino #26563 planning 7 ms→~3 min with stats
on). The vendor **cost/benchmark figures remain snippet-only** and unverifiable
from here; closing that gap requires broadening the session's network policy or
fetching from a less restricted environment. Firecrawl is not an option in this
environment (no tool/key, and its API endpoint is blocked by the same allowlist).

## Confidence / reliability assessment

- **High confidence:** the *method* (analysis-first), and the validated levers
  (compaction, order-aware clustering, MoR-requires-maintenance, maintenance
  order/safety). These survived all five perspectives.
- **Medium confidence:** the specific numeric defaults and cadences — directionally
  right, individually unvalidated; the playbook now frames them as defaults to
  measure against.
- **Low confidence / verify before quoting:** vendor cost figures, managed-platform
  internals, and v3 performance magnitudes.

**Net:** the playbook's *structure and method are robust*; the *numbers are
hypotheses with citations*; and the four corrections above closed the gaps where
the first draft stated contested advice as settled.

← Back to [STORM overview](00-method.md) · [Main playbook](../README.md)
