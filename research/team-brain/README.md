# Team-brain post — image source

Source behind the lead and social images for the post
[*Building a Team Brain That Updates Itself*](../../content/posts/2026-06-09-building-a-self-updating-team-brain.md).

## Layout

```
sim/
  make_images.py   matplotlib generator (dark 3blue1brown style) for:
                     header.png  1200x560  in-page lead banner (no title text)
                     social.png  1200x630  OpenGraph / Twitter card (title baked in)
```

Both render the same motif — a central **team brain** (a small cross-linked wiki
graph living in a Git repo) that every builder keeps current via a pull/push
cron loop, with autonomous agents reading from it. `header.png` lays it out
left→center→right (builders · brain · agents); `social.png` puts the loop motif
behind a title block.

The committed PNGs live in `public/img/team-brain/` alongside the post's other
assets (`graph.png`, `rag-vs-wiki.mp4`, `sync.mp4`).

## Regenerate

```bash
python research/team-brain/sim/make_images.py
```

## Honesty note

Illustrative diagrams — the node labels, counts, and layout are hand-picked for
clarity, not a capture of a live system.
