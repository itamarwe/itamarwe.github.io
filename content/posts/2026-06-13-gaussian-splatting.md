---
layout: post
title: "Gaussian Splatting: a Million Soft Blobs That Learn to Look Like a Scene"
comments: true
date: 2026-06-13
categories: graphics
image: /img/gaussian-splatting/social.png
---

<style>
.viz-frame { width: 100%; aspect-ratio: 16/10; border: 0; border-radius: 8px;
  margin: 1rem 0; background: #000; }
@media (max-width: 600px) { .viz-frame { aspect-ratio: 3/4; } }
</style>

I keep running into Gaussian splatting — in mapping demos, in VR captures, in the
"scan your living room with your phone" apps — and for a while I only had a fuzzy
sense of what it actually was. So I sat down to understand it properly, and this
post is the explanation I wish I'd had: what problem it solves, how it relates to
NeRF, and why it took over so fast. I've built a few interactive pieces along the
way so you can poke at the ideas directly.

## The problem both NeRF and splatting are trying to solve

Start with the goal, because NeRF and Gaussian splatting are two answers to the
*same* question: **novel-view synthesis**. You have a handful of photos of a scene,
and you know roughly where each camera was. Now render the scene from a viewpoint
that no photo was ever taken from — smoothly, photorealistically, as if you'd had a
camera there the whole time.

![Novel-view synthesis: from known photos, render an unseen viewpoint](/img/gaussian-splatting/problem.png)

This is harder than it sounds. Stitching photos into a panorama doesn't work —
you're not rotating in place, you're *moving through* the scene, so everything
shifts with parallax. You have to recover something about the 3D structure to fill
in the views in between. Classical photogrammetry does this by building an explicit
mesh: find surfaces, triangulate them, paint textures on top. That's great for
clean, well-defined objects and miserable for leaves, hair, wires, smoke, and
glass. The interesting work of the last few years is about representations that
don't need you to commit to a mesh up front.

## How NeRF does it

[NeRF](https://arxiv.org/abs/2003.08934) (2020) had a beautifully simple idea:
*make the scene a function.* Train a small neural network that takes a 3D point and
a viewing direction — five numbers, `(x, y, z, θ, φ)` — and returns the color and
the density at that point. The whole scene lives in the network's weights.

To render a pixel, you shoot a ray out through it and march along the ray, querying
the network at many sample points, then integrate color weighted by density and how
much light survives to reach the camera. Do that for every pixel and you get an
image.

![NeRF: the scene is a neural function you query by ray-marching](/img/gaussian-splatting/nerf.png)

It works astonishingly well. It also has one structural problem baked right into
that picture: **rendering a single pixel means hundreds of neural-network
queries.** A full image is millions of pixels. Early NeRFs took *days* to train and
many seconds to render one frame. The representation is elegant — a continuous
function over all of space — but it's *implicit*: nothing about the scene is laid
out where you can touch it. Everything has to be re-derived, ray by ray, query by
query.

## Why Gaussian splatting was invented

Gaussian splatting is, at heart, NeRF made practical for real-time rendering. It
keeps the differentiable-rendering idea — optimize a representation until its
rendered views match the photos — and throws out the slow part.

Instead of asking a neural network "what's at this 3D point?", **3D Gaussian
splatting represents the scene as millions of little soft translucent ellipsoids
floating in space.** Each ellipsoid is a *splat*. To render a new view you project
the ellipsoids onto the image plane, blend them front-to-back, and read off a
photorealistic image. No ray marching, no per-pixel network — just projecting and
compositing primitives, which is exactly what GPUs are built to do.

![Implicit neural field versus an explicit cloud of Gaussians](/img/gaussian-splatting/implicit_vs_explicit.png)

That's the whole shift in one line: **NeRF is implicit, splatting is explicit.** The
[2023 paper](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/) made the
claim that landed it everywhere — high-quality novel views at **real-time 1080p**,
from an explicit set of 3D Gaussians, optimized directly from calibrated photos with
a fast visibility-aware rasterizer.

The mental model I find useful is three ways to reconstruct a room from photos:

- **Photogrammetry** says: find surfaces, build a mesh, texture it.
- **NeRF** says: train a neural field mapping location + direction → color + density.
- **Gaussian splatting** says: fill the scene with soft colored blobs, then nudge
  their position, shape, opacity, and color until the rendered views match the
  photos.

## What one Gaussian actually is

A single Gaussian is a tiny fuzzy volumetric particle, and it carries only a few
numbers:

```
position:  x, y, z                    — where it sits in space
shape:     a 3D covariance            — encoded as scale + rotation
opacity:   α                          — how solid it is
color:     spherical-harmonic coeffs  — so color can shift with viewing angle
```

![Anatomy of one Gaussian: position, covariance, opacity, view-dependent color](/img/gaussian-splatting/anatomy.png)

The covariance is the interesting part. A Gaussian isn't a sphere — it's an
*anisotropic* ellipsoid that can be stretched, flattened, and rotated freely. That
flexibility is why a million of them can approximate surfaces, thin structures,
vegetation, and soft semi-transparent stuff so well: a flat surface becomes a sheet
of thin pancake-shaped Gaussians, while a fuzzy region gets fatter, more
volumetric ones. The spherical harmonics let a splat look gold from one angle and
white from another, which is how you get specular-ish highlights without modeling
any real physics.

Here's the thing that took me a moment to internalize: **none of this is a neural
network in the usual sense.** There's no MLP. The "model" is just a giant list of
blobs and their parameters. Below is a scene built entirely out of Gaussians — orbit
it, and switch between seeing them as soft *splats*, as the raw *ellipsoids*, or as
bare *centers*. The same blobs that look like a smooth surface when splatted are, up
close, a discrete cloud of oriented lozenges:

<iframe src="/gaussian-splat-viz/splats.html" title="Interactive Gaussian-splat explorer — orbit the scene and switch between splats, ellipsoids, and point centers" loading="lazy" class="viz-frame"></iframe>

Drop the opacity and the surface dissolves into a translucent fog of overlapping
blobs — which is what the representation *actually* is. Crank it back up and your
eye reassembles a solid object. That tension between "discrete particles" and
"continuous surface" is the whole trick.

## How training works

You don't author those millions of Gaussians by hand — you *optimize* them. The
pipeline goes:

![The training loop: capture, SfM, initialize, render, loss, densify and prune](/img/gaussian-splatting/pipeline.png)

1. **Capture** many images, or a video. Coverage matters more than count: move
   around the object, get parallax, avoid motion blur.
2. **Estimate camera poses.** This is usually [COLMAP](https://colmap.github.io/)
   doing structure-from-motion, which hands you the camera intrinsics, the camera
   poses, *and* a sparse 3D point cloud as a by-product.
3. **Initialize Gaussians** by dropping one at each of those sparse points, with
   some starting scale, rotation, opacity, and color.
4. **Render** a training view differentiably: project every visible Gaussian into
   the image, turn each into a 2D ellipse, sort by depth, alpha-blend, get an image.
5. **Compute the loss** against the real photo — a photometric term plus an
   SSIM-style image-similarity term — and **backpropagate into the splats.** Gradient
   descent updates every Gaussian's position, scale, rotation, opacity, and color
   coefficients. You're not training a network; you're optimizing a cloud of
   differentiable, renderable primitives.
6. **Densify and prune.** Periodically, the optimizer splits or clones Gaussians in
   regions that are still blurry, and deletes the ones that have gone nearly
   transparent or contribute nothing. This interleaved density control — together
   with the anisotropic covariance — was one of the core tricks of the original
   method.

Roughly:

```python
gaussians = initialize_from_sparse_sfm_points()

for step in range(training_steps):
    camera, target_image = sample_training_view()
    rendered = render_gaussians(gaussians, camera)
    loss = image_loss(rendered, target_image)
    loss.backward()
    optimizer.step()

    if step % densify_interval == 0:
        split_or_clone_high_error_gaussians()
        prune_low_opacity_or_useless_gaussians()
```

## The loss: what "match the photo" means

Step 5 hides the only real objective in the whole method, so it's worth writing
down. Because the renderer is differentiable, I can state exactly what we minimize.

**The forward render** for a pixel `p` is alpha compositing — the same front-to-back
"over" operator as any graphics pipeline. Take the Gaussians that cover `p`, sort
them by depth, and accumulate:

```
C(p) = Σ_i  c_i · α_i(p) · Π_{j<i} (1 − α_j(p))

   with  α_i(p) = o_i · exp( −½ (p − μ_i)ᵀ Σ_i'⁻¹ (p − μ_i) )
```

Here `c_i` is the splat's (view-dependent) color, `o_i` its opacity, and `μ_i`, `Σ_i'`
the center and 2×2 covariance of its *projected* 2D ellipse. The exponential is the
Gaussian falloff — a pixel near the center of the ellipse gets nearly full `α`, the
edges almost none. The product term is the **transmittance**: how much light still
gets through after the splats in front have taken their cut. Closer, more opaque
splats dominate, and once transmittance reaches zero the rest of the list behind is
invisible.

**The loss** then compares that rendered image `C` against the ground-truth photo
`Ĉ`. The [3DGS paper](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/)
blends a pixel-wise term with a structural one:

```
L = (1 − λ) · L1  +  λ · L_D-SSIM            (λ ≈ 0.2)

   L1       = (1/N) Σ_p | C(p) − Ĉ(p) |      per-pixel color difference
   L_D-SSIM = 1 − SSIM(C, Ĉ)                  structural dissimilarity
```

Why two terms? **L1** pulls every pixel toward the right color, but on its own it
tolerates a soft, slightly-blurry answer that's "close enough" on average.
**D-SSIM** is built from SSIM, which compares *local* means, variances, and
covariances over small windows — luminance, contrast, and structure — so it
specifically punishes the blur and washed-out texture that L1 shrugs off. Writing it
as `1 − SSIM` makes it zero when the images are identical, so both terms pull the
same way.

Everything feeding `C` — positions, covariances, opacities, color coefficients — is
differentiable, so `∂L/∂(each parameter)` flows back through the compositing and the
projection, and one gradient step nudges all of them at once.

Watching it happen is the part that made it click for me. Here's the loop running
against a target image: it starts from a sparse scattering of blobs, and as it
renders, measures the error, and densifies where things are still vague, the scene
sharpens into focus:

<video src="/img/gaussian-splatting/training.mp4" autoplay loop muted playsinline style="width:100%;border-radius:8px;margin:1rem 0"></video>

(Full disclosure: this clip is an *illustration* of the loop, not a real training
run. It follows the real shape — init → render → measure error → densify → prune —
but uses a simple weighted-blend renderer and a greedy densifier rather than true
gradient descent on the loss above. The source is in the repo.)

## How the GPU makes it real-time

The "real-time 1080p" claim is the whole reason splatting took off, and it falls out
of the fact that rendering is now *rasterization* — projecting and blending
primitives — instead of NeRF's ray-marching with a network query at every sample.
That maps onto a GPU almost perfectly. The quiet hero of the 2023 paper is a
**tile-based differentiable rasterizer**:

![Tile-based rasterization: the image is split into tiles, splats are binned and depth-sorted once, and each tile is blended in parallel by a GPU thread block](/img/gaussian-splatting/tiling.png)

1. **Project** every 3D Gaussian to 2D in parallel — one GPU thread per Gaussian
   works out its screen-space center and 2D covariance.
2. **Bin** the screen into 16×16-pixel tiles and assign each Gaussian to every tile
   its ellipse overlaps.
3. **Sort once.** Rather than sort splats separately for each pixel, do a single
   global GPU radix sort of all `(tile, depth)` pairs per frame. This one move is
   what makes the whole thing fast.
4. **Blend in parallel.** Each tile goes to one GPU thread block; its threads walk
   the tile's depth-sorted list front-to-back, alpha-blending, and bail out early
   once a pixel's transmittance saturates. Tiles are independent, so the GPU chews
   through thousands of them at once.

For **training**, the backward pass is a custom CUDA kernel that pushes gradients
from the rendered pixels back onto each Gaussian's parameters — and because a full
frame renders in milliseconds, you can run tens of thousands of optimization steps
and finish a scene in minutes-to-an-hour on a single consumer GPU. For
**inference**, it's just that forward rasterizer with no network in the loop, which
is where the ≥30 fps comes from. The practical ceiling is **memory**: millions of
explicit Gaussians have to fit in VRAM — which is exactly why the compression work
below matters, and why genuinely huge scenes get partitioned across multiple GPUs.

## Why Gaussians, and not points or triangles?

This was my nagging question — why *this* primitive? It's because a Gaussian sits in
exactly the right spot between the alternatives:

- A **point** has no extent. You'd need an impossible number of them, and there's
  nothing to interpolate between samples.
- A **triangle** needs explicit surface topology — you have to decide, up front,
  which points connect to which, and that's the hard, brittle part of meshing.
- A **Gaussian** is point-like enough to be flexible, surface-like enough to render
  smooth shapes when you flatten it, and volumetric enough to model fuzzy,
  uncertain, semi-transparent regions when you don't.

Real photo reconstruction is messy, and the Gaussian lets you stay non-committal
about geometry while still rendering something that looks right. You never have to
declare "this is a surface and here is its mesh."

## Why it exploded

Put it together and you can see why it spread so fast:

- **Fast to train** relative to classic NeRF — you're optimizing explicit particles,
  not distilling everything into an opaque network.
- **Real-time to render** — projecting splats maps onto the GPU rasterization
  pipeline instead of ray-marching a dense field. The original work leaned hard on
  ≥30 fps at 1080p.
- **Photorealistic from ordinary captures** — phone video of a cluttered real scene,
  leaves and wires and all.
- **Editable-ish** — because it's explicit blobs in space, you can inspect, move,
  segment, prune, compress, or combine them far more naturally than you can edit a
  neural field.
- **A great fit for AR/VR and spatial computing** — a compact, renderable scene
  straight from a capture, which is why people started calling it a "JPEG moment"
  for scanned environments.

## Where it falls down

It's not magic, and the limitations are real:

- **It's not a clean mesh.** You get a gorgeous visual representation, not usable
  geometry. Collision, physics, relighting, and CAD-style editing are all harder
  than with a normal mesh.
- **Memory is heavy.** Millions of Gaussians, each with position, covariance,
  opacity, and SH color, add up fast. Compression is an active front —
  [Niedermayr et al.](https://arxiv.org/abs/2401.02436) report up to **31×**
  compression with minimal visual loss using vector clustering and quantization-aware
  training.
- **View extrapolation is limited.** It's excellent near the captured camera
  trajectory and starts revealing holes, floaters, and hallucinated detail when you
  wander somewhere no photo ever saw. (You can see exactly those floaters as stray
  blobs in the training video above.)
- **Geometry can be wrong even when the image looks right.** Vanilla 3DGS optimizes
  for *view synthesis*, not surface accuracy, which is what motivated
  [2D Gaussian Splatting](https://arxiv.org/abs/2403.17888) — collapsing each blob
  into an oriented planar disk to get view-consistent surfaces.
- **Aliasing under scale changes.** Zoom in or change focal length and you get
  artifacts; [Mip-Splatting](https://arxiv.org/abs/2311.16493) added a 3D smoothing
  filter and a 2D Mip filter to keep rendering alias-free.

That last cluster of follow-up papers is the tell that this is a young, fast-moving
representation. But the core idea is one of those things that feels obvious in
hindsight: if you're going to optimize a scene against photos with a differentiable
renderer, don't hide it inside a neural network — lay it out explicitly as a million
soft blobs, and let the GPU do what it's good at.
