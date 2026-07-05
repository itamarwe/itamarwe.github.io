# FPV *viewer* post — figures

Source behind the post
[*A Browser for the FPV Drone-Strike Dataset*](../../content/posts/2026-07-05-exploring-the-fpv-drone-strike-dataset.md),
which introduces the interactive dataset explorer embedded/served at `/fpv`
(the built app lives in `public/fpv/`, wired up via rewrites in `next.config.ts`).

This directory only regenerates the post's **figures** (in
`public/img/fpv-viewer/`). The viewer app itself is built from a separate repo
(`itamarwe/fpv-drone-strikes-lebanon-dataset`, `apps/fpv-viewer/`) — see PR #78.

## Layout

```
2026-07-05_videos_snapshot.json   Frozen copy of public/fpv/data/videos.json the
                                  figures are computed from (the live one keeps
                                  growing). All counts/durations below are REAL,
                                  derived from this file.
sim/
  figures.py   tool_flow.png         qualitative schematic of the three views
                                     (gallery -> annotated player -> 3-D scene);
                                     no numeric axes.
               annotated_clip.png    REAL flight-annotation timeline of one clip
                                     (2026-06-06 Merkava tank, Blat), from its
                                     segment markers.
               footage_breakdown.png REAL split of annotated footage by segment
                                     type (flight ~51%, pause, replay, banner).
                                     Durations summed from consecutive segment
                                     boundaries; each clip's final open-ended
                                     segment is excluded (no clip-end time in the
                                     manifest).
               social.png            1200x630 OpenGraph card.
```

The little gallery cards and point clouds drawn *inside* the schematics are
illustrative stand-ins (not screenshots) — they say "this is what the view looks
like," they don't plot data.

## Regenerate

```
python3 -m venv .venv          # gitignored (research/**/.venv/)
.venv/bin/pip install numpy matplotlib
.venv/bin/python sim/figures.py
```

To refresh the numbers against the current dataset, copy the live manifest over
the snapshot first:

```
cp ../../public/fpv/data/videos.json 2026-07-05_videos_snapshot.json
```
