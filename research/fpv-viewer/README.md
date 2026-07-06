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
                                     no numeric axes. The 3-D panel is a REAL
                                     capture (assets/biranit_scene_capture.png).
               annotated_clip.png    REAL flight-annotation timeline of one clip
                                     (2026-06-06 Merkava tank, Blat), from its
                                     segment markers.
               footage_breakdown.png REAL split of annotated footage by segment
                                     type (flight ~51%, pause, replay, banner).
                                     Durations summed from consecutive segment
                                     boundaries; each clip's final open-ended
                                     segment is excluded (no clip-end time in the
                                     manifest).
               scene_pipeline.png    qualitative schematic of the reconstruction
                                     pipeline (raw clip -> extract flight ->
                                     enhance -> select the run -> 3-D scene);
                                     no numeric axes.
               scale_ambiguity.png   qualitative schematic of monocular scale
                                     ambiguity (small near house vs large far
                                     house in the same view cone; a known-size
                                     door anchors the scale); no numeric axes.
               social.png            1200x630 OpenGraph card, composited over a
                                     REAL capture of the viewer's 3-D scene
                                     (assets/biranit_scene_capture.png).
assets/
  biranit_scene_capture.png   Screenshot of the live scene viewer for the Biranit /
                              Iron Dome strike (2026-05-26_anti_drone_platform_barashit),
                              used as the social-card background. Grabbed by the
                              capture pipeline below (out/scene_still.png).
capture/
  capture_segments.mjs  Playwright: record the gallery + scene interfaces from the
                        running dev server (each fully loaded before the action).
  capture_video.mjs     Playwright: record the video interface, scrolling the
                        flight-annotation ribbon into view.
  build_demo.sh         Trim each recording to its action window, burn caption
                        pills, cross-fade -> public/img/fpv-viewer/viewer-demo.mp4
                        (the guided tour embedded in the post).
  capture_social.mjs    Playwright: record the three social-media source takes
                        (gallery scroll/search/filter, video playing, scene
                        playing start->end TWICE — orbit sweeps on the first
                        pass, untouched second pass), each at 16:9 AND a native
                        square viewport. Defaults to the LIVE site (override
                        BASE; ONLY=scene re-records one scenario).
  build_social.sh       capture_social.mjs + trim + encode -> out/social/ with
                        8 videos: {tour,gallery,video,scene} x {linkedin 1080sq,
                        twitter 1280x720}. Tour = the three clips cross-faded
                        with caption pills.
```

The little gallery cards and the pipeline boxes drawn *inside* the schematics
are illustrative stand-ins (not screenshots) — they say "this is what the view
looks like," they don't plot data. The tool_flow 3-D panel, the social card and
the demo video, by contrast, are **real** captures of the running viewer
(Biranit / Iron Dome scene).

## Rebuild the demo video / social capture

Needs the viewer dev server at `http://localhost:5185` (serves scenes &
thumbnails from local disk) — run `npm run dev` in `apps/fpv-viewer/` of the
`fpv-drone-strikes-lebanon-dataset` repo (`fpv-video-quality`). Then:

```
cd capture && ./build_demo.sh
cp out/scene_still.png ../assets/biranit_scene_capture.png   # refresh social bg
```

## Social-media videos

`build_social.sh` produces the 8 share-ready clips under `capture/out/social/`
({tour, gallery, video, scene} × {LinkedIn 1080×1080, Twitter 1280×720}). It
records from the **live site** by default, so it only needs Playwright + ffmpeg
— no dev server:

```
cd capture && ./build_social.sh                 # live site
BASE=http://localhost:5185 ./build_social.sh    # or against the dev server
```

## Regenerate

```
python3 -m venv .venv          # gitignored (research/**/.venv/)
.venv/bin/pip install numpy matplotlib pillow
.venv/bin/python sim/figures.py
```

To refresh the numbers against the current dataset, copy the live manifest over
the snapshot first:

```
cp ../../public/fpv/data/videos.json 2026-07-05_videos_snapshot.json
```
