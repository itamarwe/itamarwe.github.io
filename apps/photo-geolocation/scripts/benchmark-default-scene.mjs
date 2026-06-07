#!/usr/bin/env node
// ════════════════════════════════════════════════════════════════════════════════
//  REAL-SCENE POSE BENCHMARK
//
//  Uses the default map (seed=42, 18 buildings) and the default camera pose,
//  picks vertices of random buildings as anchors, projects them through the
//  Three.js-equivalent pinhole camera, and reports per-estimator bias and
//  noise sensitivity.
//
//  Inputs the solver actually sees per anchor:
//    - mapPoint = { x, z }   (footprint corner — no y)
//    - photoX, photoY        (full projected pixel — 3D vertex including y)
//
//  Ground truth we compare against:
//    px, pz, heading, fov_horizontal.
//
//  Vertex mode controls the y-coordinate used for projection:
//    'base'   → y = 0           (all anchors on the ground)
//    'roof'   → y = b.height    (all anchors on rooftops)
//    'mixed'  → random per anchor
//
//  Because photoX at a pitched camera depends on the point's y (through the
//  depth denominator), 'roof' and 'mixed' anchors expose any bias caused by
//  the horizontal-only solver assuming pitch = 0.
// ════════════════════════════════════════════════════════════════════════════════

import { generateScene } from '../src/shared/utils/generateScene.js'
import {
  estimateCentroid,
  estimateFullPnP,
  estimateFullPnPRansac,
} from '../src/v1/pose/algorithms.js'

// ── Scene / camera constants (copied from store.js + photoState.js defaults) ─
const DEFAULT_SEED   = 42
const DEFAULT_COUNT  = 18
const PHOTO_W        = 900
const PHOTO_H        = 600
const CAM_PX         = 0
const CAM_PY         = 45
const CAM_PZ         = 90
const CAM_DX         = 0
const CAM_DY         = -0.45
const CAM_DZ         = -0.89
const CAM_FOV_V_DEG  = 60     // Three.js PerspectiveCamera fov is VERTICAL

// Normalise forward (raw constants aren't quite unit length).
const fNorm = Math.hypot(CAM_DX, CAM_DY, CAM_DZ)
const FX = CAM_DX / fNorm, FY = CAM_DY / fNorm, FZ = CAM_DZ / fNorm

// Horizontal heading (ground-plane projection of forward): θ = atan2(dx, -dz).
const TRUE_HEADING = Math.atan2(FX, -FZ)
const TRUE_PITCH   = Math.asin(-FY)                               // radians; + = pitched down
const TRUE_FOV_V   = CAM_FOV_V_DEG * Math.PI / 180
const TRUE_F_PX    = (PHOTO_H / 2) / Math.tan(TRUE_FOV_V / 2)     // square pixels → f_x = f_y
const TRUE_FOV_H   = 2 * Math.atan((PHOTO_W / 2) / TRUE_F_PX)     // horizontal fov (rad)

// ── Camera basis (right / up / forward) from forward vector + world-up = +Y ──
const WORLD_UP = [0, 1, 0]
function cross(a, b) {
  return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
}
function normalize(v) {
  const n = Math.hypot(v[0], v[1], v[2]) || 1
  return [v[0]/n, v[1]/n, v[2]/n]
}
function dot(a, b) { return a[0]*b[0] + a[1]*b[1] + a[2]*b[2] }

const FWD   = [FX, FY, FZ]
const RIGHT = normalize(cross(FWD, WORLD_UP))
const UP    = cross(RIGHT, FWD)   // already unit-length since right ⟂ forward

/**
 * Project a world point through the default camera. Returns { u, v, depth }.
 * depth > 0 means in front of the camera.
 */
function project(P) {
  const dx = P[0] - CAM_PX
  const dy = P[1] - CAM_PY
  const dz = P[2] - CAM_PZ
  const delta = [dx, dy, dz]
  const cxL = dot(RIGHT, delta)
  const cyL = dot(UP,    delta)
  const depth = dot(FWD, delta)
  if (depth <= 0) return null
  const u = PHOTO_W / 2 + TRUE_F_PX * cxL / depth
  const v = PHOTO_H / 2 - TRUE_F_PX * cyL / depth
  return { u, v, depth }
}

// Footprint corners of a building, as 4 (x, z) pairs.
function footprintCorners(b) {
  const hw = b.width / 2, hd = b.depth / 2
  return [
    [b.x - hw, b.z - hd],
    [b.x + hw, b.z - hd],
    [b.x + hw, b.z + hd],
    [b.x - hw, b.z + hd],
  ]
}

