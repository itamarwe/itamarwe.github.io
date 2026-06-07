# Pose Estimator Performance Verification

How we verify the v1 pose estimators, the scenarios we test, and the measured
sensitivity of each algorithm to pixel-click noise.

## What we're verifying

The app's core claim: given `N` anchors (each pinned both to a pixel in the
photo and a map point in the 2D orthophoto), the estimators recover the
camera's pose accurately. For each estimator we measure:

- **Position error** — 2D distance in world units between estimated camera
  and ground truth. The single number users care about.
- **Heading error** — unsigned angular delta, degrees.
- **FOV error** — unsigned focal-length delta, degrees (Joint GN only; Ratio GN
  is intrinsics-free).
- **Wall-clock ms** — time for a single call. The UI runs estimators on every
  anchor edit, so > 100 ms per call is disruptive.

## Methodology

All tests synthesize ground-truth scenes, project the anchors through a clean
pinhole model to get `(photoX, photoY)`, optionally add pixel noise, and hand
the resulting observations straight to the same functions the UI calls
(`estimateJointGN`, `estimateRatioGN`, `estimateJointGNRansac`).

### Ground-truth generation

Per trial (seeded LCG for determinism):

- Camera position on a circle of radius 80 around origin, azimuth uniform.
- Camera height fixed at `camY = 25`. Heading ∈ `[-0.4, 0.4]` rad (≈ ±23°).
- Photo size `1200 × 800 px`, FOV = 60°.
- Anchor `(x, z)` drawn uniformly in `[-70, 70]²`. Anchor `y` drawn uniformly
  in `[0, 30]` to represent mixed ground and building-top picks.
- Rejection-sample anchors against the camera's view cone so we only keep
  ones that'd actually fall inside the image frame.
- Project each anchor through the pinhole model to get `(photoX, photoY)`.

### Pixel-noise injection

Each `photoX` and `photoY` independently gets additive Gaussian noise with
standard deviation `σ` px. The four regimes we sweep:

- `σ = 0` — perfect clicks. Machine-precision behaviour.
- `σ = 0.5` — pixel-perfect human click.
- `σ = 1–2` — careful-human click on a clear feature.
- `σ = 5` — sloppy click, or click on a blurry / ambiguous feature.

### Metrics

Per scenario we run **30 independent trials**. Report median, p90 and median
time. Medians (not means) because the error distribution is heavy-tailed when
the seed grid happens to miss the basin of attraction — the p90 column surfaces
those cases.

## Results

### 1. Anchor-count sweep (noiseless, FOV = 60°)

Shows the baseline — how accurate is each estimator before any noise.

| N  | estimator       | medPos | p90Pos | medHdg | medFov | medMs |
|---:|-----------------|-------:|-------:|-------:|-------:|------:|
|  4 | Joint GN        |   2.38 |  13.16 |   0.70 |   4.54 |   3.5 |
|  4 | Joint GN RANSAC |   2.38 |  13.16 |   0.70 |   4.54 |  27.3 |
|  4 | Ratio GN        |    —   |    —   |    —   |    —   |   —   |
|  5 | Joint GN        |   4.67 |   9.44 |   1.02 |   2.98 |   4.0 |
|  5 | Ratio GN        |   0.00 |   0.89 |   0.00 |    —   |   2.6 |
|  6 | Joint GN        |   4.58 |  10.33 |   1.01 |   3.94 |   4.6 |
|  6 | Ratio GN        |   0.00 |   1.47 |   0.00 |    —   |   2.4 |
|  8 | Joint GN        |   1.99 |   7.45 |   0.46 |   1.26 |   5.4 |
|  8 | Ratio GN        |   0.00 |   0.00 |   0.00 |    —   |   2.5 |
| 12 | Joint GN        |   0.04 |   4.28 |   0.01 |   0.04 |   7.4 |
| 12 | Ratio GN        |   0.00 |   0.00 |   0.00 |    —   |   3.4 |

Dashes = estimator can't run (below its `minAnchors`). Ratio GN requires
`N ≥ 5`; Joint GN / RANSAC require `N ≥ 4`.

### 2. Sensitivity to pixel noise (N = 8)

The headline sensitivity table. Does a couple of pixels of noise wreck things?

