# STORM research layer

This directory documents the research behind the Iceberg Optimization Playbook,
conducted with the **Stanford STORM method** — *Synthesis of Topic Outlines
through Retrieval and Multi-perspective Question asking* (Stanford OVAL Lab,
NAACL 2024) — in the practical four-phase form, with **source retrieval added at
every phase** (the higher-reliability variant).

The point of STORM: a single research prompt returns the *majority framing* of a
topic. Asking from multiple expert perspectives first, then mapping where they
disagree, surfaces blind spots and separates consensus from genuine debate before
anything is written.

## How it was run here (an agents workflow)

```
        ┌─────────────────────────────────────────────────────────────┐
 Phase 1│  MULTI-PERSPECTIVE SCAN  (5 parallel research agents)         │
        │  Practitioner · Skeptic · Economist · Historian · Academic   │
        │  each: research with web retrieval → claims + 4-5 sources     │
        └───────────────────────────────┬─────────────────────────────┘
                                        ▼
 Phase 2│  CONTRADICTION MAP   where the perspectives disagree, why,    │
        │  and which claims are well-supported / weak / missing         │
                                        ▼
 Phase 3│  SYNTHESIS BRIEFING  findings · tradeoffs · reliability       │
        │  ranking · recommended actions                                │
                                        ▼
 Phase 4│  PEER REVIEW   critique the briefing: strong/weak claims,     │
        │  biases, missing angles, what needs source verification       │
        └─────────────────────────────────────────────────────────────┘
```

- **Phase 1** was executed as a literal **agents workflow**: five independent
  research subagents, one per perspective, run in parallel. Each was instructed to
  do real web retrieval and attach 4–5 credible sources to its claims (per the
  STORM caveat that persona-prompting without retrieval is just structured
  guessing).
- **Phases 2–4** are the orchestrator's synthesis over the five scans.

## Files

| File | Phase | Contents |
|---|---|---|
| [`01-perspectives.md`](01-perspectives.md) | 1 | The five sourced perspective scans, verbatim. |
| [`02-contradiction-map.md`](02-contradiction-map.md) | 2 | Where perspectives disagree; evidence strength. |
| [`03-synthesis-briefing.md`](03-synthesis-briefing.md) | 3 | The research briefing with reliability ranking. |
| [`04-peer-review.md`](04-peer-review.md) | 4 | Self-critique of the briefing. |

## Relationship to the main book

The main [Iceberg Optimization Playbook](../README.md) (the analysis-first
methodology + category/platform recommendations) is the *product*. This STORM
layer is the *research record* behind it: it stress-tests the playbook's claims
from five angles and records where the advice is solid, contested, or
context-dependent. Where the peer review (Phase 4) flagged a material correction,
it was folded back into the main chapters — those edits are noted in
[`04-peer-review.md`](04-peer-review.md).

## Honesty note

Perspective personas are a thinking tool, not authorities. Every substantive claim
is tied to a retrieved source; claims without a source are labelled as reasoning,
not fact. The reliability ranking in the synthesis reflects how well each finding
is actually supported, not how confidently any single perspective stated it.
