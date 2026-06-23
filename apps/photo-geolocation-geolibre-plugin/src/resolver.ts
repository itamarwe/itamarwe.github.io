/**
 * The ONLY place this plugin reads GeoLibre's geodata.
 *
 * A map click gives us lng/lat. PnP also needs the point's height. We do NOT
 * reason about buildings, rooftops, levels, or terrain-vs-structure — we just
 * sample the DSM (digital surface model: whatever is on top at that point —
 * ground, tree, roof, mountain, anything) that GeoLibre has loaded, and take
 * that single value as the anchor's elevation.
 *
 * `sampleDsm` is the whole seam. It is written against the simplest case: the
 * DSM is registered as the map's terrain/elevation source, so MapLibre's
 * `queryTerrainElevation` returns the surface height directly. If your DSM is
 * instead a plain raster overlay (displayed but not set as terrain), MapLibre
 * has no pixel-read API — swap the body for one of:
 *   - register that layer as the terrain source, then this one-liner works; or
 *   - sample the underlying COG/tile value (GeoLibre's DuckDB-WASM Spatial /
 *     raster utilities can do this).
 * Nothing else in the plugin needs to change — keep the dependency here.
 */

import type { MapLibreMap } from './geolibre';
import { llToLocal, type LngLat, type Origin } from './geo';

export interface WorldPoint {
  x: number; // east, metres
  y: number; // up, metres (= DSM value at the click)
  z: number; // -north, metres
}

/** Surface height (metres) from the DSM that GeoLibre has loaded. */
export function sampleDsm(map: MapLibreMap, lngLat: LngLat): number {
  // queryTerrainElevation returns the elevation of the active terrain source
  // at lngLat, or null when no terrain is set / the tile isn't loaded yet.
  const h = map.getTerrain?.() ? map.queryTerrainElevation?.(lngLat) : null;
  return Number.isFinite(h as number) ? (h as number) : 0;
}

/**
 * Turn a map click into the 3D world point the PnP solver consumes.
 * x/z come from the true-ground-metres ENU conversion (NOT Mercator);
 * y is the DSM sample.
 */
export function resolveWorldPoint(map: MapLibreMap, lngLat: LngLat, origin: Origin): WorldPoint {
  const { x, z } = llToLocal(lngLat.lat, lngLat.lng, origin);
  const y = sampleDsm(map, lngLat);
  return { x, y, z };
}
