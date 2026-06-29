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

// ---- load brightness / density field --------------------------------------
const { data } = await sharp(SRC)
  .resize(G, G, { fit: "fill" })
  .grayscale()
  .raw()
  .toBuffer({ resolveWithObject: true });

const bright = new Float32Array(G * G); // 0..1 luma
const rho = new Float32Array(G * G); // density used for weighting
for (let i = 0; i < G * G; i++) {
  const b = data[i] / 255;
  bright[i] = b;
  rho[i] = Math.pow(b, GAMMA);
}
const brightAt = (x, y) => {
  const xi = Math.min(G - 1, Math.max(0, x | 0));
  const yi = Math.min(G - 1, Math.max(0, y | 0));
  return bright[yi * G + xi];
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
const out = new Array(N * 3);
for (let s = 0; s < N; s++) {
  const b = brightAt(sx[s], sy[s]);
  out[s * 3] = Math.round((sx[s] / G) * OUT_SIZE);
  out[s * 3 + 1] = Math.round((sy[s] / G) * OUT_SIZE);
  out[s * 3 + 2] = Math.round(b * BMAX);
}
mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(
  OUT,
  JSON.stringify({ size: OUT_SIZE, bmax: BMAX, n: N, data: out }),
);
console.log(`wrote ${N} points -> ${OUT}`);
