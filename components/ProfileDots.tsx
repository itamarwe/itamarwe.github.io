"use client";

import { useEffect, useRef } from "react";

/**
 * Dot-art ("stipple") rendering of the profile portrait, in the StippleGen 2
 * style: a weighted Voronoi stippling (centroidal Voronoi tessellation) whose
 * local dot *density* tracks image brightness, so the dots are scattered
 * organically rather than on a grid. Each dot's radius also scales with the
 * local brightness. The portrait sits on black, so the dark background carries
 * no dots and disappears, leaving the face and shirt in a field of white dots.
 *
 * The point set is precomputed offline (`research/profile-dots/stipple.mjs` →
 * `public/img/profile-dots/points.json`) so the page just loads and draws it —
 * no per-load relaxation. Points are stored in a normalized integer grid; we
 * scale them to the canvas on draw, so a resize only rescales. Keeping the
 * point set in memory also leaves the door open for a later animation pass.
 */

type Packed = { size: number; bmax: number; n: number; data: number[] };

type Props = {
  /** Precomputed stipple points (normalized integer coords + brightness). */
  src?: string;
  /** Min/max dot radius as a fraction of the canvas size. */
  rMin?: number;
  rMax?: number;
  alt?: string;
  className?: string;
};

function draw(
  ctx: CanvasRenderingContext2D,
  pts: Packed,
  pxSize: number,
  rMin: number,
  rMax: number,
) {
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, pxSize, pxSize);
  ctx.fillStyle = "#fff";
  const { data, n, size, bmax } = pts;
  const sc = pxSize / size;
  const r0 = rMin * pxSize;
  const dr = (rMax - rMin) * pxSize;
  for (let i = 0; i < n; i++) {
    const x = data[i * 3] * sc;
    const y = data[i * 3 + 1] * sc;
    const b = data[i * 3 + 2] / bmax;
    const r = r0 + dr * b;
    if (r < 0.12) continue;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  }
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

    let pts: Packed | null = null;
    let raf = 0;
    let cancelled = false;

    const render = () => {
      if (!pts) return;
      // Backing store = CSS box × devicePixelRatio so dots stay crisp on retina.
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const cssSize = canvas.clientWidth || 300;
      const pxSize = Math.round(cssSize * dpr);
      if (canvas.width !== pxSize) {
        canvas.width = pxSize;
        canvas.height = pxSize;
      }
      draw(ctx, pts, pxSize, rMin, rMax);
    };

    fetch(src)
      .then((r) => r.json())
      .then((data: Packed) => {
        if (cancelled) return;
        pts = data;
        render();
      })
      .catch(() => {});

    const onResize = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(render);
    };
    const ro = new ResizeObserver(onResize);
    ro.observe(canvas);

    return () => {
      cancelled = true;
      ro.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [src, rMin, rMax]);

  return (
    <canvas ref={canvasRef} className={className} role="img" aria-label={alt} />
  );
}
