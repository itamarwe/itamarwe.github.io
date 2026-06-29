"use client";

import { useEffect, useRef } from "react";

/**
 * Animated dot-art rendering of the profile portrait. The static look is a
 * weighted Voronoi stipple (StippleGen 2 style) precomputed offline
 * (`research/profile-dots/stipple.mjs` → `public/img/profile-dots/points.json`):
 * a centroidal Voronoi tessellation whose local dot density tracks image
 * brightness, so dots scatter organically and the dark background draws nothing.
 *
 * Each dot keeps its stipple spot as a `home`; every frame a spring pulls it
 * home while a time-varying force field perturbs it, so the portrait stays
 * recognizable but alive and loops forever:
 *   - curl-noise shimmer  — a divergence-free flow field, gentle swirling drift
 *   - breathing           — a slow radial inhale/exhale about the centroid
 *   - pointer repulsion    — dots part around the cursor and spring back
 *
 * Physics runs in normalized [0,1] space (resize just rescales the draw). Dots
 * are blitted from a pre-rendered sprite for speed; the loop pauses when the
 * canvas is off-screen or the tab is hidden. Honors `prefers-reduced-motion`:
 * renders the static stipple and never starts the loop.
 */

type Packed = { size: number; bmax: number; n: number; data: number[] };

type Props = {
  src?: string;
  /** Min/max dot radius as a fraction of the canvas size. */
  rMin?: number;
  rMax?: number;
  alt?: string;
  className?: string;
};

// --- force-field tuning (normalized units, time in seconds) ----------------
const SPRING = 120; // pull-home stiffness
const DAMP = 22; // velocity damping (~critical for SPRING)
const CURL_AMP = 0.8; // shimmer strength
const CURL_FREQ = 18; // shimmer spatial frequency (radians across the image)
const CURL_SPEED = 0.35; // shimmer temporal speed
const BREATHE_AMP = 0.0156; // ±1.56% scale about the centroid
const BREATHE_PERIOD = 7; // seconds per breath
const POINTER_R = 0.2; // repulsion radius (fraction of size)
const POINTER_STR = 2.6; // repulsion strength

// Head mask: suppress the curl swirl over the face/hair so it never distorts
// the features (breathing and pointer repulsion still apply there). An ellipse
// in normalized coords; curl ramps back to full strength beyond HEAD_FADE.
const HEAD_CX = 0.47;
const HEAD_CY = 0.27;
const HEAD_RX = 0.17;
const HEAD_RY = 0.2;
const HEAD_FADE = 1.8; // ellipse-distance² at which curl returns to full

/** Divergence-free flow field: curl of a scalar potential, so dots swirl in
 *  place rather than drifting away. Returns a roughly unit-magnitude vector. */
function curl(x: number, y: number, t: number, out: [number, number]) {
  const p = x * CURL_FREQ + t * CURL_SPEED;
  const q = y * CURL_FREQ + t * CURL_SPEED * 1.3;
  // second octave for a less regular texture
  const p2 = x * CURL_FREQ * 2.1 - t * CURL_SPEED * 0.9;
  const q2 = y * CURL_FREQ * 2.1 + t * CURL_SPEED * 1.1;
  out[0] = -Math.sin(p) * Math.sin(q) - 0.5 * Math.sin(p2) * Math.sin(q2);
  out[1] = -Math.cos(p) * Math.cos(q) - 0.5 * Math.cos(p2) * Math.cos(q2);
}

function makeSprite(): HTMLCanvasElement {
  const S = 64;
  const s = document.createElement("canvas");
  s.width = s.height = S;
  const c = s.getContext("2d")!;
  c.fillStyle = "#fff";
  c.beginPath();
  c.arc(S / 2, S / 2, S / 2 - 2, 0, Math.PI * 2);
  c.fill();
  return s;
}

