/**
 * Local tangent-plane (ENU) geometry — the boundary between GeoLibre's
 * lng/lat world and the metric frame the PnP solver works in.
 *
 * Two coordinate systems are in play:
 *
 *   1. WGS84 lat/lon       — what GeoLibre / MapLibre / deck.gl speak.
 *   2. Local ground metres — the world frame the PnP pipeline solves in
 *      (x = east, z = -north, y = up). Origin is a chosen reference lat/lon
 *      (here: the map centre when the plugin activates).
 *
 * We use an equirectangular tangent-plane approximation. Over a few km it is
 * accurate to well under a metre and, crucially, keeps TRUE ground scale —
 * unlike Web Mercator, which stretches distances by 1/cos(lat) (~18 % at
 * 32° N). Feeding the solver Mercator metres would reintroduce that error
 * into the camera position, so ALWAYS cross this boundary via llToLocal /
 * localToLl — never hand the solver raw Mercator coordinates.
 *
 * z is negated so +z points south, matching the original tool's frame; the
 * solver is sign-consistent as long as llToLocal and localToLl agree.
 */

export const EARTH_R = 6378137; // metres, WGS84 equatorial radius
const DEG = Math.PI / 180;

export interface LngLat {
  lng: number;
  lat: number;
}
export interface Origin {
  lat: number;
  lon: number;
}
export interface LocalXZ {
  x: number;
  z: number;
}

export function metresPerDegree(originLat: number): { perLat: number; perLon: number } {
  const perLat = EARTH_R * DEG;
  const perLon = EARTH_R * DEG * Math.cos(originLat * DEG);
  return { perLat, perLon };
}

/** WGS84 lat/lon → local ground metres { x, z } relative to `origin`. */
export function llToLocal(lat: number, lon: number, origin: Origin): LocalXZ {
  const { perLat, perLon } = metresPerDegree(origin.lat);
  return {
    x: (lon - origin.lon) * perLon,
    z: -(lat - origin.lat) * perLat,
  };
}

/** Local ground metres { x, z } → WGS84 lat/lon relative to `origin`. */
export function localToLl(x: number, z: number, origin: Origin): { lat: number; lon: number } {
  const { perLat, perLon } = metresPerDegree(origin.lat);
  return {
    lat: origin.lat - z / perLat,
    lon: origin.lon + x / perLon,
  };
}
