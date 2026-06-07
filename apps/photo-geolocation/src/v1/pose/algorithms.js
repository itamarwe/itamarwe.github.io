// ════════════════════════════════════════════════════════════════════════════════
//  v1 POSE ESTIMATION — full 6-DOF PnP
//
//  Each anchor carries a 3D world point  (mapPoint.x, mapPoint.y, mapPoint.z)
//  and a 2D pixel  (photoX, photoY).  This is exactly the PnP setup, so we
//  solve jointly for the camera pose:
//
//      unknowns = (px, pz, camY, heading, pitch, f)        // 6 DOF, no roll
//
//  Pinhole model (right-handed, world up = +y, pitch positive = looking down):
//      right = ( cos h, 0,  sin h )
//      fwd   = ( sin h cos p, -sin p, -cos h cos p )
//      up    = ( sin h sin p,  cos p, -cos h sin p )
//
//  For anchor at (X, Y, Z) and Δ = (X-px, Y-camY, Z-pz):
//      P  = sin h · ΔX − cos h · ΔZ        (signed forward, horizontal)
//      Q  = cos h · ΔX + sin h · ΔZ        (signed right)
//      D  = cos p · P − sin p · ΔY         (= depth; > 0 in front)
//      V  = sin p · P + cos p · ΔY         (= signed "up" in camera frame)
//      u_pred = cx_px + f · Q / D
//      v_pred = cy_px − f · V / D
//
//  Residuals r_u, r_v are in pixels; minimise Σ(r_u² + r_v²). Gauss-Newton
//  with analytical Jacobian and LM-style damping. ≥ 4 anchors needed to keep
//  the 6×6 normal equations well-conditioned (theoretical minimum is 3 via
//  P3P).
//
//  Why this superseded the horizontal-only Joint GN / Ratio GN: those solvers
//  assumed forward_y = 0, which left a structural ~22 m position bias on the
//  default 27°-pitched camera even at zero pixel noise. See
//  docs/real-scene-bias.md.  Using anchor y closes the bias.
// ════════════════════════════════════════════════════════════════════════════════

// ─── Small helpers ────────────────────────────────────────────────────────────

export function wrapAngle(a) {
  while (a >  Math.PI) a -= 2 * Math.PI
  while (a < -Math.PI) a += 2 * Math.PI
  return a
}

/** Solve NxN linear system A·x = b via Gaussian elimination. Returns null if singular. */
function solveLinear(A, b) {
  const n = A.length
  const M = A.map((row, i) => [...row, b[i]])
  for (let i = 0; i < n; i++) {
    let p = i
    for (let j = i + 1; j < n; j++) if (Math.abs(M[j][i]) > Math.abs(M[p][i])) p = j
    if (Math.abs(M[p][i]) < 1e-12) return null
    if (p !== i) [M[i], M[p]] = [M[p], M[i]]
    for (let j = 0; j < n; j++) {
      if (j === i) continue
      const f = M[j][i] / M[i][i]
      for (let k = i; k < n + 1; k++) M[j][k] -= f * M[i][k]
    }
  }
  const x = new Array(n)
  for (let i = 0; i < n; i++) x[i] = M[i][n] / M[i][i]
  return x
}

/**
 * Build observations from anchor state.  Both photoPixel (x, y) and a full 3D
 * mapPoint (x, y, z) are forwarded.  mapPoint.y defaults to 0 if unset for
 * older anchors; current store auto-fills y from the building footprint.
 */
export function buildObservations(anchors) {
  const out = []
  for (const a of anchors) {
    if (!a.photoPixel || !a.mapPoint) continue
    out.push({
      photoX: a.photoPixel.x,
      photoY: a.photoPixel.y ?? null,
      mapPoint: {
        x: a.mapPoint.x,
        y: Number.isFinite(a.mapPoint.y) ? a.mapPoint.y : 0,
        z: a.mapPoint.z,
      },
    })
  }
  return out
}

// ════════════════════════════════════════════════════════════════════════════════
//  A. CENTROID — trivial baseline. No pose, just averages anchor (x, z).
// ════════════════════════════════════════════════════════════════════════════════

export function estimateCentroid(observations /*, ctx */) {
  if (observations.length < 1) return null
  let sx = 0, sz = 0
  for (const o of observations) { sx += o.mapPoint.x; sz += o.mapPoint.z }
  const n = observations.length
  return { px: sx / n, pz: sz / n, heading: NaN, fov: NaN }
}

