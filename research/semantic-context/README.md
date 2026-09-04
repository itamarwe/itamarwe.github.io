# Semantic context that builds itself — figure source

Source behind the post
[*Semantic Context That Builds Itself*](../../content/posts/2026-09-04-semantic-context-that-builds-itself.md):
the three-layer (physical → usage → curation) model for building the context
layer AI agents need over organizational data.

All visuals are labelled schematics, not data plots. The only measured numbers
drawn are the directional-containment ratios of the customers/transfers example
quoted in the post; the join-specification card and the animation use
illustrative values and made-up tables and say so.

## Layout

```
sim/
  figs.py     matplotlib generator for the five PNGs:
              social.png (1200x630 lead / social card, the pedestal),
              history.png, containment.png, evidence.png, loop.png
scenes/
  anim.py     Manim scene `Process`: physical discovery -> usage mining ->
              lineage -> agent discovery + human curation -> the pedestal.
              No LaTeX, Text labels only.
```

## Running it

A venv with `matplotlib manim` (Manim only for the video).

```bash
python research/semantic-context/sim/figs.py
cd research/semantic-context/scenes && manim -qh --format=mp4 anim.py Process
```

Outputs are committed under `public/img/semantic-context/`.
