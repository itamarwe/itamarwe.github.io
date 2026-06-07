# Real-Scene Bias Benchmark

`scripts/benchmark-default-scene.mjs` projects real building vertices through
the real default camera, feeds `(mapPoint={x,y,z}, photoX, photoY)` to each
estimator, and compares the returned pose to ground truth.

**Status:** the systematic ~22 m bias documented below applied to the
horizontal-only solvers (Joint GN, Ratio GN). They were replaced by **Full
PnP**, a 6-DOF solver that consumes the anchor's full 3D position. On the
default scene Full PnP achieves **0.00 m median position error at zero
pixel noise** for every N ≥ 6, with no mode dependence (base / roof / mixed).

The text below is preserved as documentation of the original bias.

## Setup

- Scene: `generateScene(seed=42, count=18)` — the user's default map.
- Camera: `p=(0, 45, 90)`, forward `=(0, -0.451, -0.892)` ⇒ heading 0°,
  **pitch = 26.82° down**, Three.js vertical FOV 60° ⇒ horizontal FOV 81.79°,
  focal length 519.6 px on a 900 × 600 image.
- Anchors: random building footprint corners.
  - **base** — anchor y = 0 (ground-level corner).
  - **roof** — anchor y = `building.height`.
  - **mixed** — 50/50 random per anchor.
- 120 trials per condition; same observations feed every estimator.

## Highlights

### Noiseless bias by mode (N = 8)

| mode  | estimator       | medPos (m) | meanPos (m) | p90Pos (m) | medFov° err |
|-------|-----------------|-----------:|------------:|-----------:|------------:|
| base  | Joint GN        |    22.48   |    22.07    |    23.36   |     6.24    |
| base  | Ratio GN        |    22.75   |    22.75    |    22.75   |      —      |
| roof  | Joint GN        |    21.44   |    64.65    |   273.50   |    10.39    |
| roof  | Ratio GN        |    18.04   |    23.20    |    34.91   |      —      |
| mixed | Joint GN        |   210.06   |   153.99    |   323.03   |    51.85    |
| mixed | Ratio GN        |    21.76   |    32.28    |    50.20   |      —      |

At **zero pixel noise**, Joint GN and Ratio GN both settle ~22 m away from
the true camera position on the default scene. Adding anchors does not help
(N = 12 base, σ = 0: still 22.7 m). Adding pixel noise barely moves the
median — the bias dominates.

### Where the bias comes from

The horizontal-only pinhole model assumes the camera's forward vector lies
in the x–z plane, so it predicts

  `u = cx + f · tan(θ − h)`

with `θ = atan2(ΔX, −ΔZ)` — **no dependence on anchor y**. The real
projection is

  `u = cx + f · (right · Δ) / (forward · Δ)`

When `forward_y ≠ 0`, the denominator becomes
`−forward_z · ΔZ + forward_y · ΔY` and gains a y-dependent term. On the
default scene with 27° downward pitch:

- For a **base** anchor (Δy ≈ −45 m) at Δz ≈ −100 m, the true depth is
  ~109, but the model assumes ~100 — a fixed ~9% scale error in angular
  predictions. The solver compensates by pulling the camera back ~22 m,
  producing an apparently self-consistent but biased solution.
- For a **roof** anchor (Δy ≈ −20 m), the depth error shrinks to ~0.3%,
  hence the smaller roof bias.
- For **mixed** anchors, no single `(px, pz, h, f)` can satisfy both
  regimes simultaneously; the solver falls into poor local minima and
  Joint GN's position error blows up to 200–300 m. Ratio GN is
  intrinsics-free so it avoids the focal-length degeneracy that traps
  Joint GN, but still can't reach zero bias.

### What pixel noise adds on top

Once the bias is in, pixel noise contributes ~1–5 m of additional
randomness at σ ≤ 2 px and N ≥ 6. The bias is an order of magnitude larger
than the noise term for this scene — improving noise rejection alone
won't close the gap.

## Takeaway

**Pitch is the dominant error source on this scene, not pixel noise.** Any
meaningful accuracy improvement has to include vertical information — i.e.
estimate pitch and camY — and needs some prior on anchor y (known building
heights are the obvious source). Without that, both Joint GN and Ratio GN
are hard-limited to ~20 m median error on the default scene, no matter how
clean the anchors are or how many the user places.

## Resolution: Full PnP

Replaced the horizontal-only solvers with a 6-DOF Gauss-Newton PnP that
estimates `(px, pz, camY, heading, pitch, f)` jointly from `(u, v)` pixel
residuals against 3D `(X, Y, Z)` anchors. Selected results from the same
benchmark, post-replacement:

| N  | mode  | σpx | medPos (m) | meanPos (m) | p90Pos (m) | medHdg° | medFov° |
|---:|:-----:|:---:|----------:|------------:|-----------:|--------:|--------:|
|  6 | base  |  0  |     0.00  |       0.00  |      0.00  |   0.000 |    0.00 |
|  6 | roof  |  0  |     0.00  |       0.00  |      0.00  |   0.000 |    0.00 |
|  6 | mixed |  0  |     0.00  |       0.00  |      0.00  |   0.000 |    0.00 |
|  8 | base  |  2  |     1.68  |       2.84  |      5.99  |   0.266 |    1.24 |
|  8 | mixed |  2  |     1.61  |       2.27  |      5.05  |   0.237 |    1.13 |
| 12 | mixed |  2  |     0.97  |       1.46  |      3.49  |   0.193 |    0.72 |

The bias is gone; what remains is purely the noise term, which scales
linearly with σ and reduces with N as expected for a properly-conditioned
least-squares problem.

## Reproducing

```
node scripts/benchmark-default-scene.mjs
```

Outputs three tables (one per vertex mode), sweeping N ∈ {4, 6, 8, 12} and
σ ∈ {0, 0.5, 1, 2} px.
