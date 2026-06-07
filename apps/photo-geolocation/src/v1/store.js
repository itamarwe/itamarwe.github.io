import { create } from 'zustand'
import { nextAnchorColor } from '../shared/utils/anchors'
import { photoState } from './photoState'
import { ESTIMATORS } from './pose/registry'
import { DEFAULT_ORIGIN, localToLl } from './tlv/geo'
import { fetchBuildings, pointInPolygon } from './tlv/buildings'
import { cellKey, cellsCoveringBbox, unionBounds } from './tlv/grid'
import { getCells, putCells } from './tlv/cache'
import { peekElevation, getElevation, prefetchElevation } from './tlv/elevation'

const DEFAULT_RADIUS_M = 500

// Cap on how many uncached grid cells a single viewport fetch may pull. When
// zoomed too far out the visible area covers more cells than this — we skip
// the auto-fetch and ask the user to zoom in rather than firing a huge
// Overpass query. ~24 cells ≈ a 2 km × 2 km window.
const MAX_CELLS_PER_FETCH = 24

// Cells currently being fetched, tracked outside the store so concurrent
// viewport changes don't re-request the same patch (and don't trigger
// re-renders just for in-flight bookkeeping).
const inFlightCells = new Set()

function makeAnchor(nextAnchorId, anchors) {
  return {
    id: nextAnchorId,
    color: nextAnchorColor(anchors, nextAnchorId),
    photoPixel: null,
    mapPoint: null,    // { x, y, z } once placed; y auto-filled from building footprint
  }
}

/**
 * Structure height above local ground at a (x, z) map click: inside any
 * building footprint → that building's height (rooftop click); otherwise → 0
 * (ground click). This is the part the user clicked *above the ground*; the
 * terrain elevation is added separately so the solver's world y is the point's
 * true elevation above sea level.
 */
function inferStructureHeight(x, z, buildings) {
  // A point can fall inside several overlapping footprints; pick the tallest.
  let h = 0
  for (const b of buildings) {
    if (pointInPolygon(x, z, b.polygon) && b.height > h) h = b.height
  }
  return h
}

/**
 * Build the full mapPoint for a (x, z) click. World y is the point's true
 * elevation in metres above sea level: terrain elevation (from the DEM) plus
 * the structure height clicked above local ground. Using absolute ASL means
 * the solve needs no separate "origin elevation" datum — only the *relative*
 * terrain between anchors matters to PnP, and that's preserved. The camera's
 * solved height then comes out as its own elevation ASL.
 *
 * groundEle may be null when the terrain tile isn't cached yet; y then falls
 * back to the structure height alone and setAnchorMapPoint async-corrects it.
 */
function buildMapPoint(x, z, buildings, origin) {
  const structureY = inferStructureHeight(x, z, buildings)
  const ll = localToLl(x, z, origin)
  const groundEle = peekElevation(ll.lat, ll.lon)
  return { x, z, structureY, groundEle, y: structureY + (groundEle ?? 0) }
}

