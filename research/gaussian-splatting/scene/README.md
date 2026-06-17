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

## Running real 3DGS on Apple Silicon (OpenSplat)

Stock nerfstudio/`gsplat` is CUDA-only (its kernels need `nvcc`), so `ns-train
splatfacto` will not run on an M-series Mac. [OpenSplat](https://github.com/pierotofy/OpenSplat)
is a C++/libtorch 3DGS trainer that has a Metal/MPS backend (and a CPU fallback).

`make_opensplat_project.py` converts a `capture_views.py --poses` output dir into
the nerfstudio project OpenSplat's loader wants:

```bash
# 1. Capture with poses (writes camera_meta.json)
python capture_views.py --out training_50 --cov 0.50 --poses

# 2. Build the OpenSplat project (transforms.json + ground-plane seed cloud).
#    OpenSplat rejects random init, and the USAF target is a flat plane, so the
#    seed points are sprinkled on y=0.  c2w uses OpenGL convention to match
#    capture_views.py's camera basis.
python make_opensplat_project.py --train training_50

# 3. Train + render the withheld top-down novel view in one shot.
#    --val-image withholds the clean top-down camera; --val-render saves its
#    render (model.forward) every 10 steps -> the last one is the reconstruction.
OMP_NUM_THREADS=1 KMP_DUPLICATE_LIB_OK=TRUE \
  opensplat training_50 -n 7000 --val --val-image topdown_gt.png \
            --val-render training_50/val_render
cp training_50/val_render/7000.png training_50/topdown_recon.png

# 4. Benchmark
python benchmark.py --recon training_50/topdown_recon.png \
                    --gt    training_50/topdown_gt.png --label cov50_opensplat
```

Build notes (macOS): `brew install cmake opencv`; configure with
`-DGPU_RUNTIME=MPS -DCMAKE_PREFIX_PATH=<python torch dir>` (the **Metal** compiler
ships only with a native Apple-Silicon **Xcode.app**, not the Command Line Tools —
omit `-DGPU_RUNTIME=MPS` for a slower CPU build). `OMP_NUM_THREADS=1` avoids a
duplicate-libomp crash between libtorch and OpenCV.

Generated artifacts (`training_50/*.png`, `splat.ply`, `val_render/`) are
git-ignored — regenerate them with the commands above.