// ════════════════════════════════════════════════════════════════════════════════
//  B. FULL PnP — 6-DOF pose with analytical-Jacobian Gauss-Newton.
// ════════════════════════════════════════════════════════════════════════════════

/** Sum of squared (u, v) pixel residuals for the current pose. */
function pnpResidualSumSq(obs, cx_px, cy_px, x, z, cy, h, p, f) {
  const sh = Math.sin(h), ch = Math.cos(h)
  const sp = Math.sin(p), cp = Math.cos(p)
  let s = 0
  for (const o of obs) {
    const a = o.mapPoint.x - x
    const b = o.mapPoint.y - cy
    const c = o.mapPoint.z - z
    const P = sh * a - ch * c
    const Q = ch * a + sh * c
    const D = cp * P - sp * b
    const V = sp * P + cp * b
    if (D < 1e-3) return Infinity
    const u_pred = cx_px + f * Q / D
    const v_pred = cy_px - f * V / D
    const ru = o.photoX - u_pred
    const rv = (o.photoY ?? cy_px) - v_pred
    s += ru * ru + rv * rv
  }
  return s
}

/**
 * One Gauss-Newton step.  Builds the 6×6 normal equations from analytical
 * Jacobians and returns the parameter update Δ (or null if singular /
 * any anchor projects behind the camera).
 *
 * Param order: [x, z, cy, h, pitch, f].
 *
 * Partial derivatives (collected from the model in the file header):
 *   ∂Q/∂x = -ch    ∂Q/∂z = -sh    ∂Q/∂h = -P
 *   ∂P/∂x = -sh    ∂P/∂z =  ch    ∂P/∂h =  Q
 *   ∂D/∂x = -cp·sh ∂D/∂z =  cp·ch ∂D/∂cy = sp   ∂D/∂h =  cp·Q   ∂D/∂p = -V
 *   ∂V/∂x = -sp·sh ∂V/∂z =  sp·ch ∂V/∂cy = -cp  ∂V/∂h =  sp·Q   ∂V/∂p =  D
 *
 *   u_pred = cx_px + f·Q/D
 *   ∂u_pred/∂param = f·(∂Q·D − Q·∂D)/D²    (and ∂u_pred/∂f = Q/D)
 *
 *   v_pred = cy_px − f·V/D
 *   ∂v_pred/∂param = −f·(∂V·D − V·∂D)/D²   (and ∂v_pred/∂f = −V/D)
 *
 *   r_u = u_obs − u_pred  ⇒  ∂r/∂param = −∂u_pred/∂param
 *   r_v = v_obs − v_pred  ⇒  ∂r/∂param = −∂v_pred/∂param
 *
 *   Two convenient simplifications used below:
 *     • ∂V/∂p = cp·P − sp·b = D
 *     • ∂D/∂p = −(sp·P + cp·b) = −V
 *   so ∂v_pred/∂p reduces to −f·(D² + V²)/D².
 */
function pnpStep(obs, cx_px, cy_px, params, lambda) {
  const [x, z, cy, h, p, f] = params
  const sh = Math.sin(h), ch = Math.cos(h)
  const sp = Math.sin(p), cp = Math.cos(p)

  const JTJ = [
    [0,0,0,0,0,0], [0,0,0,0,0,0], [0,0,0,0,0,0],
    [0,0,0,0,0,0], [0,0,0,0,0,0], [0,0,0,0,0,0],
  ]
  const JTr = [0,0,0,0,0,0]

  for (const o of obs) {
    const a = o.mapPoint.x - x
    const b = o.mapPoint.y - cy
    const c = o.mapPoint.z - z
    const P = sh * a - ch * c
    const Q = ch * a + sh * c
    const D = cp * P - sp * b
    const V = sp * P + cp * b
    if (D < 1e-3) return null
    const id  = 1 / D
    const id2 = id * id

    const u_pred = cx_px + f * Q * id
    const v_pred = cy_px - f * V * id
    const ru = o.photoX - u_pred
    const rv = (o.photoY ?? cy_px) - v_pred

    // ∂u_pred / ∂[x, z, cy, h, p, f]
    const k_uh = -P * D - cp * Q * Q                           // numerator for ∂h
    const du_dx = f * (-ch * D + Q * cp * sh) * id2
    const du_dz = f * (-sh * D - Q * cp * ch) * id2
    const du_dcy = -f * Q * sp * id2
    const du_dh  = f * k_uh * id2
    const du_dp  = f * Q * V * id2
    const du_df  = Q * id

    // ∂v_pred / ∂[x, z, cy, h, p, f]
    const k_v = sp * D - cp * V                                // shared factor
    const dv_dx  =  f * sh * k_v * id2
    const dv_dz  = -f * ch * k_v * id2
    const dv_dcy =  f * (cp * D + sp * V) * id2
    const dv_dh  = -f * Q  * k_v * id2
    const dv_dp  = -f * (D * D + V * V) * id2
    const dv_df  = -V * id

    // J = ∂r/∂param = −∂pred/∂param
    const Ju = [-du_dx, -du_dz, -du_dcy, -du_dh, -du_dp, -du_df]
    const Jv = [-dv_dx, -dv_dz, -dv_dcy, -dv_dh, -dv_dp, -dv_df]

    for (let i = 0; i < 6; i++) {
      JTr[i] -= Ju[i] * ru + Jv[i] * rv
      for (let j = 0; j < 6; j++) {
        JTJ[i][j] += Ju[i] * Ju[j] + Jv[i] * Jv[j]
      }
    }
  }

  // LM-style relative Tikhonov so units (metres / radians / pixels) don't
  // need ad-hoc per-parameter scaling.
  for (let d = 0; d < 6; d++) JTJ[d][d] += lambda * (1 + JTJ[d][d])

  return solveLinear(JTJ, JTr)
}