export const useStore = create((set, get) => ({
  // Tel Aviv map state ------------------------------------------------------
  origin: DEFAULT_ORIGIN,            // local-frame reference lat/lon (fixed)
  radiusMeters: DEFAULT_RADIUS_M,    // initial framing half-extent
  buildings: [],                     // merged polygon footprints in local metres
  loadedCells: new Set(),            // grid cells already loaded (this session)
  buildingsLoading: false,
  buildingsError: null,
  buildingsLoadedAt: null,

  anchors: [],
  activeAnchorId: null,
  nextAnchorId: 1,
  enabledEstimators: new Set(ESTIMATORS.map((e) => e.id)),
  image: photoState.image,
  captureVersion: 1,

  // Uploaded real-world photo (TLV geolocation flow). photoUrl is an object
  // URL for the user-selected file; when set, the photo pane shows the image
  // instead of the synthetic 3D scene. image.width/height become the photo's
  // natural pixel dimensions so photoPixel coords and the assumed principal
  // point (width/2) line up with the real sensor.
  photoUrl: null,
  photoName: null,

  // True once the user has made work-bearing changes (placed/edited anchors,
  // toggled estimators) since the current photo was loaded, a session was
  // loaded, or the session was saved. Drives the "you'll lose your work"
  // confirmation when removing the photo.
  dirty: false,

  /**
   * Adopt an uploaded photo. Sets the object URL + natural pixel dimensions,
   * clears any photo-side anchor placements (map anchors are kept so the user
   * can re-pick the same corners on the new image), and bumps captureVersion
   * so the map auto-fit / estimators recompute.
   */
  setPhoto: (url, width, height, name) => set((state) => {
    if (state.photoUrl && state.photoUrl !== url) {
      try { URL.revokeObjectURL(state.photoUrl) } catch { /* ignore */ }
    }
    const w = Math.max(1, Math.round(width))
    const h = Math.max(1, Math.round(height))
    const image = { width: w, height: h }
    photoState.image = image
    return {
      photoUrl: url,
      photoName: name ?? null,
      image,
      mode: 'view',
      anchors: state.anchors.map((a) => ({ ...a, photoPixel: null })),
      activeAnchorId: null,
      dirty: false,
      captureVersion: state.captureVersion + 1,
    }
  }),

  clearPhoto: () => set((state) => {
    if (state.photoUrl) {
      try { URL.revokeObjectURL(state.photoUrl) } catch { /* ignore */ }
    }
    return {
      photoUrl: null,
      photoName: null,
      // Removing the photo discards all anchors — they only make sense paired
      // with the photo they were placed against.
      anchors: [],
      activeAnchorId: null,
      nextAnchorId: 1,
      dirty: false,
    }
  }),

  /**
   * Restore a session previously produced by SessionControls' save. The saved
   * photo travels as a self-contained data URL (so the file is portable), which
   * works directly as an <img> src and for re-decoding. Everything needed to
   * reproduce the work is restored: the photo + its pixel dimensions, every
   * anchor (photo pixel + map point with structureY/groundEle/y), the enabled
   * estimators, and the map origin/framing. Bumps captureVersion so the map
   * auto-fits and estimators recompute.
   */
  loadSession: (session) => set((state) => {
    if (!session || typeof session !== 'object') return {}
    if (state.photoUrl && state.photoUrl !== session.photo) {
      try { URL.revokeObjectURL(state.photoUrl) } catch { /* ignore */ }
    }
    const img = session.image
    const image = img && Number.isFinite(img.width) && Number.isFinite(img.height)
      ? { width: Math.max(1, Math.round(img.width)), height: Math.max(1, Math.round(img.height)) }
      : state.image
    photoState.image = image

    const anchors = Array.isArray(session.anchors) ? session.anchors : []
    const maxId = anchors.reduce((m, a) => Math.max(m, a?.id || 0), 0)
    const enabled = Array.isArray(session.enabledEstimators)
      ? new Set(session.enabledEstimators)
      : state.enabledEstimators

    return {
      origin: session.origin ?? state.origin,
      radiusMeters: Number.isFinite(session.radiusMeters) ? session.radiusMeters : state.radiusMeters,
      anchors,
      activeAnchorId: session.activeAnchorId ?? null,
      nextAnchorId: Number.isFinite(session.nextAnchorId) ? session.nextAnchorId : maxId + 1,
      enabledEstimators: enabled,
      image,
      photoUrl: session.photo ?? null,
      photoName: session.photoName ?? null,
      dirty: false,
      captureVersion: state.captureVersion + 1,
    }
  }),

  /** Called after a successful session save — the current state is now persisted. */
  markSaved: () => set({ dirty: false }),

  /**
   * Ensure building footprints are loaded for every grid cell intersecting the
   * given lat/lon bbox (typically the current map viewport). Cells already
   * loaded this session, or in flight, are skipped. Missing cells are served
   * from the IndexedDB cache where possible; the remainder are fetched from
   * Overpass in a single cell-aligned request, partitioned back into per-cell
   * cache entries by building centroid, and merged into `buildings` (deduped
   * by id). The local-frame origin never moves, so anchors stay valid.
   */
  ensureAreaLoaded: async (bbox) => {
    const state = get()
    const origin = state.origin

    // Warm terrain tiles for the viewport (cheap, capped) so anchor placement
    // and the cursor readout can read ground elevation synchronously.
    prefetchElevation(bbox)

    const cells = cellsCoveringBbox(bbox)
    const missing = cells.filter((k) => !state.loadedCells.has(k) && !inFlightCells.has(k))
    if (missing.length === 0) return

    if (missing.length > MAX_CELLS_PER_FETCH) {
      set({ buildingsError: 'Zoom in to load buildings' })
      return
    }

    missing.forEach((k) => inFlightCells.add(k))
    set({ buildingsLoading: true, buildingsError: null })
    try {
      const cached = await getCells(origin, missing)
      const toFetch = missing.filter((k) => cached[k] === undefined)

      let fetched = []
      if (toFetch.length > 0) {
        fetched = await fetchBuildings(unionBounds(toFetch), origin)
        // Partition fetched buildings into their centroid's cell so the cache
        // is keyed consistently. Cells with no buildings are cached as [] so
        // we never re-query an empty patch.
        const writes = {}
        for (const k of toFetch) writes[k] = []
        for (const b of fetched) {
          const ll = localToLl(b.centroid.x, b.centroid.z, origin)
          const k = cellKey(ll.lat, ll.lon)
          if (writes[k]) writes[k].push(b)
        }
        putCells(origin, writes) // fire-and-forget persistence
      }

      const incoming = fetched.concat(
        ...Object.keys(cached).map((k) => cached[k]),
      )

      set((s) => {
        const byId = new Map(s.buildings.map((b) => [b.id, b]))
        for (const b of incoming) byId.set(b.id, b)
        const nextLoaded = new Set(s.loadedCells)
        missing.forEach((k) => nextLoaded.add(k))
        return {
          buildings: [...byId.values()],
          loadedCells: nextLoaded,
          buildingsLoading: false,
          buildingsError: null,
          buildingsLoadedAt: Date.now(),
        }
      })
    } catch (err) {
      set({ buildingsLoading: false, buildingsError: err?.message || String(err) })
    } finally {
      missing.forEach((k) => inFlightCells.delete(k))
    }
  },

  addAnchor: () => set((state) => {
    // Anchors only make sense against a loaded photo.
    if (!state.photoUrl) return {}
    const anchor = makeAnchor(state.nextAnchorId, state.anchors)
    return {
      anchors: [...state.anchors, anchor],
      activeAnchorId: anchor.id,
      nextAnchorId: state.nextAnchorId + 1,
      dirty: true,
    }
  }),

  removeAnchor: (id) => set((state) => ({
    anchors: state.anchors.filter((a) => a.id !== id),
    activeAnchorId: state.activeAnchorId === id ? null : state.activeAnchorId,
    dirty: true,
  })),

  clearAnchors: () => set({ anchors: [], activeAnchorId: null, nextAnchorId: 1, dirty: true }),

  setActiveAnchor: (id) => set((state) => ({
    activeAnchorId: state.activeAnchorId === id ? null : id,
  })),

  setAnchorPhotoPixel: (id, photoPixel) => set((state) => ({
    anchors: state.anchors.map((a) => (a.id === id ? { ...a, photoPixel } : a)),
    dirty: true,
  })),

  /**
   * Set an anchor's map point. When the caller didn't supply y (the typical
   * case — Map2D produces {x, z} from a 2D click), build the full point:
   * structure height from the footprint + terrain offset from the DEM, so
   * world y is a true height above the origin's ground. If the terrain tile
   * wasn't cached at click time (groundEle null), fetch it and correct y.
   */
  setAnchorMapPoint: (id, mapPoint) => {
    const state = get()
    let mp = mapPoint
    const needsBuild = mp && (mp.y === undefined || mp.y === null)
    if (needsBuild) {
      mp = buildMapPoint(mp.x, mp.z, state.buildings, state.origin)
    }
    set((s) => ({
      anchors: s.anchors.map((a) => (a.id === id ? { ...a, mapPoint: mp } : a)),
      dirty: true,
    }))

    // Async-fill the terrain elevation if its tile wasn't cached at click time.
    if (needsBuild && mp.groundEle == null) {
      const ll = localToLl(mp.x, mp.z, state.origin)
      getElevation(ll.lat, ll.lon).then((ele) => {
        if (ele == null) return
        set((s) => ({
          anchors: s.anchors.map((a) => {
            if (a.id !== id || !a.mapPoint) return a
            return { ...a, mapPoint: { ...a.mapPoint, groundEle: ele, y: (a.mapPoint.structureY ?? 0) + ele } }
          }),
        }))
      })
    }
  },

  /**
   * Override the structure height (metres above local ground) for an anchor —
   * e.g. when the click was the base, the eaves, or a facade point rather than
   * the rooftop. World y (elevation ASL) is the structure height plus the
   * anchor's terrain elevation.
   */
  setAnchorMapPointY: (id, structureY) => set((state) => ({
    anchors: state.anchors.map((a) => {
      if (a.id !== id || !a.mapPoint) return a
      const mp = a.mapPoint
      return { ...a, mapPoint: { ...mp, structureY, y: structureY + (mp.groundEle ?? 0) } }
    }),
    dirty: true,
  })),

  toggleEstimator: (id) => set((state) => {
    const next = new Set(state.enabledEstimators)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    return { enabledEstimators: next, dirty: true }
  }),
}))