export default function ProfileDots({
  src = "/img/profile-dots/points.json",
  rMin = 0.6 / 600,
  rMax = 2.4 / 600,
  alt = "Itamar Weiss",
  className,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const sprite = makeSprite();
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");

    // Per-dot state (filled once points load). Coordinates are normalized.
    let n = 0;
    let homeX: Float32Array, homeY: Float32Array, br: Float32Array;
    let posX: Float32Array, posY: Float32Array, velX: Float32Array, velY: Float32Array;
    let curlScale: Float32Array; // 0 over the face, 1 in the free field
    let cx = 0.5,
      cy = 0.5; // centroid, for breathing

    let pxSize = 0;
    const ensureSize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const next = Math.round((canvas.clientWidth || 300) * dpr);
      if (next !== pxSize) {
        pxSize = next;
        canvas.width = pxSize;
        canvas.height = pxSize;
      }
    };

    const render = () => {
      ctx.fillStyle = "#000";
      ctx.fillRect(0, 0, pxSize, pxSize);
      const r0 = rMin * pxSize;
      const dr = (rMax - rMin) * pxSize;
      for (let i = 0; i < n; i++) {
        const r = r0 + dr * br[i];
        if (r < 0.15) continue;
        const d = r * 2;
        ctx.drawImage(sprite, posX[i] * pxSize - r, posY[i] * pxSize - r, d, d);
      }
    };

    // Pointer (normalized canvas coords, or null when not hovering).
    let mx = 0,
      my = 0,
      hover = false;
    const onMove = (e: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      mx = (e.clientX - rect.left) / rect.width;
      my = (e.clientY - rect.top) / rect.height;
      hover = true;
    };
    const onLeave = () => (hover = false);

    const cf: [number, number] = [0, 0];
    const step = (t: number, dt: number) => {
      const breathe = 1 + BREATHE_AMP * Math.sin((2 * Math.PI * t) / BREATHE_PERIOD);
      for (let i = 0; i < n; i++) {
        // breathing target: stipple home scaled about the centroid
        const tx = cx + (homeX[i] - cx) * breathe;
        const ty = cy + (homeY[i] - cy) * breathe;
        let ax = SPRING * (tx - posX[i]) - DAMP * velX[i];
        let ay = SPRING * (ty - posY[i]) - DAMP * velY[i];

        curl(posX[i], posY[i], t, cf);
        const ca = CURL_AMP * curlScale[i];
        ax += ca * cf[0];
        ay += ca * cf[1];

        if (hover) {
          const dx = posX[i] - mx;
          const dy = posY[i] - my;
          const d2 = dx * dx + dy * dy;
          if (d2 < POINTER_R * POINTER_R) {
            const d = Math.sqrt(d2) || 1e-4;
            const f = (POINTER_STR * (1 - d / POINTER_R)) / d;
            ax += f * dx;
            ay += f * dy;
          }
        }

        velX[i] += ax * dt;
        velY[i] += ay * dt;
        posX[i] += velX[i] * dt;
        posY[i] += velY[i] * dt;
      }
    };

    // --- run loop, paused when off-screen / hidden / reduced-motion ---------
    let raf = 0;
    let last = 0;
    let running = false;
    let visible = false;
    let onScreen = false;

    const frame = (now: number) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      ensureSize();
      step(now / 1000, dt);
      render();
      raf = requestAnimationFrame(frame);
    };
    const start = () => {
      if (running || reduce.matches || !visible || !onScreen || !n) return;
      running = true;
      last = performance.now();
      raf = requestAnimationFrame(frame);
    };
    const stop = () => {
      running = false;
      cancelAnimationFrame(raf);
    };

    const drawStatic = () => {
      ensureSize();
      render();
    };

    const io = new IntersectionObserver(
      ([e]) => {
        onScreen = e.isIntersecting;
        if (onScreen) start();
        else stop();
      },
      { rootMargin: "100px" },
    );
    io.observe(canvas);

    const onVis = () => {
      visible = document.visibilityState === "visible";
      if (visible) start();
      else stop();
    };
    document.addEventListener("visibilitychange", onVis);
    visible = document.visibilityState === "visible";

    const ro = new ResizeObserver(() => {
      if (!running) drawStatic(); // keep static frame crisp through resizes
    });
    ro.observe(canvas);

    const onReduceChange = () => {
      if (reduce.matches) {
        stop();
        drawStatic();
      } else {
        start();
      }
    };
    reduce.addEventListener("change", onReduceChange);

    let cancelled = false;
    fetch(src)
      .then((r) => r.json())
      .then((p: Packed) => {
        if (cancelled) return;
        n = p.n;
        homeX = new Float32Array(n);
        homeY = new Float32Array(n);
        br = new Float32Array(n);
        posX = new Float32Array(n);
        posY = new Float32Array(n);
        velX = new Float32Array(n);
        velY = new Float32Array(n);
        curlScale = new Float32Array(n);
        let sx = 0,
          sy = 0;
        for (let i = 0; i < n; i++) {
          const x = p.data[i * 3] / p.size;
          const y = p.data[i * 3 + 1] / p.size;
          homeX[i] = posX[i] = x;
          homeY[i] = posY[i] = y;
          br[i] = p.data[i * 3 + 2] / p.bmax;
          // suppress curl inside the head ellipse, smooth ramp back outside
          const d2 =
            ((x - HEAD_CX) / HEAD_RX) ** 2 + ((y - HEAD_CY) / HEAD_RY) ** 2;
          const s = Math.min(1, Math.max(0, (d2 - 1) / (HEAD_FADE - 1)));
          curlScale[i] = s * s * (3 - 2 * s); // smoothstep
          sx += x;
          sy += y;
        }
        cx = sx / n;
        cy = sy / n;
        canvas.addEventListener("pointermove", onMove);
        canvas.addEventListener("pointerleave", onLeave);
        drawStatic(); // portrait visible immediately
        start();
      })
      .catch(() => {});

    return () => {
      cancelled = true;
      stop();
      io.disconnect();
      ro.disconnect();
      document.removeEventListener("visibilitychange", onVis);
      reduce.removeEventListener("change", onReduceChange);
      canvas.removeEventListener("pointermove", onMove);
      canvas.removeEventListener("pointerleave", onLeave);
    };
  }, [src, rMin, rMax]);

  return (
    <canvas ref={canvasRef} className={className} role="img" aria-label={alt} />
  );
}