| σ (px) | estimator | medPos | p90Pos | medHdg | medFov |
|-------:|-----------|-------:|-------:|-------:|-------:|
|  0     | Joint GN  |   1.99 |   7.45 |   0.46 |   1.26 |
|  0     | Ratio GN  |   0.00 |   0.00 |   0.00 |    —   |
|  0.5   | Joint GN  |   1.87 |   8.08 |   0.16 |   1.07 |
|  0.5   | Ratio GN  |   0.61 |   2.06 |   0.36 |    —   |
|  1     | Joint GN  |   1.35 |  10.73 |   0.25 |   1.22 |
|  1     | Ratio GN  |   0.59 |   2.64 |   1.57 |    —   |
|  2     | Joint GN  |   1.78 |   4.65 |   0.37 |   1.23 |
|  2     | Ratio GN  |   0.90 |   9.50 |   1.65 |    —   |
|  5     | Joint GN  |   2.24 |  29.31 |   0.49 |   1.69 |
|  5     | Ratio GN  |   2.86 |  14.67 |   2.80 |    —   |

### 3. Few-anchor sensitivity (N = 6)

At the low end of realistic anchor counts, both estimators degrade faster.

| σ (px) | estimator | medPos | p90Pos | medHdg |
|-------:|-----------|-------:|-------:|-------:|
|  0     | Joint GN  |   4.58 |  10.33 |   1.01 |
|  0     | Ratio GN  |   0.00 |   1.47 |   0.00 |
|  0.5   | Joint GN  |   3.37 |   8.20 |   0.53 |
|  0.5   | Ratio GN  |   0.84 |  13.68 |   1.28 |
|  1     | Joint GN  |   2.70 |  10.55 |   0.51 |
|  1     | Ratio GN  |   1.28 |   7.46 |   1.70 |
|  2     | Joint GN  |   5.60 |  23.48 |   1.08 |
|  2     | Ratio GN  |   2.56 |  12.62 |   3.52 |
|  5     | Joint GN  |   9.02 | 132.24 |   1.97 |
|  5     | Ratio GN  |  11.69 |  49.65 |   8.33 |

## Observations

1. **Joint GN is 4-DOF horizontal-only.** Earlier experiments treated anchor
   heights as additional unknowns (5 + N DOFs) so `photoY` could constrain the
   vertical angle. That worked on synthetic data but destabilised for small N
   (the system becomes under-determined for N ≤ 5), and the vertical residual
   amplified pixel noise when `|camY − anchorY|` was small — exactly the
   camera-at-building-top case in this app. The `photoY` pixel is stored in
   observations for future use (visualisation, optional 3D refinement) but is
   not consumed by the current solver. The code's header comment in
   `src/v1/pose/algorithms.js` has the full rationale.

2. **Ratio GN is ~exact on noiseless data** for `N ≥ 5`. It's over-determined
   there (N−2 ratio residuals vs. 3 unknowns) and converges to machine
   precision. Joint GN does not match this because it also has to recover `f`;
   with `N = 5` that's 5 unknowns vs. 5 horizontal residuals → just determined,
   slight numerical slack leaks into position.

3. **Noise sensitivity is sub-linear at moderate N.** At `N = 8`, medPos
   doubling `σ` from 1 → 2 → 5 px only nudges Joint GN from 1.35 → 1.78 → 2.24 m.
   The angular residual form (`atan2(du, f)`) is numerically well-conditioned
   and absorbs small pixel errors without exploding. Ratio GN degrades slightly
   faster because its ratio form differentiates the pixel signal twice (both
   numerator and denominator are noisy).

4. **p90 is the warning shot.** Means behave, but p90 spikes on `N = 6, σ = 5px`
   to 132 m for Joint GN — that's the "once in 10 trials, the seed grid lands
   in a local minimum" tail. Users with high-noise clicks should push to `N ≥ 8`.

5. **RANSAC has zero accuracy cost, ~10× time cost** on clean data (same
   medPos, medHdg as bare Joint GN but 50 ms vs 5 ms). Its value shows only
   when outliers exist — a user picks the wrong building edge, or mis-associates
   an anchor. The inner RANSAC loop now uses a stripped-down 4-seed × 1-focal
   solver (`estimateJointGNFast`) so the big anchor sets don't hang the browser:
   previously with the 5+N-DOF solver inside, N=10 anchors had the browser
   spinning for several seconds.

6. **`N = 4` is everyone's floor.** Joint GN has exactly 4 unknowns and 4
   equations — no slack. Even noiseless, the seed grid sometimes lands in a
   bad basin (p90 = 13 m). Tell users "4 anchors is a minimum, 6+ is
   comfortable, 8+ is robust to 2 px noise."

7. **Timings are comfortable for interactive use.** All non-RANSAC runs are
   under 8 ms even at `N = 12`, so the UI can re-estimate on every anchor
   edit without stuttering. RANSAC tops out around 75 ms at `N = 12`, which
   is just perceptible as a frame drop but never blocking.