/** Run GN from a single seed.  Returns model + residual, or null on failure. */
function runFullPnPGN(obs, cx_px, cy_px, x0, z0, cy0, h0, p0, f0) {
  let params = [x0, z0, cy0, h0, p0, f0]
  const MAX_ITERS = 60
  const lambda    = 1e-6

  for (let iter = 0; iter < MAX_ITERS; iter++) {
    const delta = pnpStep(obs, cx_px, cy_px, params, lambda)
    if (!delta) return null

    // Backtracking line search on the squared-residual.
    const r0 = pnpResidualSumSq(obs, cx_px, cy_px, ...params)
    let step = 1, accepted = false
    for (let k = 0; k < 14; k++) {
      const trial = params.map((v, i) => v + delta[i] * step)
      if (trial[5] < 1) { step *= 0.5; continue }      // f must stay positive
      const rn = pnpResidualSumSq(obs, cx_px, cy_px, ...trial)
      if (rn < r0 - 1e-9) { params = trial; accepted = true; break }
      step *= 0.5
    }
    if (!accepted) break

    // Mixed-units convergence test: scale heading/pitch up so a fraction-of-a-
    // degree step counts the same as a fraction-of-a-metre step.
    const norm =
      Math.abs(delta[0] * step) + Math.abs(delta[1] * step) +
      Math.abs(delta[2] * step) +
      100 * (Math.abs(delta[3] * step) + Math.abs(delta[4] * step)) +
      Math.abs(delta[5] * step) / 100
    if (norm < 1e-7) break
  }

  return {
    px: params[0], pz: params[1], camY: params[2],
    heading: wrapAngle(params[3]), pitch: params[4], f: params[5],
    residual: pnpResidualSumSq(obs, cx_px, cy_px, ...params),
  }
}

/** Multi-seed wrapper.  Returns the best PnP solution. */
export function estimateFullPnP(observations, ctx) {
  if (observations.length < 4) return null
  return runFullPnPMultiSeed(observations, ctx, /* fast = */ false)
}

function runFullPnPMultiSeed(observations, ctx, fast) {
  const W = ctx.photoWidth, H = ctx.photoHeight
  const cx_px = W / 2, cy_px = H / 2

  // Centroid + spread of (x, z) anchors → seed circle radius / centre.
  const c = estimateCentroid(observations)
  let rSum = 0, yMean = 0
  for (const o of observations) {
    rSum  += Math.hypot(o.mapPoint.x - c.px, o.mapPoint.z - c.pz)
    yMean += o.mapPoint.y
  }
  yMean /= observations.length
  const seedRadius = Math.max(rSum / observations.length * 2, 30)

  // Seed grids.  We keep these small because the GN basin is wide for
  // reasonable starting points; in benchmarks at ≥6 anchors any seed in the
  // correct angular octant converges to the same answer to numerical
  // precision. Fast mode (RANSAC inner) trims further.
  const angleSteps = fast ? 4 : 8
  const fSeeds  = fast ? [W * 1.0] : [W * 0.7, W * 1.4]
  const cySeeds = fast ? [yMean + 25] : [yMean + 25]
  const pSeeds  = fast ? [0]       : [-0.3, 0.1]

  let best = null
  for (let k = 0; k < angleSteps; k++) {
    const angle  = (k / angleSteps) * Math.PI * 2
    const startX = c.px + Math.sin(angle) * seedRadius
    const startZ = c.pz - Math.cos(angle) * seedRadius
    const startH = angle + Math.PI

    for (const f0 of fSeeds) {
      for (const cy0 of cySeeds) {
        for (const p0 of pSeeds) {
          const r = runFullPnPGN(observations, cx_px, cy_px, startX, startZ, cy0, startH, p0, f0)
          if (!r || !isFinite(r.residual) || r.f <= 0) continue
          if (best === null || r.residual < best.residual) best = r
        }
      }
    }
  }

  if (!best) return null
  const fovDeg = 2 * Math.atan(W / (2 * best.f)) * 180 / Math.PI
  return {
    px: best.px, pz: best.pz, py: best.camY,
    heading: best.heading, pitch: best.pitch,
    fov: fovDeg, f: best.f,
    residual: best.residual,
  }
}

