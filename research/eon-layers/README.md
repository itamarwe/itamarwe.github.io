# Eon — data-for-AI layers: animation source

Source behind the post
[*How Eon Turns Cloud Backups Into an AI-Queryable Data Lake*](../../content/posts/2026-06-15-how-eon-turns-backups-into-an-ai-data-lake.md).

The post embeds a ~60-second 3blue1brown-style explainer of the four AI layers
Eon builds on top of its backup-derived Iceberg lake:

1. Joinability detection (min-hash physical overlap + LLM semantic check)
2. Semantic analysis by LLM (per-table descriptions, fed the layer-1 evidence)
3. RAG over **tables** (an index of table metadata + the joinability subgraph)
4. NL → SQL (retrieve cluster → confirm → join on real overlaps → time-travel)

## Layout

```
eon_layers_conversation.md   Working log: the source transcript summary, the
                             four-layer breakdown, and the render decisions.
scenes/
  eon_layers_manim.py        Single self-contained Manim CE script.
                             `EONLayers`     — 16:9, Twitter/X/YouTube (1920x1080)
                             `EONLayersTall` — 4:5, LinkedIn feed (1080x1350)
                             No LaTeX; all labels are Text/Unicode.
```

The rendered MP4s committed for the post live in `public/img/eon-layers/`
(`eon_layers_16x9_1920x1080.mp4`, `eon_layers_4x5_1080x1350.mp4`), plus
`social.png` (a 1200×630 frame of the layer-3 beat, used as the OG card).

## Re-rendering

```bash
pip install manim

# 16:9 — Twitter / X / YouTube — 1920x1080
manim -qh scenes/eon_layers_manim.py EONLayers

# 4:5 — LinkedIn feed — 1080x1350
manim --resolution 1080,1350 -qm scenes/eon_layers_manim.py EONLayersTall

# Loopable GIF
manim -qm --format gif scenes/eon_layers_manim.py EONLayers
```

Both scenes fade in and out from black, so they loop cleanly.

## Honesty note

The animation is an *illustrative* depiction of the pipeline — the table names,
Jaccard scores (e.g. `0.94`), and cluster layouts are hand-picked for clarity,
not output from a live Eon system. It's a teaching diagram, not a screen capture.
