// Weighted Voronoi stippling of the profile portrait — the StippleGen 2 algorithm
// (Adrian Secord, "Weighted Voronoi Stippling", 2002): seed N points, then run
// Lloyd's relaxation toward the *density-weighted* centroid of each point's
// Voronoi cell until the set settles into a centroidal Voronoi tessellation whose
// local point density tracks image brightness. The Voronoi diagram is computed
// per iteration with the Jump-Flooding Algorithm (JFA) on a grid.
//
// Input : public/img/profile.jpg  (decoded + downsampled with sharp)
// Output: public/img/profile-dots/points.json  — { size, bmax, n, data:[x,y,b,...] }
//         x,y are integers in [0,size), b is brightness in [0,bmax].
//
// Re-run after changing the source image or parameters:
//   node research/profile-dots/stipple.mjs
//
// The on-page render (components/ProfileDots.tsx) loads this file and draws a
// white dot per point on black, radius scaled by b. Brightness is the density,
// so the dark studio background draws no points and simply disappears.

import sharp from "sharp";
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..", "..");
const SRC = resolve(ROOT, "public/img/profile.jpg");
const OUT = resolve(ROOT, "public/img/profile-dots/points.json");

// ---- parameters -----------------------------------------------------------
const G = 512; // Voronoi/density grid resolution
const N = 8000; // number of stipple dots
const ITERS = 40; // Lloyd relaxation iterations
const GAMMA = 0.85; // density = brightness^GAMMA  (<1 lifts midtones)
const OUT_SIZE = 4096; // coordinate quantization in the output file
const BMAX = 255;

// Highlight rolloff (a "levels" pre-pass): the bright shirt/face highlights
// were packing in too many dots, reading as a blown-out white blob. Dim the
// highlights before stippling so they get fewer, slightly smaller dots. The
// b^HL_POW factor concentrates the dimming in the top end, leaving the
// mid-tones essentially untouched:  b' = b * (1 - HL_DIM * b^HL_POW).
const HL_DIM = 0.55; // how much to pull down pure white (0..1)
const HL_POW = 2.5; // higher => dimming stays closer to the highlights
const levels = (b) => b * (1 - HL_DIM * Math.pow(b, HL_POW));

// Brightness ceiling outside the face. The bright t-shirt was hitting the same
// tone ceiling as the face and saturating (especially shrunk to phone size), so
// outside a face ellipse the tone (which drives dot size *and* density) is
// capped to ~80% of the in-face max — the face stays the bright focal point and
// the shirt reads dimmer. Smoothly ramps over the ellipse so there's no seam.
const FACE_CX = 0.47;
const FACE_CY = 0.28;
const FACE_RX = 0.18;
const FACE_RY = 0.22;
const FACE_FADE = 1.8; // ellipse-distance² where the cap reaches full strength
const CAP_OUT = 0.44; // ~80% of the rolloff ceiling (~0.549)
const faceCap = (xN, yN) => {
  const d2 = ((xN - FACE_CX) / FACE_RX) ** 2 + ((yN - FACE_CY) / FACE_RY) ** 2;
  const s = Math.min(1, Math.max(0, (d2 - 1) / (FACE_FADE - 1)));
  const out = s * s * (3 - 2 * s); // 0 in face, 1 outside
  return 1 - out * (1 - CAP_OUT); // 1.0 in face, CAP_OUT outside
};

// Edge-aware density: density is a mix of tone (so the figure stays present and
// the dark background empty) and *edges* (so detailed, information-rich regions
// like the face/hair/collar get many more dots than flat regions like the
// t-shirt). rho = tone^GAMMA * (FLAT_BASE + EDGE_GAIN * edge).
const FLAT_BASE = 0.32; // density of a flat, edgeless area (relative)
const EDGE_GAIN = 2.4; // how hard edges boost density
const EDGE_BLUR = 5; // box-blur radius (px) spreading edges into a region
const EDGE_POW = 0.7; // <1 lifts faint edges so detail reads broadly

// Foreground mask: the subject is far brighter than the near-black studio
// backdrop, so a flood fill of dark pixels inward from the border cleanly
// separates background from foreground (no transparent PNG needed). If a
// public/img/profile.png with real alpha is added later, prefer that instead.
const BG_THRESH = 0.18; // luma below this, reachable from the border, is bg

// ---- load luma -------------------------------------------------------------
const { data } = await sharp(SRC)
  .resize(G, G, { fit: "fill" })
  .grayscale()
  .raw()
  .toBuffer({ resolveWithObject: true });

