---
layout: post
title: "VGGT-Ω: 3D Reconstruction in a Single Forward Pass"
date: 2026-07-09
categories: vision
image: /img/vggt-omega/social.png
---

![VGGT-Ω: reconstructing cameras and 3D geometry in one forward pass](/img/vggt-omega/social.png)

For most of two decades, turning a pile of photos into a 3D scene meant running an
*optimizer*. You'd feed a few dozen images into COLMAP, walk away, and come back to
find it had matched features, guessed where every camera was, and slowly nudged all
of it into agreement. It worked, it was accurate, and it was the thing you reached
for. It was also slow, fragile, and prone to just... giving up on a scene with too
few textures or too many repeated windows.

The part that made me want to write this post is how completely that has flipped. The
strongest of the new feed-forward methods —
[VGGT-Ω](https://arxiv.org/abs/2605.15195) (VGGT-Omega, May 2026, from the same
Oxford-VGG / Meta AI team behind VGGT) — takes those same photos and hands you the
cameras *and* the dense 3D geometry in **a single forward pass of a neural network**,
in about a second, with no optimization loop at all. No bundle adjustment, no global
alignment, no walking away.

Before the how, here's the whole shift in one clip — the old iterative loop grinding
toward an answer next to VGGT-Ω snapping the scene into place in one pass (a stylized
re-enactment of both processes, not real solver output):

<video src="/img/vggt-omega/optimize-vs-predict.mp4" autoplay loop muted playsinline style="width:100%; border-radius:8px; margin:1rem 0;"></video>

This post is the explanation I wish I'd had for how we got from one to the other: what
the old methods did, why each new idea replaced the last, and what exactly VGGT-Ω
changed to make reconstruction something you *scale* like a language model instead of
something you *tune* like an optimizer.

## What "reconstruction" actually has to recover

Start with the goal, because everything downstream is a different bet on how to reach
it. You have a handful of photos of a scene. You want two things back:

- **Where each camera was** — its position and orientation, plus its focal length
  (the extrinsics and intrinsics).
- **Where every surface point is** — a dense 3D geometry of the scene, usually as a
  depth map per image or a point cloud in one shared coordinate frame.

![From a set of photos, recover camera poses and the 3D geometry in one shared frame](/img/vggt-omega/problem.png)

The catch is that these two unknowns are entangled. You can't place the points without
knowing where the cameras were, and you can't pin down the cameras without knowing
which points in different images are the *same* point. Every method in this post is a
different way to break that chicken-and-egg loop.

## The old way: match, then optimize