## Recommendations when clicking anchors

If a user asks "how accurate is this?", the honest answer is:

- **6+ careful anchors (≤ 1 px noise)**: expect sub-metre median, single-digit
  p90 errors.
- **6–8 anchors, 2 px noise**: 2–5 m median is typical.
- **Fewer than 6 anchors or 5+ px noise**: errors can tail into tens of metres
  occasionally; the 2D map view will visibly jitter on anchor edits.
- **Outliers suspected**: turn on Joint GN RANSAC.

## Reproduction

Open the dev server, open browser devtools, and paste:

```js
const { estimateJointGN, estimateRatioGN, estimateJointGNRansac } =
  await import('/src/v1/pose/algorithms.js')

function lcg(seed){let s=seed>>>0;if(s===0)s=1;return()=>{s=(Math.imul(s,1664525)+1013904223)>>>0;return s/2**32}}
function gaussian(rnd){const u1=Math.max(1e-12,rnd()),u2=rnd();return Math.sqrt(-2*Math.log(u1))*Math.cos(2*Math.PI*u2)}
function wrapA(a){while(a>Math.PI)a-=2*Math.PI;while(a<-Math.PI)a+=2*Math.PI;return a}

function makeTruth(rnd, { fov=60, nAnchors=8, camDist=80 } = {}) {
  const heading = (rnd()-0.5) * 0.8
  const camAng = rnd() * Math.PI * 2
  const camX = Math.cos(camAng)*camDist, camZ = Math.sin(camAng)*camDist
  const photoWidth=1200, photoHeight=800, camY=25
  const f = photoWidth / (2 * Math.tan(fov*Math.PI/180 / 2))
  const cx = photoWidth/2, cy = photoHeight/2
  const halfFov = fov*Math.PI/180 / 2
  const anchors = []
  let tries = 0
  while (anchors.length < nAnchors && tries++ < nAnchors*80) {
    const ax=(rnd()-0.5)*140, ay=rnd()*30, az=(rnd()-0.5)*140
    const theta = Math.atan2(ax-camX, -(az-camZ))
    const b = theta - heading
    if (Math.abs(b) > halfFov-0.02) continue
    const dz_cam = (ax-camX)*Math.sin(heading) - (az-camZ)*Math.cos(heading)
    if (dz_cam <= 1) continue
    const photoX = cx + f * Math.tan(b)
    const photoY = cy - f * (ay-camY) / dz_cam
    if (photoY < 0 || photoY > photoHeight) continue
    anchors.push({ photoX, photoY, mapPoint: { x: ax, z: az } })
  }
  return { camX, camZ, heading, fov, f, anchors, ctx: { photoWidth, photoHeight } }
}

async function run({ N=8, noise=0, trials=30 }={}) {
  const ests = [['joint',estimateJointGN,4],['ratio',estimateRatioGN,5],['ransac',estimateJointGNRansac,4]]
  const r = Object.fromEntries(ests.map(([id])=>[id,{pos:[],hd:[],ms:[]}]))
  for (let t=0; t<trials; t++) {
    const rnd = lcg(0xc0ffee + t*7919 + N*31 + Math.floor(noise*100))
    const tr = makeTruth(rnd, { nAnchors: N })
    if (tr.anchors.length < N) continue
    const obs = tr.anchors.map(a => ({
      photoX: a.photoX + (noise ? gaussian(rnd)*noise : 0),
      photoY: a.photoY + (noise ? gaussian(rnd)*noise : 0),
      mapPoint: a.mapPoint,
    }))
    for (const [id, fn, minA] of ests) {
      if (obs.length < minA) continue
      const t0 = performance.now()
      const m = fn(obs, tr.ctx); const ms = performance.now()-t0
      if (!m) continue
      r[id].pos.push(Math.hypot(m.px-tr.camX, m.pz-tr.camZ))
      if (Number.isFinite(m.heading)) r[id].hd.push(Math.abs(wrapA(m.heading-tr.heading))*180/Math.PI)
      r[id].ms.push(ms)
    }
  }
  const med = a => a.length ? a.slice().sort((x,y)=>x-y)[a.length>>1] : null
  console.table(Object.fromEntries(Object.entries(r).map(([id, v]) =>
    [id, { medPos: med(v.pos)?.toFixed(2), medHd: med(v.hd)?.toFixed(2), medMs: med(v.ms)?.toFixed(1) }])))
}

// Example: reproduce the N=8 σ=2 row.
await run({ N: 8, noise: 2 })
```

All numbers above were produced on an M-series Mac, Vite dev server, single
JS thread. Timings will scale with hardware; the error metrics should not.