// ─── Observation sampler ──────────────────────────────────────────────────────

function makePrng(seed) {
  let s = (seed ^ 0x9e3779b9) >>> 0
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0
    return s / 0x100000000
  }
}
function gaussian(rand) {
  // Box-Muller
  let u = 0, v = 0
  while (u === 0) u = rand()
  while (v === 0) v = rand()
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
}

/**
 * Sample N observations from the scene.
 *
 * @param {Array}  buildings        Building objects from generateScene.
 * @param {number} n                Number of anchors to collect.
 * @param {'base'|'roof'|'mixed'} mode  y-selection for the anchor's 3D vertex.
 * @param {number} pixelSigma       Gaussian noise stdev in pixels (u and v).
 * @param {()=>number} rand         [0,1) PRNG.
 *
 * @returns {Array} observations in the solver's format, or null if it
 *                  couldn't find `n` visible anchors after many tries.
 */
function sampleObservations(buildings, n, mode, pixelSigma, rand) {
  const obs = []
  let tries = 0
  while (obs.length < n && tries < n * 200) {
    tries++
    const b = buildings[Math.floor(rand() * buildings.length)]
    const corners = footprintCorners(b)
    const c = corners[Math.floor(rand() * 4)]
    let y
    if (mode === 'base') y = 0
    else if (mode === 'roof') y = b.height
    else y = rand() < 0.5 ? 0 : b.height       // mixed

    const P = [c[0], y, c[1]]
    const proj = project(P)
    if (!proj) continue                         // behind camera
    // Must fall inside the photo rectangle.
    if (proj.u < 0 || proj.u >= PHOTO_W) continue
    if (proj.v < 0 || proj.v >= PHOTO_H) continue

    const noisyU = proj.u + (pixelSigma > 0 ? gaussian(rand) * pixelSigma : 0)
    const noisyV = proj.v + (pixelSigma > 0 ? gaussian(rand) * pixelSigma : 0)

    obs.push({
      photoX:   noisyU,
      photoY:   noisyV,
      mapPoint: { x: c[0], y, z: c[1] },
    })
  }
  return obs.length === n ? obs : null
}

// ─── Error metrics ────────────────────────────────────────────────────────────

function wrap(a) {
  while (a > Math.PI)  a -= 2 * Math.PI
  while (a < -Math.PI) a += 2 * Math.PI
  return a
}

function errors(result) {
  if (!result) return null
  const dx = result.px - CAM_PX
  const dz = result.pz - CAM_PZ
  const posErr = Math.hypot(dx, dz)
  const hdgErr = Number.isFinite(result.heading)
    ? Math.abs(wrap(result.heading - TRUE_HEADING)) * 180 / Math.PI
    : NaN
  const fovErr = Number.isFinite(result.fov)
    ? Math.abs(result.fov - TRUE_FOV_H * 180 / Math.PI)
    : NaN
  return { posErr, hdgErr, fovErr }
}

// ─── Estimator registry (mirrors src/v1/pose/registry.js minus color/UI) ──────

const ESTIMATORS = [
  { id: 'centroid',        name: 'Centroid',         fn: estimateCentroid },
  { id: 'full-pnp',        name: 'Full PnP',         fn: estimateFullPnP },
  { id: 'full-pnp-ransac', name: 'Full PnP RANSAC',  fn: estimateFullPnPRansac },
]

// ─── Aggregation ──────────────────────────────────────────────────────────────

function quantile(xs, q) {
  if (xs.length === 0) return NaN
  const sorted = [...xs].sort((a, b) => a - b)
  const idx = Math.min(sorted.length - 1, Math.max(0, Math.floor(q * sorted.length)))
  return sorted[idx]
}
function mean(xs) {
  if (xs.length === 0) return NaN
  let s = 0; for (const x of xs) s += x; return s / xs.length
}
function median(xs) { return quantile(xs, 0.5) }

function pad(s, w) { s = String(s); return s.length >= w ? s : s + ' '.repeat(w - s.length) }
function padL(s, w) { s = String(s); return s.length >= w ? s : ' '.repeat(w - s.length) + s }
function fmt(x, d = 2) {
  if (!Number.isFinite(x)) return 'n/a'
  return x.toFixed(d)
}