Classical **Structure-from-Motion** (SfM), of which [COLMAP](https://colmap.github.io/)
is the canonical implementation, breaks the loop by brute force and iteration:

1. **Detect and match features** across every pair of images — find the same corner,
   the same poster edge, in photo after photo.
2. **Triangulate and bundle-adjust** — guess camera poses and 3D points, then run
   *bundle adjustment*: a big non-linear least-squares optimization that jointly nudges
   every camera and every point until the 3D points reproject as close as possible to
   where they were actually seen.
3. **Densify** with multi-view stereo to go from a sparse set of matched points to a
   dense surface.

![The classical SfM + MVS pipeline: match, iteratively optimize, then densify](/img/vggt-omega/sfm-pipeline.png)

Be clear about what this pipeline gets right, because it's a lot. **When the capture is
good, bundle adjustment is astonishingly precise** — on well-conditioned scenes it pins
camera angles down to hundredths of a degree, which is why photogrammetry and mapping
still run on it. And it's *interpretable*: the reprojection residual tells you not just
the answer but how much to trust it.

**Bundle adjustment is also the problem.** It's an iterative optimizer, so it's slow —
minutes to hours for a real scene — and it's only as good as its starting guess. Give it
a textureless wall, a hall of repeated windows, or too few overlapping views, and the
matches go wrong, the optimization walks into a bad local minimum, and the whole
reconstruction collapses. For twenty years the research went into making that
optimization more robust.

![Where classical SfM breaks: textureless surfaces, repeated structure, too few views, and local minima](/img/vggt-omega/sfm-limitations.png)

VGGT-Ω's lineage went the other way: **what
if you never optimize at all, and just predict the answer?**

## DUSt3R's bet: regress the geometry instead of solving for it

The turn came from [DUSt3R](https://arxiv.org/abs/2312.14132) (2024). Its idea is
almost cheeky: take two images, feed them to a Vision Transformer, and have it
*directly output* a **pointmap** for each — an image-shaped grid where every pixel
holds its `(x, y, z)` position in a shared 3D frame. No feature matching, no bundle
adjustment, no camera intrinsics required as input. The network has seen enough scenes
during training that it simply *regresses* plausible geometry.

![DUSt3R regresses a pointmap per image pair; many images need costly pairwise gluing](/img/vggt-omega/dust3r-pointmap.png)

Because both pointmaps live in the *same* coordinate frame, matching and pose estimation
fall out almost for free — the network has effectively already decided which points
correspond. And where SfM needs many overlapping, well-textured views before it can even
start, DUSt3R happily works from **just two images with extreme viewpoint changes**, the
exact regime that kills feature matching. It was a genuine paradigm shift:
**reconstruction as regression, not optimization.**
[MASt3R](https://arxiv.org/abs/2406.09756) sharpened it with a dedicated matching head
for metric accuracy.

But there's a structural weakness hiding in "take *two* images." Real scenes have
dozens or hundreds. DUSt3R handles that by processing pairs and then stitching them
together with a **global alignment** step — which is, quietly, an optimizer again, and
one whose cost grows with the number of pairs. So it traded bundle adjustment for a
smaller optimization, but didn't escape it.

## VGGT: do the whole scene in one pass

[VGGT](https://arxiv.org/abs/2503.11651) — Visual Geometry Grounded Transformer, the
CVPR 2025 best paper — closed that gap. Instead of pairs plus gluing, it ingests **all
the views at once** and predicts everything jointly in one feed-forward pass: camera
parameters, depth maps, dense pointmaps, and even point tracks. No global alignment
step, because there are no pairs to align — the whole scene is reasoned about together.

The architecture is worth seeing, because VGGT-Ω is best understood as a surgical edit
of it:

![VGGT: DINO tokens, alternating frame/global attention, camera token, and DPT heads](/img/vggt-omega/vggt-arch.png)

Three pieces to hold onto:

- **A DINOv2 encoder** turns each image into a grid of tokens, and each frame gets a
  handful of extra tokens riding along: one **camera token** that will carry that view's
  pose, plus a few **register tokens** — spare tokens with no pixel of their own.
  (Registers were introduced into vision transformers because ViTs kept hijacking random
  patch tokens to stash global information; giving them dedicated scratch tokens fixed
  it. File that away — it becomes the main character shortly.)
- **Alternating attention** is the core trick: layers alternate between *frame*
  attention (tokens attend only within their own image) and *global* attention (every
  token attends to every other token across every frame). Frame attention keeps each
  image coherent; global attention is what lets the network reconcile all the views into
  one consistent 3D world.
- **Prediction heads** decode the refined tokens — a camera head that iteratively
  refines poses, and heavy **DPT** (dense prediction transformer) heads for the
  per-pixel depth, pointmaps, and tracks.

It reconstructs a scene in **under a second** and beat the optimization-based methods it
replaced. It was, rightly, a big deal.

## The wall VGGT hit

Look back at that global-attention block, because it's where VGGT ran out of room.

**Global attention is all-to-all, so its cost grows quadratically.** If you have `F`
frames and `T` tokens each, every global-attention layer relates `F·T` tokens to all
`F·T` others — an `(F·T)²` blowup. Double the frames and you roughly quadruple the
compute of that step. That's fine for a handful of images and brutal for hundreds. On
top of that, the **DPT heads' high-resolution convolutional layers eat a
disproportionate share of GPU memory** — not because they hold many parameters, but
because training has to store their huge activation maps. And the whole model is capped
by how much *labeled* 3D data exists to train on — which is not much, because
ground-truth geometry is expensive to capture.

Here's the observation that opens the door: when the VGGT-Ω team visualized VGGT's
global attention maps, they found them **mostly sparse** — the overwhelming majority of
token pairs barely exchange anything. All-to-all attention was paying full price for
connectivity the network wasn't using.

![Global attention pays quadratic cost, yet VGGT's learned attention maps are mostly sparse](/img/vggt-omega/global-attention-wall.png)

So the question VGGT-Ω set out to answer wasn't "can we predict geometry in one pass"
— VGGT already did that — but "**can we make that pass cheap enough to scale it like we
scale everything else in deep learning: bigger model, more data.**"

## VGGT-Ω's three moves

VGGT-Ω makes three changes, and they compound: together they cut **70% of the GPU
memory during training**, which is precisely what lets everything in the next section
happen.

**1. Register attention.** Remember those spare register tokens each frame carries
(sixteen scene tokens; in the released code, the camera token rides with them through
this block)? VGGT-Ω promotes them from passengers to couriers. In a *register attention*
layer, **only this tiny scratch-token set talks across frames** — the image tokens don't
attend across frames at all. The cross-frame conversation happens between each frame's
register/camera couriers, and then, in the *next frame-attention layer*, each frame's
couriers brief their own image tokens on what the rest of the scene looks like.
Information still flows globally — it just travels through a two-step relay instead of a
full mesh.

![Register attention: each frame's tiny scene-token set meets across frames, then briefs its own frame's tokens locally](/img/vggt-omega/register-attention.png)

The economics are dramatic because this 17-token courier set is so much smaller than the
thousands of image tokens per frame. And the ablations are wonderfully precise about the
trade:
**swapping 25% of the global-attention layers for register attention costs no
measurable accuracy** while saving about 23% of the backbone's training FLOPs and 16%
of its memory. Swap *all* of them and FLOPs collapse to 6% of the original — a
1000-frame reconstruction drops from 240 seconds to 12 — but accuracy falls back to
roughly original-VGGT level. The released model takes the free 25%; the all-register
variant is there if you're running on a drone.

Here's the swap in numbers, at VGGT-Ω's released-code token counts: 1,024 image tokens
per 512×512 frame, 16 registers, and the camera token included in the register-attention
block. Both curves grow quadratically with the number of frames — the register layer is
simply **about 3,750× lower at every F**, because a tiny courier set replaces a
thousand-token crowd:

![Exact interaction counts per attention layer: the register layer is ~3,750× cheaper than the global layer at any frame count](/img/vggt-omega/attention-cost.png)

**2. One lean dense head instead of many heavy ones.** VGGT predicted depth, pointmaps,
and tracks each through its own DPT decoder, and the expensive part — high-resolution
convolutions — hoarded training memory. VGGT-Ω keeps only the cheap low-resolution DPT
layers and replaces the high-resolution blocks with **a single MLP plus a pixel-shuffle
upsampler**. More surprising: it keeps only **one dense head, for depth** (plus a
lightweight camera head that now predicts poses in a single shot — no iterative
refinement; the theme of this post runs deep). Pointmaps and tracks aren't predicted at
all anymore. They're still *supervised* — the training loss checks them — but at
inference you get pointmaps by simply unprojecting the predicted depth through the
predicted cameras. **Multi-task losses, not multi-task heads.** (They tried going
fully convolution-free with MLP-only decoders; it scored fine on benchmarks but produced
blocky depth artifacts that humans notice immediately — so the shallow conv layers
stayed.)

**3. Fifteen times the data — with an assist from the old enemy.** The memory savings
buy the headline: VGGT-Ω trains on about **4 million scene sequences, 15× more than
VGGT**. Around 3M come from curated public and internal datasets; the rest were
distilled from **40 million raw internet-style videos** by a new annotation pipeline —
a VLM filters out hopeless clips, an ensemble of matchers finds correspondences, moving
objects are masked out, and then, in a twist I love, **COLMAP runs bundle adjustment to
produce the pseudo-ground-truth labels**. The classical optimizer this whole lineage
set out to replace is now the *teacher*, grinding away offline at scale so the network
never has to optimize online. (The irony has a face: Johannes Schönberger, COLMAP's
creator, is a co-author on the paper.) The pipeline is deliberately conservative —
anything ambiguous is thrown away — and its retained labels beat MegaSaM's estimates by
a wide margin on Sintel's ground truth.

![VGGT-Ω's data engine: 40M raw videos filtered and pseudo-labeled — by COLMAP — into a 4M-sequence training set](/img/vggt-omega/data-engine.png)

There's also a **self-supervised protocol** — a DINO-style teacher-student setup that
learns from 18 million videos with no labels at all. I expected this to be the headline
and it isn't: it nudges the numbers (point error 0.073 → 0.070 in the ablation) and
mostly helps out-of-distribution robustness. The authors are refreshingly blunt that
self-supervised reconstruction "remains an open problem." The scale story, for now, is
the labeled pipeline.

One more source of speed worth naming: the encoder upgraded from DINOv2 to **DINOv3**,
whose larger 16-pixel patches mean ~25% fewer tokens per image before attention even
starts. Between that and register attention, VGGT-Ω is meaningfully faster than VGGT at
inference — and about **50× faster than MegaSaM**, the strongest optimization-based
method it's compared against. Memory at inference stays remarkably flat as scenes grow —
the released 1B model on a single A100 uses about **6 GB for one frame, 13 GB for 100,
and 43 GB for 500** (those are the reported peak-memory figures for the released model,
not my measurements). The near-linear growth isn't the registers' doing, though — flash
attention never materializes the quadratic attention matrix, so inference memory is
dominated by per-frame tensors either way. Registers buy *speed*; the three moves
together buy *training* memory, and training is where scale lives.

## Scaling it — the part that changes the story

Here's why the efficiency matters beyond "it's faster." Once training a reconstruction
model looks like training a language model — a clean architecture that eats as much data
as you can throw at it — you can ask the question we ask of language models: **does it
keep getting better as you make it bigger?**

It does, and this time there are real numbers to plot. Growing the model from **0.2B to
10B parameters** drops the 3D point error from **0.107 to 0.046**; growing the training
data from two thousand sequences to two million drops it from **0.275 to 0.073**. Both
curves fall smoothly, **power-law-like**, with no plateau in sight — the same shape of
curve that drove the LLM scale-up, showing up in geometry.

![VGGT-Ω's scaling laws: 3D point error falls smoothly as model size grows 0.2B→10B and data grows 2K→2M sequences (values from the paper)](/img/vggt-omega/scaling.png)

The accuracy lands hard where the field was weakest. VGGT-Ω sets the state of the art
on three **static** and three **dynamic** benchmarks — dynamic scenes, things moving
during capture, were the pointmap lineage's blind spot, and training on real video is
what closed it. On the notoriously hard [Sintel](http://sintel.is.tue.mpg.de/)
sequences, camera accuracy (AUC@3°) jumps from the previous best of **22.5 to 40.0 — a
77% relative improvement** — over MegaSaM, an optimization-based method, while running
50× faster. Depth accuracy on the same data improves by 26%. And the 10B model beats
the 1B everywhere, which is the scaling law doing exactly what it promises.

## Where it stands: pros, cons, and where this is headed

Let me lay out the ledger honestly.

**What VGGT-Ω is genuinely good at:**

- **Speed and simplicity** — a single forward pass, ~50× faster than the best
  optimization-based method on dynamic scenes, with no bundle adjustment or global
  alignment to babysit, and over a thousand frames on one A100.
- **Scale** — it behaves like a proper foundation model: a clean architecture whose
  accuracy improves predictably from 0.2B to 10B parameters and from thousands to
  millions of training scenes.
- **Robustness and coverage** — because it *learned* geometry rather than solving for
  it, it doesn't collapse on textureless walls, repeated structure, or barely-overlapping
  views the way SfM does, and it handles **dynamic** scenes, not just static ones.

![VGGT-Ω's limitations: scale ambiguity, confident hallucination off-distribution, and bundle adjustment's precision ceiling](/img/vggt-omega/vggt-omega-limitations.png)

**The honest limitations:**

- **Metric scale is still hard.** Like the rest of the pointmap family, absolute
  real-world scale (is that a dollhouse or a real house?) isn't something a lone image
  set pins down reliably without extra cues.
- **Peak precision still belongs to the optimizer.** The paper says so itself: on
  well-conditioned captures, bundle adjustment reaches angular errors of *hundredths of
  a degree* — survey-grade territory feed-forward doesn't touch yet. The authors' own
  framing is that the two aren't in conflict: a feed-forward pass makes an excellent
  *initialization* for optimization when you need that last decimal. And if what you're
  after is photoreal novel views rather than raw geometry, this output is exactly what a
  [Gaussian-splatting](/blog/gaussian-splatting/) pipeline wants as input.
- **It's a learned prior, so it can hallucinate.** On scenes far from its training
  distribution it will still hand you a confident, plausible-looking geometry that may
  be wrong — with no optimizer residual to warn you the way bundle adjustment's
  reprojection error would.
- **Accuracy was deliberately left on the table.** The authors note that task-specific
  add-ons they chose *not* to ship — iterative camera refinement, feeding RGB into the
  depth head — buy another 4–6% on camera accuracy. They prioritized a simple, clean
  backbone over squeezing the benchmark, betting the community builds on it. The best
  numbers also come from the 10B model, which is real compute.

**Where this is headed.** The most interesting results in the paper aren't about
reconstruction at all. Those sixteen register tokens per frame — the couriers — turn
out to be a compact, transferable **spatial representation of the scene**. Frozen and
bolted onto a vision-language-action model, they lift the LIBERO robot-manipulation
benchmark from 97.1% to **98.5%** average success. Aligned with a language model
CLIP-style, they let text retrieve the right video with **97% top-3 accuracy** — the
registers, which never see a pixel directly, carry enough scene-level meaning to match
natural language. My favorite: cluster the model's internal features on a video of a
dancer in a crowd, and one cluster **tracks the dancer** — motion segmentation nobody
asked for, emerging from reconstruction training alone.

![Reconstruction as a pretext task: predicting the scene yields a spatial representation that transfers to language and action](/img/vggt-omega/future-spatial-foundation.png)

The suggestion is that **reconstruction is becoming a pretext task for spatial
intelligence**: train a model to rebuild the 3D world from video, at scale, and what
you get for free is a network that *understands* space — the missing piece for robots
and embodied agents. The authors go a step further and sketch the endgame: reconstruction
as one capability inside future unified "omni-models," trained jointly with language and
vision, where the geometry resolves what semantics can't and vice versa. The same move
that made language models good at everything by training them to predict the next word
may be about to happen for 3D, by training models to predict the scene.

That's the arc worth sitting with. In a decade we went from *walking away while an
optimizer grinds* to *one forward pass* — with the old optimizer's last job being to
label the training data for its successor. The forward pass turned out to be the easy
part; the real prize is that scaling it teaches the model something like a sense of
space.

---

*Sources: [VGGT-Ω (arXiv 2605.15195)](https://arxiv.org/abs/2605.15195) ·
[project page](https://vggt-omega.github.io/) ·
[VGGT (arXiv 2503.11651)](https://arxiv.org/abs/2503.11651) ·
[DUSt3R](https://arxiv.org/abs/2312.14132) ·
[MASt3R](https://arxiv.org/abs/2406.09756) ·
[COLMAP](https://colmap.github.io/) ·
[facebookresearch/vggt-omega](https://github.com/facebookresearch/vggt-omega) ·
3D house model in the figures: [KayKit Medieval Hexagon Pack](https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0) (CC0)*
