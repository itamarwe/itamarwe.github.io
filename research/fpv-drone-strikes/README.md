# FPV-drone-strikes post — data, figures & the real VGGT reconstruction

Source behind the post
[*An Open Dataset of FPV Drone Strikes — and a 3-D Flight Path From One Clip*](../../content/posts/2026-06-21-fpv-drone-strikes-open-dataset.md).
Everything here regenerates the figures and the path-extraction video, which live
in `public/img/fpv-drone-strikes/`.

The dataset itself (the 95 strike videos + manifest) lives in a separate repo:
<https://github.com/itamarwe/fpv-drone-strikes-lebanon-dataset>.

## Layout

```
2026-06-21_manifest_snapshot.tsv   Frozen copy of the dataset manifest the
                                   figures are computed from (the live one keeps
                                   growing).
clips/                             (gitignored, large) the source strike MP4 and
                                   the trimmed FPV-only segment.
sim/
  figures.py     Dataset-overview figures: target_mix.png (REAL counts from the
                 manifest), timeline.png (REAL dates), pipeline.png (qualitative
                 schematic, no numeric axes), and the 1200x630 social.png card.
  render_path.py Renders the REAL VGGT output: reconstruction_hero.png and the
                 synced side-by-side path_extraction.mp4.
vggt/
  run_vggt.py      Uploads the FPV-only segment to the public facebook/vggt-omega
                   HF Space (ZeroGPU) and downloads the predicted .glb
                   (point cloud + per-frame camera frustums).
  extract_path.py  Parses the .glb -> camera_path.npy (the flight path) and
                   point_cloud.npz (scene).
  vggt_scene.glb   (gitignored, 16 MB) the raw model output.
  frames/          (gitignored) the 38 sampled FPV frames, one per recovered pose.
```

## Reproduce

```bash
python -m venv vggt/venv && source vggt/venv/bin/activate
pip install gradio_client trimesh numpy matplotlib

# 1. trim the FPV-only segment (drop title cards / outro logo): seconds 8–46
ffmpeg -ss 8 -to 46 -i clips/2026-06-06_sholef_howitzer_adaissah.mp4 \
       -an -c:v libx264 -pix_fmt yuv420p -crf 18 clips/fpv_segment.mp4

# 2. run the real model + parse it
python vggt/run_vggt.py          # -> vggt/vggt_scene.glb
python vggt/extract_path.py      # -> camera_path.npy, point_cloud.npz
ffmpeg -i clips/fpv_segment.mp4 -vf fps=1 vggt/frames/f_%03d.jpg

# 3. figures + video
python sim/render_path.py still   # reconstruction_hero.png
python sim/render_path.py anim    # path_extraction.mp4
python sim/figures.py             # target_mix / timeline / pipeline / social
```

## Honesty notes

- **The reconstruction is real model output**, not an illustration. VGGT recovers
  geometry up to an unknown global scale + rotation, so the trajectory *shape* is
  real but absolute meters are not pinned down.
- VGGT mis-estimated **2 of 38 poses** (motion-blurred frames); `render_path.py`
  flags them as outliers (red crosses) and interpolates the drawn line across them.
- `target_mix.png` buckets are a coarse hand-grouping of the manifest's free-text
  slugs (see `categorize()` in `figures.py`); the **counts are exact**.
