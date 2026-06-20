# Phase 2 — Contradiction map

Comparing the five perspectives, where do they actually disagree, why, and how
well-supported is each side? This is where the real uncertainty lives — and where
the main playbook had to be careful not to state contested advice as settled.

First, what they **agree** on (consensus is as important as conflict):

- **Small files are a real, costly problem**, and **compaction is the
  highest-impact remedy** — the one optimization with peer-reviewed backing
  (Academic: AutoComp/LST-Bench; Practitioner; Historian: it's the HDFS merge).
- **A bare Iceberg table is not self-maintaining** — without compaction,
  expiration, orphan cleanup, and manifest rewrites it degrades (Practitioner,
  Skeptic, Economist all agree; only the *who pays / is it worth it* differs).
- **MoR shifts cost from write-time to read-time and therefore mandates
  compaction** (Practitioner, Skeptic, Academic — the Academic frames it as a
  formal write-amp/read-amp tradeoff).
- **Physical layout must match query patterns**; statistics alone don't prune if
  data order is wrong (Academic, Practitioner, Historian).
- **Managed auto-optimization only covers tables the platform manages** — foreign
  / external-catalog tables get nothing (Practitioner, Economist).

Now the genuine contradictions:

---

### C1 · Is there a "right" target file size? (128–512 MB)

| Side | Claim | Support |
|---|---|---|
| Practitioner | 128–512 MB is the practical band; 256 MB a sane default. | Vendor/practitioner docs (Dremio). **Medium.** |
| Skeptic | The number is contested (128 vs 256 vs 512 all "recommended"), **and the knob is often not even honored** by writers. | GitHub issue #8729 + conflicting docs. **Medium-high** for "contested"; **high** for "not always honored." |
| Academic | No controlled study isolates the optimal; the *real* driver is data **order**, not file size per se. | VLDB 2023 columnar study. **High** (for the order-dominance point). |

**Resolution:** there is a defensible *default band*, but it is a starting point
to validate, not a law — and you must **verify actual output file sizes**, since
the target isn't guaranteed. The playbook already hedges this ([§2.3](../02-recommendations-table-properties.md#23-target-file-size)); the peer review strengthens the "verify, don't trust the knob" wording.

---

### C2 · Is Iceberg optimization worth the effort, or overhead cargo-cult?

| Side | Claim | Support |
|---|---|---|
| Skeptic | At gigabyte scale Iceberg is "the new Hadoop" — indirection + mandatory maintenance is pure overhead; much tuning is cargo-culted. | Quesma, Data Eng Weekly, HN. **Medium** (opinion-heavy, but well-argued). |
| Practitioner/Economist/Historian | The value (and the maintenance tax) is **real and scales with size, concurrency, and #engines**; at petabyte/multi-engine scale it earns its keep. | Netflix origin, production reports. **Medium-high.** |

**Resolution:** not a true contradiction once you condition on **scale**. The
cost/benefit flips with table size, query frequency, concurrency, and number of
engines. This is a strong argument for the playbook's **analysis-first** stance:
the profile (esp. scale + access frequency) decides whether a given optimization
pays. Folded into peer review as an explicit "when *not* to optimize" note.

---

### C3 · Managed auto-optimization: convenience or runaway meter?

| Side | Claim | Support |
|---|---|---|
| Practitioner | Managed platforms (Snowflake TOS, Databricks PO, Fivetran) remove the maintenance toil. | Vendor docs. **Medium** (vendor-sourced, opaque). |
| Economist/Skeptic | It's **serverless compute billed continuously**, decided by the vendor; on cold or high-churn tables it can **cost more than the reads it accelerates**. | Snowflake/Databricks billing docs, FinOps blogs. **Medium-high.** |

**Resolution:** both true — automation removes toil *and* introduces opaque,
metered spend. The decision is economic, not just technical: enable it on
frequently-queried tables; for cold/rarely-read tables, auto-clustering/compaction
can be net-negative. The playbook mentioned "watch costs"; peer review elevates
this to a first-class **cost gate** in the platform chapter.

---

### C4 · Streaming + compaction: complementary or in conflict?

| Side | Claim | Support |
|---|---|---|
| Practitioner | Stream fast, **pair with aggressive downstream compaction** — standard architecture. | Iceberg docs, masterclass. **Medium-high.** |
| Skeptic | High-frequency streaming commits (esp. delete files) are **"very likely to conflict with any ongoing compaction"** — so "just compact harder" creates commit-conflict churn. | Iceberg dev mailing list. **Medium.** |

**Resolution:** real tension, not a clean win. "Compact aggressively" is right but
**not free of write-side conflict risk**. Mitigations: partition-scoped
compaction on disjoint partitions from the live writer, partial-progress commits,
and raised commit-retry counts. This nuance was **missing** from the playbook's
ingestion/maintenance chapters → added in peer review.

---

### C5 · "Z-order everything" vs workload-specific clustering

| Side | Claim | Support |
|---|---|---|
| Common advice / some practitioners | Z-order multiple columns for multi-dim pruning. | Vendor blogs. **Low-medium.** |
| Academic | Z-order helps **only** queries filtering the clustered columns; **locality decays with each added column**; **Hilbert > Z-order** for 2+ dims. | Space-filling-curve literature; Databricks' Hilbert switch. **High.** |

**Resolution:** Academic wins on evidence. Z-order is not free and not universal —
cluster only on columns that actually filter, and prefer the platform's modern
curve (Databricks Liquid Clustering uses Hilbert). The playbook said "don't sort
columns nobody filters" but didn't mention curve choice/locality decay → added.

---

### C6 · "Open, no lock-in" vs catalog/egress lock-in

| Side | Claim | Support |
|---|---|---|
| Marketing / pro-Iceberg framing | Open format ⇒ no lock-in, pick any engine. | Vendor positioning. **Low** (as an absolute). |
| Skeptic | **Catalog choice** is the real lock-in; the catalog vendor holds strategic power. | Confluent/Medium analysis. **Medium.** |
| Economist | **Cross-engine/cross-region reads reintroduce egress + per-request costs** that the neutrality pitch omits. | Snowflake/AWS cost docs. **Medium-high.** |

**Resolution:** "no lock-in" is overstated. Format openness is real; **catalog and
egress economics are where lock-in/cost re-enters.** Out of scope for the
optimization playbook's three categories, but a material caveat for the synthesis'
"recommended actions" (catalog choice is a strategic decision, not a detail).

---

### C7 · Is any of this genuinely new?

| Side | Claim | Support |
|---|---|---|
| Historian | Layout optimizations are 1980s–2005 DW/Hadoop ideas reborn (Z-order 1966, DB2 MDC 2003, C-Store 2005, Snowflake micro-partitions ~2016). | Primary lineage sources. **High.** |
| Academic/others | The **metadata/commit layer** (serializable, serverless-coordinated, engine-agnostic over object storage) is the real discontinuity. | Iceberg spec, CIDR 2023. **High.** |

**Resolution:** both true and complementary — the *optimizations* are old, the
*substrate* (metadata layer over object stores) is new. Useful framing for the
synthesis: trust the decades-old layout wisdom; treat the metadata layer as the
genuinely novel (and still-maturing, e.g. v3) part.

---

## Open questions no single perspective resolved

- **Quantified within-format tuning.** Nobody has rigorous numbers for "256 vs
  512 MB on workload X" or "compact every 1 h vs 4 h." The Academic confirms this
  gap exists; the playbook's numeric defaults are therefore *informed defaults to
  measure against*, not validated optima.
- **v3 deletion vectors' measured impact.** Design intent is clear (bound delete
  growth, cut read amplification); independent end-to-end measurements are scarce.
- **Real cost attribution of maintenance.** "Does this compaction pay for itself?"
  is unanswered in general — caching and shifting query patterns defeat the
  counterfactual. Argues for measuring per-table, not assuming.

→ Continue to [Phase 3 · Synthesis briefing](03-synthesis-briefing.md).
