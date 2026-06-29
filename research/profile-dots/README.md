# Profile dot-art (weighted Voronoi stippling)

Turns the profile portrait (`public/img/profile.jpg`) into a **weighted Voronoi
stipple** — the StippleGen 2 algorithm (Adrian Secord, *Weighted Voronoi
Stippling*, 2002). Points are seeded by importance sampling and then relaxed with
Lloyd's iteration toward the **density-weighted centroid** of each point's Voronoi
cell, until the set becomes a centroidal Voronoi tessellation whose local point
density tracks image brightness. The Voronoi diagram is recomputed each iteration
with the Jump-Flooding Algorithm (JFA) on a grid.

The result is an organic, non-grid scatter of white dots on black: density (and
dot radius) follow the image, so detailed regions are dense and the dark studio
background carries only a faint scatter.

A "levels" pre-pass (`HL_DIM`/`HL_POW`) rolls off the highlights before
stippling — the brightest areas were packing in so many dots they read as a
blown-out white blob, so the top end of the brightness range is dimmed
(mid-tones left alone) to thin them out. A second cap (`CAP_OUT`) limits tone
*outside a face ellipse* to ~80% of the in-face max, so the bright t-shirt no
longer out-shines the face (it was saturating, especially at phone size).

**Edge-aware density.** Density is a mix of tone and *edges* (a blurred Sobel
magnitude), `rho = tone^GAMMA * (FLAT_BASE + EDGE_GAIN * edge)`. Information-rich
regions (face, hair, beard, collar) get many more dots than flat regions (the
t-shirt), while tone still gates the figure against the empty background.

**Foreground / background split.** The subject is far brighter than the
near-black backdrop, so a flood fill of dark pixels inward from the image border
cleanly separates background from foreground — no transparent PNG needed (if a
`public/img/profile.png` with real alpha is added later, prefer that). Each
emitted point carries an `fg` flag (`stride: 4`); `ProfileDots.tsx` uses it to
render the figure over a foreground occupancy mask, while background dots spray
outward from the image center and recycle after leaving the canvas.

## Regenerate

```bash
node research/profile-dots/stipple.mjs
```

Writes `public/img/profile-dots/points.json`
(`{ size, bmax, n, stride, data:[x,y,b,fg, …] }`, integer-quantized
coordinates). The on-page render is `components/ProfileDots.tsx`, used by
`app/about/page.tsx`; it loads this file and draws a white dot per point, radius
scaled by `b`.

Re-run after changing the source image or the parameters at the top of
`stipple.mjs` (`G` grid resolution, `N` dot count, `ITERS`, `GAMMA` density
contrast).
