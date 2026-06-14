# Forest Scene — Gaussian Splatting Benchmark

Simulated 3D scene: soldier standing in a forest clearing, surrounded by trees
with animated leaves. Used to benchmark Gaussian Splatting reconstruction
quality under dense vegetation occlusion.

## Files

| File | Purpose |
|---|---|
| `../../../public/forest-scene/index.html` | Three.js interactive scene |
| `capture_views.py` | Headless multi-view capture (Chrome) |
| `benchmark.py` | PSNR/SSIM/occlusion benchmark |
| `sample_images/` | Pre-captured paired samples (veg / no-veg) |

## Quick start

```bash
# 1. Capture all training views (needs Chrome headless)
cd research/gaussian-splatting/scene
python capture_views.py --port 7890 --out sample_images

# 2. Run benchmark on captured images
pip install Pillow scikit-image matplotlib
python benchmark.py --images sample_images --out .
# → benchmark_report.json + benchmark_summary.png
```

## URL parameters (scene)

| Param | Description | Default |
|---|---|---|
| `az` | Camera azimuth (degrees) | 30 |
| `el` | Camera elevation (degrees) | 58 |
| `d`  | Camera distance | 20 |
| `veg` | Vegetation visible (0/1) | 1 |
| `t`  | Wind time | 0 |
| `ui` | Show HUD (0/1) | 1 |
| `interactive` | Enable mouse controls (0/1) | 1 |

## Benchmark metrics

- **occlusion_ratio** — fraction of soldier-ROI pixels significantly altered
  by vegetation (0 = clear view, 1 = fully hidden)
- **psnr / ssim** — full-frame quality vs. ground-truth (no-veg) render
- **soldier_psnr / soldier_ssim** — same metrics restricted to the central
  ROI containing the soldier
- **scene_difficulty** — composite [0,1]; >0.5 is significantly challenging
  for standard 3DGS

## Scene difficulty by elevation tier (example values)

| Tier | Elevation | Expected occlusion |
|---|---|---|
| top-down | ≥78° | 0.6–0.9 |
| high oblique | ≈62° | 0.2–0.5 |
| mid oblique | ≈42° | 0.05–0.25 |
| low side | ≈18° | 0.0–0.15 |

## Connecting to real 3DGS training

To use this scene as a 3DGS benchmark:
1. Run `capture_views.py` to generate N training views (all with `veg=1`)
2. Extract camera poses from the URL params (azimuth, elevation, distance →
   spherical → COLMAP-style extrinsics)
3. Train a 3DGS model on those images + poses
4. Render novel views from the trained model
5. Compare to `*_noveg.png` ground-truth renders using `benchmark.py` metrics
