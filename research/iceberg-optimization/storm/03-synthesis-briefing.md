# Phase 3 — Synthesis briefing

A research briefing that combines the five perspectives and the contradiction map
into findings, tradeoffs, a reliability ranking, and recommended actions. This is
the bridge between the STORM research and the [main playbook](../README.md).

## Bottom line

Iceberg optimization is **layout + maintenance economics applied to one specific
workload** — the optimizations themselves are decades-old database wisdom
(Historian), only a few are empirically validated (Academic), and whether any of
them pays off is conditional on scale, query frequency, and who runs/pays for the
work (Economist, Skeptic). This is the strongest possible argument for the
playbook's **analysis-first** method: the right settings are *derived per table*,
not adopted from a defaults list. The biggest cross-perspective correction to
conventional how-tos: **stop treating numeric defaults and "just turn on
auto/just compact harder" as universal — condition them on evidence and cost.**

## Main findings

1. **Compaction is the load-bearing optimization** and the only one with rigorous
   support. Small files genuinely hurt; compaction genuinely fixes it; everything
   else is secondary tuning. (All five; Academic = peer-reviewed.)
2. **Layout beats statistics.** Pruning is dominated by *data order*; min/max zone
   maps are near-useless on poorly-ordered data. Sort/cluster on the columns
   queries actually filter — and no more. (Academic, Practitioner.)
3. **MoR is a deferred bill, not a discount.** It trades write cost for read
   amplification that grows until compaction; equality deletes make this acute for
   streaming CDC. Choose MoR for high-mutation workloads *and commit to the
   maintenance*, or choose COW for read-heavy/low-mutation. (All; Skeptic flags
   severity; Academic formalizes it.)
4. **Defaults are starting points, not laws** — and some (target file size) aren't
   even reliably honored by writers. Always verify actual output. (Skeptic,
   Practitioner, Academic.)
5. **Managed optimization is a cost decision, not a free button.** It removes toil
   but bills as continuous serverless compute, scoped only to platform-managed
   tables; on cold/high-churn tables it can be net-negative. (Economist, Skeptic,
   Practitioner.)
6. **The scale question gates everything.** At small scale, much of this is
   overhead; the value rises with size, concurrency, and number of engines reading
   one table. (Skeptic vs the rest — resolved by conditioning on scale.)
7. **"Open / no lock-in" is overstated** — the lock-in and recurring cost move to
   the **catalog** and **cross-engine egress**. (Skeptic, Economist.)
8. **The metadata layer is the genuinely new (and least-proven) part.** Trust the
   old layout wisdom; treat v3 deletion vectors/row lineage as promising but
   not-yet-independently-measured. (Historian + Academic.)

## Key tradeoffs

| Tradeoff | Pole A | Pole B | Decide via |
|---|---|---|---|
| Write vs read cost | COW (clean reads, costly writes) | MoR (cheap writes, read tax) | mutation rate + read sensitivity (profile) |
| Freshness vs file health | frequent commits (small files) | batched commits (lag) | latency SLA (interviews) |
| Optimize-now compute vs read-savings | sort/z-order/cluster, frequent compaction | binpack-only, lazy maintenance | query frequency × table heat (economics) |
| Toil vs control/cost-visibility | managed auto-optimization | DIY procedures | table heat + cost posture |
| Layout specificity vs flexibility | tight partition/sort to current queries | looser layout | query stability + evolution risk |

## Reliability ranking of the advice

**Well-supported (act on it):**
- Compact small files; it's the highest-impact, evidence-backed move.
- Match sort/cluster keys to actual filter columns; order drives pruning.
- MoR requires regular compaction; budget for it.
- Maintenance is destructive and order-sensitive (compact → expire → orphan-remove
  → rewrite manifests); keep the orphan safety window.
- Managed optimization only covers platform-managed tables.

**Directionally right but unquantified (treat as defaults to validate):**
- Specific target file size (128–512 MB / 256 MB) — verify actual output.
- Specific compaction/expiration cadences (1–4 h, daily/hourly) — tune per table.
- `write.distribution-mode=hash` for partitioned batch — benchmark the shuffle cost.

**Contested / context-dependent (decide per case):**
- Whether to optimize at all (scale-gated).
- Whether managed auto-optimization is worth it (cost-gated).
- Z-order multiple columns (workload-gated; prefer Hilbert/Liquid Clustering where available).
- "Compact aggressively" under heavy streaming (commit-conflict risk).

**Vendor-sourced / unverified (quote with care):**
- Specific cost figures ("up to 90%", DBU rates, "99.4% pruned", $1–2B Tabular).
- Managed-platform internals (when/how aggressively auto-jobs run).

## Recommended actions

1. **Keep the analysis-first method** — the perspectives converge on "it depends on
   the workload," which is exactly what the [Part I profile](../01-methodology-and-analysis.md)
   captures. This is validated, not just stylistically nice.
2. **Add a cost/scale gate before recommending any optimization** — a "when *not*
   to optimize" check (cold tables, sub-scale tables, net-negative managed
   clustering). Fold into the maintenance + platform chapters.
3. **Harden the contested claims in the playbook** with explicit caveats:
   target-file-size verification, Z-order locality decay + Hilbert, streaming↔
   compaction commit conflicts. (Done in peer review.)
4. **Label vendor numbers as unverified** in `SOURCES.md` and avoid quoting them as
   fact. (Done.)
5. **Treat catalog choice and egress as strategic** — note in the synthesis that
   the deepest lock-in/cost is not the file format. (Noted; out of the three
   optimization categories' scope but flagged.)
6. **Prefer the few validated levers** (compaction, order-aware clustering) and
   treat everything else as a hypothesis to measure against the Stage-2 baseline.

→ Continue to [Phase 4 · Peer review](04-peer-review.md).
