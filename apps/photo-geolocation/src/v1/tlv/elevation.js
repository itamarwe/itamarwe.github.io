/**
 * Terrain elevation for the Tel Aviv geolocation flow.
 *
 * OpenStreetMap has no ground-elevation surface, so terrain comes from the
 * free, key-less AWS "Terrarium" terrain-RGB raster tiles (registry of open
 * data, CORS-enabled so pixels are readable client-side). Each tile is a PNG
 * where every pixel encodes metres above sea level:
 *
 *     elevation = (R * 256 + G + B / 256) - 32768
 *
 * Tiles are decoded to a Float32 elevation grid once and cached in memory,
 * exactly like the basemap raster tiles — so a single fetch serves unlimited
 * point samples (the live cursor readout, every anchor) with no API limits.
 *
 * Underlying data is SRTM/NED (~30 m); at z=14 a pixel is finer than that, so
 * we bilinearly sample, which is plenty for TLV's gentle terrain.
 */
import { lonToTileX, latToTileY } from './geo'

const ELEV_ZOOM = 14
const TERRARIUM_URL = (z, x, y) =>
  `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/${z}/${x}/${y}.png`
const TILE_PX = 256

// Cap a single prefetch so a zoomed-out viewport can't fire a huge tile burst.
const MAX_PREFETCH_TILES = 16

// tileKey → { state: 'loading'|'ready'|'error', data: Float32Array|null, promise }
const tiles = new Map()

let scratch = null
function decodeTile(img) {
  if (!scratch) {
    scratch = document.createElement('canvas')
    scratch.width = TILE_PX
    scratch.height = TILE_PX
  }
  const cx = scratch.getContext('2d', { willReadFrequently: true })
  cx.clearRect(0, 0, TILE_PX, TILE_PX)
  cx.drawImage(img, 0, 0, TILE_PX, TILE_PX)
  const px = cx.getImageData(0, 0, TILE_PX, TILE_PX).data
  const out = new Float32Array(TILE_PX * TILE_PX)
  for (let i = 0, j = 0; i < out.length; i++, j += 4) {
    out[i] = px[j] * 256 + px[j + 1] + px[j + 2] / 256 - 32768
  }
  return out
}

function loadTile(z, x, y) {
  const key = `${z}/${x}/${y}`
  const existing = tiles.get(key)
  if (existing) return existing.promise
  const entry = { state: 'loading', data: null, promise: null }
  entry.promise = new Promise((resolve) => {
    if (typeof Image === 'undefined') { entry.state = 'error'; return resolve(entry) }
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      try { entry.data = decodeTile(img); entry.state = 'ready' }
      catch { entry.state = 'error' }
      resolve(entry)
    }
    img.onerror = () => { entry.state = 'error'; resolve(entry) }
    img.src = TERRARIUM_URL(z, x, y)
  })
  tiles.set(key, entry)
  return entry.promise
}

/** Bilinear sample of a ready tile's grid at fractional pixel (fx, fy ∈ [0,1)). */
function sample(entry, fx, fy) {
  const X = Math.min(TILE_PX - 1, Math.max(0, fx * TILE_PX - 0.5))
  const Y = Math.min(TILE_PX - 1, Math.max(0, fy * TILE_PX - 0.5))
  const x0 = Math.floor(X), y0 = Math.floor(Y)
  const x1 = Math.min(TILE_PX - 1, x0 + 1), y1 = Math.min(TILE_PX - 1, y0 + 1)
  const tx = X - x0, ty = Y - y0
  const d = entry.data
  const a = d[y0 * TILE_PX + x0], b = d[y0 * TILE_PX + x1]
  const c = d[y1 * TILE_PX + x0], e = d[y1 * TILE_PX + x1]
  return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + e * tx) * ty
}

function tileFor(lat, lon) {
  const tx = lonToTileX(lon, ELEV_ZOOM)
  const ty = latToTileY(lat, ELEV_ZOOM)
  const ix = Math.floor(tx), iy = Math.floor(ty)
  return { ix, iy, fx: tx - ix, fy: ty - iy, key: `${ELEV_ZOOM}/${ix}/${iy}` }
}

/**
 * Synchronous elevation (metres ASL) from already-cached tiles, or null if the
 * covering tile isn't loaded yet. For the live cursor readout / synchronous
 * anchor placement — call prefetchElevation first to warm the area.
 */
export function peekElevation(lat, lon) {
  const { fx, fy, key } = tileFor(lat, lon)
  const entry = tiles.get(key)
  if (!entry || entry.state !== 'ready') return null
  return sample(entry, fx, fy)
}

/** Elevation (metres ASL), loading the covering tile if needed. null on failure. */
export async function getElevation(lat, lon) {
  const { fx, fy, ix, iy } = tileFor(lat, lon)
  const entry = await loadTile(ELEV_ZOOM, ix, iy)
  if (entry.state !== 'ready') return null
  return sample(entry, fx, fy)
}

/** Warm every terrain tile covering a lat/lon bbox so peekElevation works there. */
export function prefetchElevation({ south, west, north, east }) {
  const x0 = Math.floor(lonToTileX(west, ELEV_ZOOM))
  const x1 = Math.floor(lonToTileX(east, ELEV_ZOOM))
  const y0 = Math.floor(latToTileY(north, ELEV_ZOOM))
  const y1 = Math.floor(latToTileY(south, ELEV_ZOOM))
  const count = (x1 - x0 + 1) * (y1 - y0 + 1)
  if (count > MAX_PREFETCH_TILES || count < 1) return
  for (let x = x0; x <= x1; x++) {
    for (let y = y0; y <= y1; y++) loadTile(ELEV_ZOOM, x, y)
  }
}
