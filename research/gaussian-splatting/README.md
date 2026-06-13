# Gaussian-splatting post — figure & animation source

The Python behind the post
[*3D Gaussian Splatting, Explained*](../../content/posts/2026-06-13-gaussian-splatting.md).
Every still illustration and the training video are generated from here. The
interactive explorer is separate — it's a self-contained page at
[`public/gaussian-splat-viz/splats.html`](../../public/gaussian-splat-viz/splats.html).

## Layout

```
sim/
  figures.py     The eight dark "3blue1brown"-style figures: the novel-view
                 problem, NeRF ray-marching, implicit-vs-explicit, the anatomy
                 of one Gaussian, the training pipeline, the GPU tile-rasterizer,
                 the clone/split/prune densification figure, and the 1200×630
                 social card.
  train_anim.py  The training-loop video (training.mp4) — real 2D GS training.
```

Both scripts write straight into the post's image folder,
`public/img/gaussian-splatting/` (resolved relative to the script).

## `train_anim.py` — real 2D Gaussian splatting

This is an honest, scaled-down version of 3DGS done in 2D (not a fake):

- each Gaussian carries an optimizable mean, scale, rotation, opacity and color,
  plus a fixed depth for the compositing order;
- the renderer is the true front-to-back alpha-compositing splat,
  `C(p) = Σ_i c_i α_i Π_{j<i}(1-α_j)` with `α_i = o_i exp(-½ (p-μ_i)ᵀ Σ_i⁻¹ (p-μ_i))`;
- the loss is the 3DGS objective `0.8·L1 + 0.2·(1 - SSIM)`;
- parameters are optimized by real gradient descent (PyTorch autograd + Adam);
- adaptive density control runs off the accumulated view-space position
  gradient: **clone** under-reconstructed Gaussians, **split** over-large ones,
  **prune** the near-transparent.

It fits a synthetic but Gaussian-friendly "sunset" target and converges to a near
loss of ~0.002 with a couple of thousand Gaussians. The only things it leaves out
versus full 3DGS are the third dimension, view-dependent (spherical-harmonic)
color, and the tile-based rasterizer (it composites the whole image at once).

## Running it

Use a virtualenv with `numpy matplotlib torch` (plus `ffmpeg` on `PATH`):

```bash
python -m venv .venv && source .venv/bin/activate
pip install numpy matplotlib
pip install torch --index-url https://download.pytorch.org/whl/cpu

cd sim
python figures.py      # writes the 8 PNGs
python train_anim.py   # writes training.mp4 — real 2D GS training (CPU ~8 min)
```
