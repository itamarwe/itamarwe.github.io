/**
 * Geographic helpers for the Tel Aviv geolocation flow.
 *
 * Two coordinate systems are in play:
 *
 *   1. WGS84 lat/lon         — what OSM, GPS and tile servers speak.
 *   2. Local ground metres   — the world frame the PnP pipeline solves in.
 *      (x = east, z = -north, y = up). Origin is a fixed reference lat/lon
 *      near central Tel Aviv. We use an equirectangular tangent-plane
 *      approximation: over a few km it is accurate to well under a metre and,
 *      crucially, keeps TRUE ground scale (unlike Web Mercator, which is
 *      stretched by 1/cos(lat) ≈ 1.18 at TLV's latitude — an 18% error that
 *      would wreck the camera-position estimate).
 *
 * z is negated so that +z points south: on the 2D canvas (y grows downward)
 * this puts north at the top of the screen.
 */

export const EARTH_R = 6378137 // metres, WGS84 equatorial radius

// Central Tel Aviv (Dizengoff / King George area). The local frame origin.
export const DEFAULT_ORIGIN = { lat: 32.0773, lon: 34.7818 }

const DEG = Math.PI / 180

export function metresPerDegree(originLat) {
  const perLat = EARTH_R * DEG
  const perLon = EARTH_R * DEG * Math.cos(originLat * DEG)
  return { perLat, perLon }
}

/** WGS84 lat/lon → local ground metres { x, z } relative to `origin`. */
export function llToLocal(lat, lon, origin = DEFAULT_ORIGIN) {
  const { perLat, perLon } = metresPerDegree(origin.lat)
  return {
    x: (lon - origin.lon) * perLon,
    z: -(lat - origin.lat) * perLat,
  }
}

/** Local ground metres { x, z } → WGS84 lat/lon relative to `origin`. */
export function localToLl(x, z, origin = DEFAULT_ORIGIN) {
  const { perLat, perLon } = metresPerDegree(origin.lat)
  return {
    lat: origin.lat - z / perLat,
    lon: origin.lon + x / perLon,
  }
}

/**
 * A square bbox of `radiusMeters` around `origin`, expressed in lat/lon for
 * Overpass / tile fetching.
 */
export function bboxAround(origin = DEFAULT_ORIGIN, radiusMeters = 500) {
  const { perLat, perLon } = metresPerDegree(origin.lat)
  const dLat = radiusMeters / perLat
  const dLon = radiusMeters / perLon
  return {
    south: origin.lat - dLat,
    north: origin.lat + dLat,
    west: origin.lon - dLon,
    east: origin.lon + dLon,
  }
}

// ---- Web Mercator slippy-tile math (for raster basemap tiles) -------------

export function lonToTileX(lon, zoom) {
  return ((lon + 180) / 360) * Math.pow(2, zoom)
}

export function latToTileY(lat, zoom) {
  const r = lat * DEG
  return (
    ((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2) *
    Math.pow(2, zoom)
  )
}

export function tileXToLon(x, zoom) {
  return (x / Math.pow(2, zoom)) * 360 - 180
}

export function tileYToLat(y, zoom) {
  const n = Math.PI - (2 * Math.PI * y) / Math.pow(2, zoom)
  return (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)))
}