const lum = new Float32Array(G * G); // original luma 0..1
const bright = new Float32Array(G * G); // tone after rolloff + face cap (dot size)
for (let i = 0; i < G * G; i++) {
  lum[i] = data[i] / 255;
  const xN = (i % G) / G;
  const yN = ((i / G) | 0) / G;
  bright[i] = Math.min(levels(lum[i]), faceCap(xN, yN));
}

// Sobel edge magnitude on the original luma, normalized.
const edge = new Float32Array(G * G);
const lAt = (x, y) =>
  lum[Math.min(G - 1, Math.max(0, y)) * G + Math.min(G - 1, Math.max(0, x))];
let emax = 0;
for (let y = 0; y < G; y++) {
  for (let x = 0; x < G; x++) {
    const gx =
      lAt(x + 1, y - 1) + 2 * lAt(x + 1, y) + lAt(x + 1, y + 1) -
      (lAt(x - 1, y - 1) + 2 * lAt(x - 1, y) + lAt(x - 1, y + 1));
    const gy =
      lAt(x - 1, y + 1) + 2 * lAt(x, y + 1) + lAt(x + 1, y + 1) -
      (lAt(x - 1, y - 1) + 2 * lAt(x, y - 1) + lAt(x + 1, y - 1));
    const m = Math.hypot(gx, gy);
    edge[y * G + x] = m;
    if (m > emax) emax = m;
  }
}
// separable box blur to spread edges into a region around the detail
const blur = (src) => {
  const tmp = new Float32Array(G * G);
  const r = EDGE_BLUR;
  const norm = 1 / (2 * r + 1);
  for (let y = 0; y < G; y++) {
    let acc = 0;
    for (let x = -r; x <= r; x++) acc += src[y * G + Math.min(G - 1, Math.max(0, x))];
    for (let x = 0; x < G; x++) {
      tmp[y * G + x] = acc * norm;
      const xo = Math.max(0, x - r);
      const xi = Math.min(G - 1, x + r + 1);
      acc += src[y * G + xi] - src[y * G + xo];
    }
  }
  const dst = new Float32Array(G * G);
  for (let x = 0; x < G; x++) {
    let acc = 0;
    for (let y = -r; y <= r; y++) acc += tmp[Math.min(G - 1, Math.max(0, y)) * G + x];
    for (let y = 0; y < G; y++) {
      dst[y * G + x] = acc * norm;
      const yo = Math.max(0, y - r);
      const yi = Math.min(G - 1, y + r + 1);
      acc += tmp[yi * G + x] - tmp[yo * G + x];
    }
  }
  return dst;
};
const edgeB = blur(edge);
for (let i = 0; i < G * G; i++) edgeB[i] = Math.pow(edgeB[i] / emax, EDGE_POW);

// Density = tone gate × (flat base + edge boost).
const rho = new Float32Array(G * G);
for (let i = 0; i < G * G; i++) {
  rho[i] = Math.pow(bright[i], GAMMA) * (FLAT_BASE + EDGE_GAIN * edgeB[i]);
}

// Background mask by flood fill of dark pixels from the border.
const isBg = new Uint8Array(G * G);
{
  const st = [];
  const push = (x, y) => {
    if (x < 0 || y < 0 || x >= G || y >= G) return;
    const i = y * G + x;
    if (isBg[i] || lum[i] > BG_THRESH) return;
    isBg[i] = 1;
    st.push(i);
  };
  for (let x = 0; x < G; x++) { push(x, 0); push(x, G - 1); }
  for (let y = 0; y < G; y++) { push(0, y); push(G - 1, y); }
  while (st.length) {
    const i = st.pop();
    const x = i % G;
    const y = (i / G) | 0;
    push(x + 1, y); push(x - 1, y); push(x, y + 1); push(x, y - 1);
  }
}

const brightAt = (x, y) => {
  const xi = Math.min(G - 1, Math.max(0, x | 0));
  const yi = Math.min(G - 1, Math.max(0, y | 0));
  return bright[yi * G + xi];
};
const fgAt = (x, y) => {
  const xi = Math.min(G - 1, Math.max(0, x | 0));
  const yi = Math.min(G - 1, Math.max(0, y | 0));
  return isBg[yi * G + xi] ? 0 : 1;
};

// ---- seed points by rejection sampling ∝ density --------------------------
let rngState = 0x9e3779b9;
const rand = () => {
  // deterministic xorshift so regeneration is reproducible
  rngState ^= rngState << 13;
  rngState ^= rngState >>> 17;
  rngState ^= rngState << 5;
  return ((rngState >>> 0) % 1e6) / 1e6;
};

