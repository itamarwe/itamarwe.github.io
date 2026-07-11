# VGGT-Ω post — figures & animation

Code behind the visuals in `content/posts/2026-07-09-vggt-omega.md`.
Outputs are committed under `public/img/vggt-omega/`.

## Layout

- `sim/figures.py` — all static PNGs (social card + 12 figures), matplotlib,
  pure-black `#000` background, house palette. All figures are qualitative
  schematics **except**:
  - `scaling.png`, which plots the point-error values published in the VGGT-Ω
    paper (Fig. 1); the data-curve x-positions are interpolated on the log axis
    between the reported 2K → 2M endpoints (noted in the figure caption and
    the post);
  - `attention-cost.png`, exact arithmetic — interaction counts per attention
    layer at the released implementation's token counts (N = 1041 per frame,
    S = 17 cross-frame register/camera tokens).
- `sim/optimize_vs_predict.py` — the split-screen MP4 (bundle adjustment
  jitter-converging vs one-pass point-cloud snap). A stylized re-enactment, not
  real solver output — stated in its docstring and in the post.
- `assets/building_home_B_red.obj` — the real 3D house model used across the
  figures and the video: `building_home_B_red` from the
  [KayKit Medieval Hexagon Pack](https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0)
  (CC0, no attribution required — credited anyway). `figures.py` samples and
  renders it with a small software pipeline (OBJ parse → rotate/project →
  painter's-algorithm shading, plus a z-buffered point-cloud mode).

## Reproduce

```bash
python3 -m venv venv && venv/bin/pip install numpy matplotlib
venv/bin/python sim/figures.py              # PNGs -> public/img/vggt-omega/
venv/bin/python sim/optimize_vs_predict.py  # MP4 (needs ffmpeg on PATH)
```
