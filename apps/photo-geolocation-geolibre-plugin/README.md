# Photo Geolocation — GeoLibre plugin (scaffold)

Geolocate a photo from a single image by matching points between the image and
the map, then solving for the camera pose with **Perspective-n-Point (PnP)**.
This is a port of the standalone tool from
[itamar-weiss.com](https://itamarweiss.com/photo-geolocation/) into a
[GeoLibre](https://github.com/opengeos/GeoLibre) plugin.

**What this plugin brings:** the PnP solver and the anchor UX (pick the same
physical point in the photo and on the map).

**What it does NOT do:** fetch or model any geodata. All world coordinates come
from GeoLibre — lng/lat from the host map, and **height from whatever DSM
GeoLibre has loaded** (tree, roof, mountain, anything; no building logic).

## Architecture

```
src/
  plugin.ts        GeoLibrePlugin: activate/deactivate, registerRightPanel,
                   toolbar menu, map-click wiring, ENU origin = map centre
  resolver.ts      THE ONLY GEODATA SEAM — sampleDsm() + resolveWorldPoint()
  geo.ts           local ENU metres ⇄ lng/lat (true ground scale, not Mercator)
  store.ts         zustand: anchors, photo, estimates (runs the solver)
  pose/            PnP solver — ported VERBATIM from the original tool
    algorithms.js  6-DOF Gauss-Newton PnP (+ RANSAC, buildObservations)
    registry.js    estimator list
  anchors.js       anchor colour palette (verbatim)
  ui/              right-panel React UI (mounted into GeoLibre's container)
    Panel.tsx      PhotoPane + AnchorList + PoseReadout
  map/
    anchorMarkers.ts  reflects placed anchors as MapLibre markers
  geolibre.ts      minimal stand-ins for the host API types (replace with the
                   real @geolibre import when building against the template)
```

### The one integration point: `resolver.ts`

```ts
sampleDsm(map, lngLat)  // → surface height from GeoLibre's DSM
```

Written against the simplest case: the DSM is the map's **terrain/elevation
source**, so `map.queryTerrainElevation(lngLat)` returns the surface height
directly. If your DSM is a plain raster overlay instead, swap only this
function's body (set it as terrain, or sample the COG/tile via GeoLibre's
DuckDB-WASM Spatial). Nothing else changes.

## How it works (user flow)

1. Open the **Photo Geolocation** panel (toolbar → Open panel).
2. Upload a photo.
3. **+ Add** an anchor, click the point in the photo, then **Set on map** and
   click the same physical point on the GeoLibre map.
4. Repeat for ≥ 4 anchors (5 for RANSAC). The estimated camera lat/lon, heading
   and elevation appear in the Pose Estimation list, and a marker per anchor
   shows on the map.

## Status / TODO

This is a **scaffold**. The PnP math and the anchor UX are real and ported; the
host-integration edges are stubbed against GeoLibre's documented plugin API and
need wiring to the actual template:

- [ ] Replace `src/geolibre.ts` stand-in types with the real host package
      import (`@geolibre/core` or the plugin SDK) used by
      `opengeos/geolibre-plugin-template`.
- [ ] Add the template's `vite.config` + plugin wrapper entry and the
      `package:geolibre` script that emits the installable zip; point
      `plugin.json#entry` at the built bundle.
- [ ] Confirm the DSM is exposed as the terrain source (else adjust
      `sampleDsm`).
- [ ] Optional: persist anchors via the plugin's `getProjectState` /
      `applyProjectState` hooks.
- [ ] Optional: replace MapLibre markers with a deck.gl overlay
      (`app.getDeckGL()`) if you want richer on-map anchor rendering.

The original, full standalone app lives in `../photo-geolocation/`.