// ════════════════════════════════════════════════════════════════════════════════
//  C. FULL PnP RANSAC — robust variant.
//
//  Inner solver: estimateFullPnPFast (single focal/cy/pitch seed × 4 angles).
//  Inlier test: 2D pixel residual ≤ 5 px.  Final refinement: full PnP on the
//  inlier set.
// ════════════════════════════════════════════════════════════════════════════════

function lcgFromObservations(observations) {
  let seed = 0x811c9dc5 >>> 0
  for (const o of observations) {
    const parts = [o.photoX, o.photoY ?? 0, o.mapPoint.x, o.mapPoint.y, o.mapPoint.z]
    for (const v of parts) {
      const n = Math.round(v * 1000) | 0
      seed = Math.imul(seed ^ (n >>> 0), 0x01000193) >>> 0
    }
  }
  if (seed === 0) seed = 1
  let s = seed
  return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 2 ** 32 }
}

function sampleWithoutReplacement(items, count, rand) {
  const pool = [...items]
  const out = []
  for (let i = 0; i < count; i++) {
    const idx = Math.floor(rand() * pool.length)
    out.push(pool[idx])
    pool.splice(idx, 1)
  }
  return out
}

/** 2D pixel residual of a single observation against a candidate model. */
function pnpPixelResidual(obs, model, cx_px, cy_px) {
  const a = obs.mapPoint.x - model.px
  const b = obs.mapPoint.y - model.py
  const c = obs.mapPoint.z - model.pz
  const sh = Math.sin(model.heading), ch = Math.cos(model.heading)
  const sp = Math.sin(model.pitch),   cp = Math.cos(model.pitch)
  const P = sh * a - ch * c
  const Q = ch * a + sh * c
  const D = cp * P - sp * b
  if (D < 1e-3) return Infinity
  const V = sp * P + cp * b
  const u_pred = cx_px + model.f * Q / D
  const v_pred = cy_px - model.f * V / D
  const du = obs.photoX - u_pred
  const dv = (obs.photoY ?? cy_px) - v_pred
  return Math.hypot(du, dv)
}

export function estimateFullPnPRansac(observations, ctx) {
  if (observations.length < 5) return null
  const W = ctx.photoWidth, H = ctx.photoHeight
  const cx_px = W / 2, cy_px = H / 2

  const iterations = Math.min(120, Math.max(30, observations.length * 6))
  const threshold  = 5    // pixels — generous to absorb sub-pixel anchor placement noise
  const rand = lcgFromObservations(observations)

  let bestInliers = null
  let bestModel   = null

  for (let i = 0; i < iterations; i++) {
    // Minimum 4 anchors for the 6×6 GN to remain well-conditioned.
    const subset = sampleWithoutReplacement(observations, 4, rand)
    const model  = runFullPnPMultiSeed(subset, ctx, /* fast = */ true)
    if (!model) continue

    const inliers = observations.filter(
      (o) => pnpPixelResidual(o, model, cx_px, cy_px) <= threshold
    )
    if (!bestInliers || inliers.length > bestInliers.length) {
      bestInliers = inliers; bestModel = model; continue
    }
    if (inliers.length === bestInliers.length && bestModel && model.residual < bestModel.residual) {
      bestInliers = inliers; bestModel = model
    }
  }

  if (!bestInliers || bestInliers.length < 4) return null
  return runFullPnPMultiSeed(bestInliers, ctx, /* fast = */ false) ?? bestModel
}