const sx = new Float32Array(N);
const sy = new Float32Array(N);
{
  let placed = 0;
  let guard = 0;
  while (placed < N && guard < N * 500) {
    guard++;
    const x = rand() * G;
    const y = rand() * G;
    if (rand() < rho[(y | 0) * G + (x | 0)]) {
      sx[placed] = x;
      sy[placed] = y;
      placed++;
    }
  }
  if (placed < N) throw new Error(`only seeded ${placed}/${N} points`);
}

// ---- JFA Voronoi assignment ------------------------------------------------
// For every grid pixel, find the nearest site. seedI holds the site index;
// we read site positions from sx/sy for exact distances.
const seedI = new Int32Array(G * G);

function jfa() {
  seedI.fill(-1);
  for (let s = 0; s < N; s++) {
    const px = Math.min(G - 1, Math.max(0, sx[s] | 0));
    const py = Math.min(G - 1, Math.max(0, sy[s] | 0));
    seedI[py * G + px] = s;
  }
  for (let step = G >> 1; step >= 1; step >>= 1) {
    for (let y = 0; y < G; y++) {
      for (let x = 0; x < G; x++) {
        const idx = y * G + x;
        let cur = seedI[idx];
        let curD =
          cur < 0
            ? Infinity
            : (sx[cur] - x) * (sx[cur] - x) + (sy[cur] - y) * (sy[cur] - y);
        for (let dy = -1; dy <= 1; dy++) {
          const ny = y + dy * step;
          if (ny < 0 || ny >= G) continue;
          for (let dx = -1; dx <= 1; dx++) {
            if (dx === 0 && dy === 0) continue;
            const nx = x + dx * step;
            if (nx < 0 || nx >= G) continue;
            const cand = seedI[ny * G + nx];
            if (cand < 0) continue;
            const d =
              (sx[cand] - x) * (sx[cand] - x) +
              (sy[cand] - y) * (sy[cand] - y);
            if (d < curD) {
              curD = d;
              cur = cand;
            }
          }
        }
        seedI[idx] = cur;
      }
    }
  }
}

// ---- Lloyd relaxation toward density-weighted centroids --------------------
const accX = new Float64Array(N);
const accY = new Float64Array(N);
const accW = new Float64Array(N);

for (let it = 0; it < ITERS; it++) {
  jfa();
  accX.fill(0);
  accY.fill(0);
  accW.fill(0);
  for (let y = 0; y < G; y++) {
    for (let x = 0; x < G; x++) {
      const s = seedI[y * G + x];
      if (s < 0) continue;
      const w = rho[y * G + x];
      accX[s] += (x + 0.5) * w;
      accY[s] += (y + 0.5) * w;
      accW[s] += w;
    }
  }
  let moved = 0;
  for (let s = 0; s < N; s++) {
    if (accW[s] > 1e-9) {
      const nx = accX[s] / accW[s];
      const ny = accY[s] / accW[s];
      moved += Math.abs(nx - sx[s]) + Math.abs(ny - sy[s]);
      sx[s] = nx;
      sy[s] = ny;
    } else {
      // empty cell — drop it into a bright spot so it stays useful
      sx[s] = rand() * G;
      sy[s] = rand() * G;
    }
  }
  process.stdout.write(
    `  iter ${String(it + 1).padStart(2)}/${ITERS}  avg move ${(moved / N).toFixed(3)} px\r`,
  );
}
process.stdout.write("\n");

// ---- emit -----------------------------------------------------------------
// Stride 4 per point: x, y, brightness, fg (1 = foreground, 0 = background).
const out = new Array(N * 4);
let bgCount = 0;
for (let s = 0; s < N; s++) {
  const b = brightAt(sx[s], sy[s]);
  const fg = fgAt(sx[s], sy[s]);
  if (!fg) bgCount++;
  out[s * 4] = Math.round((sx[s] / G) * OUT_SIZE);
  out[s * 4 + 1] = Math.round((sy[s] / G) * OUT_SIZE);
  out[s * 4 + 2] = Math.round(b * BMAX);
  out[s * 4 + 3] = fg;
}
mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(
  OUT,
  JSON.stringify({ size: OUT_SIZE, bmax: BMAX, n: N, stride: 4, data: out }),
);
console.log(`wrote ${N} points (${bgCount} background) -> ${OUT}`);
