"use client";

import { useEffect, useRef } from "react";

/**
 * Dot-art ("halftone") rendering of the profile portrait. The source image is
 * sampled once into a `cols x rows` grid of luma values; each grid cell becomes
 * a white dot whose radius scales with the local brightness, on a pure-black
 * background. The portrait already sits on black, so the background samples to
 * zero-radius dots and simply disappears — leaving the face and shirt drawn in
 * dots of varying size.
 *
 * Sampling and drawing are kept separate (`sampleGrid` → `draw`) so a later
 * animation pass can re-run `draw` each frame against the cached grid without
 * re-reading pixels.
 */

type Props = {
  /** Source image (same-origin so the canvas stays untainted). */
  src?: string;
  /** Grid resolution: number of dots across (image is square, so rows = cols). */
  cols?: number;
  /** Max dot radius as a fraction of half the cell (>1 lets bright dots touch). */
  fill?: number;
  /** Brightness curve; <1 fattens midtones, >1 thins them. */
  gamma?: number;
  alt?: string;
  className?: string;
};

function sampleGrid(img: HTMLImageElement, cols: number, rows: number) {
  const off = document.createElement("canvas");
  off.width = cols;
  off.height = rows;
  const octx = off.getContext("2d", { willReadFrequently: true })!;
  octx.drawImage(img, 0, 0, cols, rows);
  const data = octx.getImageData(0, 0, cols, rows).data;
  const grid = new Float32Array(cols * rows);
  for (let i = 0; i < cols * rows; i++) {
    const r = data[i * 4];
    const g = data[i * 4 + 1];
    const b = data[i * 4 + 2];
    grid[i] = (0.299 * r + 0.587 * g + 0.114 * b) / 255; // luma 0..1
  }
  return grid;
}

function draw(
  ctx: CanvasRenderingContext2D,
  grid: Float32Array,
  cols: number,
  rows: number,
  pxSize: number,
  fill: number,
  gamma: number,
) {
  ctx.clearRect(0, 0, pxSize, pxSize);
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, pxSize, pxSize);
  ctx.fillStyle = "#fff";

  const cell = pxSize / cols;
  const maxR = cell * 0.5 * fill;

  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      const v = Math.pow(grid[y * cols + x], gamma);
      const r = maxR * v;
      if (r < 0.12) continue; // skip the black background
      ctx.beginPath();
      ctx.arc((x + 0.5) * cell, (y + 0.5) * cell, r, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

export default function ProfileDots({
  src = "/img/profile.jpg",
  cols = 100,
  fill = 1.15,
  gamma = 0.78,
  alt = "Itamar Weiss",
  className,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rows = cols;
    let grid: Float32Array | null = null;
    let raf = 0;

    const render = () => {
      if (!grid) return;
      // Size the backing store to the CSS box × devicePixelRatio so dots stay
      // crisp on retina. The element is square (aspect-ratio:1 in CSS).
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const cssSize = canvas.clientWidth || 300;
      const pxSize = Math.round(cssSize * dpr);
      if (canvas.width !== pxSize) {
        canvas.width = pxSize;
        canvas.height = pxSize;
      }
      draw(ctx, grid, cols, rows, pxSize, fill, gamma);
    };

    const img = new Image();
    img.decoding = "async";
    img.onload = () => {
      grid = sampleGrid(img, cols, rows);
      render();
    };
    img.src = src;

    const onResize = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(render);
    };
    const ro = new ResizeObserver(onResize);
    ro.observe(canvas);

    return () => {
      ro.disconnect();
      cancelAnimationFrame(raf);
      img.onload = null;
    };
  }, [src, cols, fill, gamma]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      role="img"
      aria-label={alt}
    />
  );
}
