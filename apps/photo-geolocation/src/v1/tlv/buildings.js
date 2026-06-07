/**
 * Building-source adapter for the Tel Aviv geolocation flow.
 *
 * Returns building footprints as polygons in the local ground-metres frame,
 * each with a resolved height — the discrete 3D geometry the user clicks to
 * place map anchors for Full PnP.
 *
 * Default source: OpenStreetMap via the Overpass API (free, no key, ODbL).
 * The export shape is deliberately source-agnostic so a higher-accuracy
 * source (e.g. the Tel Aviv municipality ArcGIS REST layer) can be dropped in
 * later behind the same `fetchBuildings(bbox, origin)` contract.
 *
 *   Building = {
 *     id:       string,
 *     polygon:  [{ x, z }, ...],   // local metres, closed implicitly
 *     centroid: { x, z },
 *     height:   number,            // metres, resolved (see resolveHeight)
 *     levels:   number | null,
 *     name:     string | null,
 *     estimatedHeight: boolean,    // true when height was inferred, not tagged
 *   }
 */
import { llToLocal } from './geo'

const OVERPASS_ENDPOINTS = [
  'https://overpass-api.de/api/interpreter',
  'https://overpass.kumi.systems/api/interpreter',
]

const DEFAULT_HEIGHT = 12          // metres, when nothing is tagged
const METRES_PER_LEVEL = 3.2       // typical residential storey incl. slab

/** Parse an OSM height-ish tag ("12", "12 m", "12.5m") to metres. */
function parseMeters(value) {
  if (value == null) return null
  const m = String(value).match(/-?\d+(\.\d+)?/)
  if (!m) return null
  const n = parseFloat(m[0])
  return Number.isFinite(n) ? n : null
}

/** Resolve a usable height from OSM tags, flagging when it was inferred. */
function resolveHeight(tags) {
  const direct = parseMeters(tags.height) ?? parseMeters(tags['building:height'])
  if (direct != null && direct > 0) return { height: direct, estimated: false }

  const levels =
    parseMeters(tags['building:levels']) ?? parseMeters(tags.levels)
  if (levels != null && levels > 0) {
    return { height: levels * METRES_PER_LEVEL, estimated: true }
  }
  return { height: DEFAULT_HEIGHT, estimated: true }
}

function buildQuery({ south, west, north, east }) {
  const bbox = `${south},${west},${north},${east}`
  return `[out:json][timeout:30];
(
  way["building"](${bbox});
  relation["building"]["type"="multipolygon"](${bbox});
);
out body;
>;
out skel qt;`
}

function polygonCentroid(polygon) {
  // Area-weighted centroid (falls back to vertex mean for degenerate rings).
  let a = 0, cx = 0, cz = 0
  for (let i = 0, n = polygon.length; i < n; i++) {
    const p = polygon[i]
    const q = polygon[(i + 1) % n]
    const cross = p.x * q.z - q.x * p.z
    a += cross
    cx += (p.x + q.x) * cross
    cz += (p.z + q.z) * cross
  }
  if (Math.abs(a) < 1e-9) {
    const m = polygon.reduce((acc, p) => ({ x: acc.x + p.x, z: acc.z + p.z }), { x: 0, z: 0 })
    return { x: m.x / polygon.length, z: m.z / polygon.length }
  }
  a *= 0.5
  return { x: cx / (6 * a), z: cz / (6 * a) }
}

/** Convert a closed ring of node ids → local-metre polygon (drops the dup last vertex). */
function ringToPolygon(nodeIds, nodes, origin) {
  const poly = []
  for (const id of nodeIds) {
    const node = nodes.get(id)
    if (!node) return null
    poly.push(llToLocal(node.lat, node.lon, origin))
  }
  // Overpass closes rings by repeating the first node — drop it.
  if (poly.length > 1) {
    const a = poly[0], b = poly[poly.length - 1]
    if (Math.abs(a.x - b.x) < 1e-6 && Math.abs(a.z - b.z) < 1e-6) poly.pop()
  }
  return poly.length >= 3 ? poly : null
}

function parseOverpass(json, origin) {
  const nodes = new Map()
  const ways = new Map()
  const elements = json.elements || []

  for (const el of elements) {
    if (el.type === 'node') nodes.set(el.id, { lat: el.lat, lon: el.lon })
    else if (el.type === 'way') ways.set(el.id, el)
  }

  const buildings = []

  const makeBuilding = (idKey, ring, tags) => {
    const polygon = ringToPolygon(ring, nodes, origin)
    if (!polygon) return
    const { height, estimated } = resolveHeight(tags || {})
    buildings.push({
      id: idKey,
      polygon,
      centroid: polygonCentroid(polygon),
      height,
      levels: parseMeters((tags || {})['building:levels']),
      name: (tags || {})['name'] || null,
      estimatedHeight: estimated,
    })
  }

  for (const el of elements) {
    if (el.type === 'way' && el.tags && el.tags.building && el.nodes) {
      makeBuilding(`w${el.id}`, el.nodes, el.tags)
    } else if (el.type === 'relation' && el.tags && el.tags.building && el.members) {
      // Multipolygon: emit each outer ring as its own footprint (good enough
      // for corner-picking; inner holes are ignored).
      for (const member of el.members) {
        if (member.type === 'way' && member.role === 'outer') {
          const way = ways.get(member.ref)
          if (way && way.nodes) makeBuilding(`r${el.id}_${member.ref}`, way.nodes, el.tags)
        }
      }
    }
  }

  return buildings
}

/**
 * Fetch building footprints + heights for a lat/lon bbox, returned in the
 * local ground-metres frame relative to `origin`. Tries Overpass mirrors in
 * order until one responds.
 */
export async function fetchBuildings(bbox, origin, { signal } = {}) {
  const query = buildQuery(bbox)
  let lastErr = null
  for (const endpoint of OVERPASS_ENDPOINTS) {
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'data=' + encodeURIComponent(query),
        signal,
      })
      if (!res.ok) { lastErr = new Error(`Overpass ${res.status}`); continue }
      const json = await res.json()
      return parseOverpass(json, origin)
    } catch (err) {
      if (err?.name === 'AbortError') throw err
      lastErr = err
    }
  }
  throw lastErr || new Error('All Overpass endpoints failed')
}

/** Point-in-polygon (ray casting) in the local-metre frame. */
export function pointInPolygon(x, z, polygon) {
  let inside = false
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].x, zi = polygon[i].z
    const xj = polygon[j].x, zj = polygon[j].z
    const intersect =
      (zi > z) !== (zj > z) &&
      x < ((xj - xi) * (z - zi)) / (zj - zi) + xi
    if (intersect) inside = !inside
  }
  return inside
}
