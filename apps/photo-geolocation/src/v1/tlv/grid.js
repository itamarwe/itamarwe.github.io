/**
 * Fixed lat/lon grid used to chunk Overpass fetches into reusable, cacheable
 * cells. A cell is ~0.004° ≈ 440 m (lat) × ~370 m (lon) at Tel Aviv. The grid
 * is anchored to absolute lat/lon (not the local origin), so the same cell key
 * always maps to the same ground patch and the cache stays valid regardless of
 * how the user pans.
 */
export const CELL_DEG = 0.004

export function cellKey(lat, lon) {
  return `${Math.floor(lat / CELL_DEG)}_${Math.floor(lon / CELL_DEG)}`
}

export function cellBounds(key) {
  const [iy, ix] = key.split('_').map(Number)
  return {
    south: iy * CELL_DEG,
    north: (iy + 1) * CELL_DEG,
    west: ix * CELL_DEG,
    east: (ix + 1) * CELL_DEG,
  }
}

/** All cell keys whose extent intersects the given lat/lon bbox. */
export function cellsCoveringBbox({ south, west, north, east }) {
  const keys = []
  const iy0 = Math.floor(south / CELL_DEG)
  const iy1 = Math.floor(north / CELL_DEG)
  const ix0 = Math.floor(west / CELL_DEG)
  const ix1 = Math.floor(east / CELL_DEG)
  for (let iy = iy0; iy <= iy1; iy++) {
    for (let ix = ix0; ix <= ix1; ix++) keys.push(`${iy}_${ix}`)
  }
  return keys
}

/** The cell-aligned bbox that exactly covers a set of cell keys. */
export function unionBounds(keys) {
  let south = Infinity, west = Infinity, north = -Infinity, east = -Infinity
  for (const k of keys) {
    const b = cellBounds(k)
    if (b.south < south) south = b.south
    if (b.west < west) west = b.west
    if (b.north > north) north = b.north
    if (b.east > east) east = b.east
  }
  return { south, west, north, east }
}