function runCondition(buildings, { n, mode, sigma, trials, seed }) {
  const rand = makePrng(seed)
  const ctx  = { photoWidth: PHOTO_W, photoHeight: PHOTO_H }
  const perEst = new Map(ESTIMATORS.map((e) => [e.id, { pos: [], hdg: [], fov: [], fail: 0 }]))

  let samples = 0
  let sampleFails = 0
  while (samples < trials) {
    // Re-seed per trial so each estimator gets exactly the same observations.
    const obs = sampleObservations(buildings, n, mode, sigma, rand)
    if (!obs) { sampleFails++; if (sampleFails > trials * 3) break; continue }
    samples++
    for (const e of ESTIMATORS) {
      const res = e.fn(obs, ctx)
      const err = errors(res)
      const bucket = perEst.get(e.id)
      if (!err) { bucket.fail++; continue }
      bucket.pos.push(err.posErr)
      if (Number.isFinite(err.hdgErr)) bucket.hdg.push(err.hdgErr)
      if (Number.isFinite(err.fovErr)) bucket.fov.push(err.fovErr)
    }
  }

  return { samples, perEst }
}

function printTable(title, rows) {
  console.log('\n' + title)
  console.log('─'.repeat(title.length))
  console.log(
    pad('estimator', 18) +
    padL('n', 4) + '  ' +
    padL('mode',  6) + '  ' +
    padL('σpx',   5) + '  ' +
    padL('medPos', 7) + '  ' +
    padL('meanPos', 8) + '  ' +
    padL('p90Pos', 7) + '  ' +
    padL('medHdg°', 8) + '  ' +
    padL('medFov°', 8) + '  ' +
    padL('ok/N',   7)
  )
  for (const r of rows) {
    console.log(
      pad(r.est, 18) +
      padL(r.n, 4) + '  ' +
      padL(r.mode, 6) + '  ' +
      padL(r.sigma, 5) + '  ' +
      padL(fmt(r.medPos), 7) + '  ' +
      padL(fmt(r.meanPos), 8) + '  ' +
      padL(fmt(r.p90Pos), 7) + '  ' +
      padL(fmt(r.medHdg, 3), 8) + '  ' +
      padL(fmt(r.medFov, 2), 8) + '  ' +
      padL(r.ok, 7)
    )
  }
}

// ─── Main ─────────────────────────────────────────────────────────────────────

function main() {
  const buildings = generateScene(DEFAULT_SEED, DEFAULT_COUNT)
  // Keep only buildings whose base corners are visible in the photo — avoids
  // wasting samples on buildings behind the camera.
  console.log(`Default scene: ${buildings.length} buildings @ seed=${DEFAULT_SEED}`)
  console.log(`Camera: p=(${CAM_PX}, ${CAM_PY}, ${CAM_PZ})  fwd=(${FX.toFixed(3)}, ${FY.toFixed(3)}, ${FZ.toFixed(3)})`)
  console.log(`        heading=${(TRUE_HEADING * 180 / Math.PI).toFixed(2)}°  pitch=${(TRUE_PITCH*180/Math.PI).toFixed(2)}°  fovV=${CAM_FOV_V_DEG}°  fovH=${(TRUE_FOV_H*180/Math.PI).toFixed(2)}°  f=${TRUE_F_PX.toFixed(1)}px`)
  console.log(`Photo: ${PHOTO_W}×${PHOTO_H}`)

  // Build a grid of conditions. Keep trials modest: RANSAC is the slow path.
  const conditions = []
  for (const n of [4, 6, 8, 12]) {
    for (const mode of ['base', 'roof', 'mixed']) {
      for (const sigma of [0, 0.5, 1, 2]) {
        conditions.push({ n, mode, sigma, trials: 120, seed: 0xC0FFEE ^ (n * 131 + sigma * 17 + (mode === 'base' ? 1 : mode === 'roof' ? 2 : 3)) })
      }
    }
  }

  const rows = []
  for (const cond of conditions) {
    const { samples, perEst } = runCondition(buildings, cond)
    for (const e of ESTIMATORS) {
      const b = perEst.get(e.id)
      rows.push({
        est: e.name,
        n: cond.n,
        mode: cond.mode,
        sigma: cond.sigma,
        medPos:  median(b.pos),
        meanPos: mean(b.pos),
        p90Pos:  quantile(b.pos, 0.9),
        medHdg:  median(b.hdg),
        medFov:  median(b.fov),
        ok:      `${b.pos.length}/${samples}`,
      })
    }
  }

  // Split output by mode for readability.
  for (const mode of ['base', 'roof', 'mixed']) {
    printTable(
      `Mode = ${mode}   (pos = metres, hdg = degrees, fov = degrees horizontal)`,
      rows.filter((r) => r.mode === mode),
    )
  }
}

main()
