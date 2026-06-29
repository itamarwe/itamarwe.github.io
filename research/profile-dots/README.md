# Profile dot-art (weighted Voronoi stippling)

Turns the profile portrait (`public/img/profile.jpg`) into a **weighted Voronoi
stipple** — the StippleGen 2 algorithm (Adrian Secord, *Weighted Voronoi
Stippling*, 2002). Points are seeded by importance sampling and then relaxed with
Lloyd's iteration toward the **density-weighted centroid** of each point's Voronoi
cell, until the set becomes a centroidal Voronoi tessellation whose local point
density tracks image brightness. The Voronoi diagram is recomputed each iteration
with the Jump-Flooding Algorithm (JFA) on a grid.

The result is an organic, non-grid scatter of white dots on black: density (and
dot radius) follow brightness, so the bright shirt/face are dense and the dark
studio background carries no dots and disappears.

A "levels" pre-pass (`HL_DIM`/`HL_POW`) rolls off the highlights before
stippling — the brightest areas were packing in so many dots they read as a
blown-out white blob, so the top end of the brightness range is dimmed
(mid-tones left alone) to thin them out.

## Regenerate

```bash
node research/profile-dots/stipple.mjs
```

Writes `public/img/profile-dots/points.json`
(`{ size, bmax, n, data:[x,y,b, …] }`, integer-quantized coordinates). The
on-page render is `components/ProfileDots.tsx`, used by `app/about/page.tsx`; it
just loads this file and draws a white dot per point, radius scaled by `b`.

Re-run after changing the source image or the parameters at the top of
`stipple.mjs` (`G` grid resolution, `N` dot count, `ITERS`, `GAMMA` density
contrast).
