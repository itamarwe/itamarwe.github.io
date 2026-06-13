# Gaussian-splatting post — figure & animation source

The Python behind the post
[*Gaussian Splatting: a Million Soft Blobs That Learn to Look Like a Scene*](../../content/posts/2026-06-13-gaussian-splatting.md).
Every still illustration and the training video are generated from here. The
interactive explorer is separate — it's a self-contained page at
[`public/gaussian-splat-viz/splats.html`](../../public/gaussian-splat-viz/splats.html).

## Layout

```
sim/
  figures.py     The seven dark "3blue1brown"-style figures: the novel-view
                 problem, NeRF ray-marching, implicit-vs-explicit, the anatomy
                 of one Gaussian, the training pipeline, the GPU tile-rasterizer,
                 and the 1200×630 social card.
  train_anim.py  The training-loop video (training.mp4).
```

Both scripts write straight into the post's image folder,
`public/img/gaussian-splatting/` (resolved relative to the script).

## A caveat about `train_anim.py`

It is a **didactic stand-in, not real 3DGS training.** There is no gradient
descent, no photometric + D-SSIM loss, and no backprop. It uses a normalized
alpha-weighted blend for rendering and a greedy "drop a Gaussian at the
highest-error pixel / prune the weakest / shrink everything" heuristic for
densification. It reproduces the *shape* of the loop (init → render → measure
error → densify → prune) and the look of blobs resolving into a scene, which is
all the embedded clip is meant to convey. The math the real method optimizes is
written out in the post's "The loss" section.

## Running it

Use a virtualenv with `numpy scipy matplotlib` (plus `ffmpeg` on `PATH` for the
video):

```bash
python -m venv .venv && source .venv/bin/activate
pip install numpy scipy matplotlib

cd sim
python figures.py      # writes the 7 PNGs
python train_anim.py   # writes training.mp4 (needs ffmpeg)
```
