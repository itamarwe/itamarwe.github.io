import { useEffect, useMemo, useRef, useState } from 'react'
import { useStore } from '../store'
import { poseState } from '../poseState'
import { ESTIMATORS } from '../pose/registry'
import { buildObservations, wrapAngle } from '../pose/algorithms'
import {
  llToLocal, localToLl, latToTileY, lonToTileX, tileXToLon, tileYToLat, bboxAround,
} from '../tlv/geo'
import { pointInPolygon } from '../tlv/buildings'
import { peekElevation } from '../tlv/elevation'

/**
 * Structure height at a local (x, z) point: the first building footprint
 * containing it → that building (rooftop height), else ground (0 m). Heights
 * are real-world structure heights above local ground (metres), matching what
 * an anchor placed there would receive.
 */
function heightAt(x, z, buildings) {
  // A point can fall inside several overlapping footprints; pick the tallest.
  let tallest = null
  for (const b of buildings) {
    if (pointInPolygon(x, z, b.polygon) && (!tallest || b.height > tallest.height)) {
      tallest = b
    }
  }
  return tallest ? { height: tallest.height, building: tallest } : { height: 0, building: null }
}

/** Structure-height portion of the cursor readout's second line. */
function readoutHeightLabel(r) {
  if (r.onBuilding) return `▲ ${Math.round(r.height)} m${r.estimated ? ' (est.)' : ''}`
  return 'ground'
}

const DPR = typeof window === 'undefined' ? 1 : Math.max(1, window.devicePixelRatio || 1)

// CARTO Voyager raster basemap (free for dev use, shows street names). Drawn
// underneath the building footprints in the same local-metres transform.
const TILE_SUBDOMAINS = ['a', 'b', 'c', 'd']
const tileUrl = (z, x, y) =>
  `https://${TILE_SUBDOMAINS[(x + y) % TILE_SUBDOMAINS.length]}.basemaps.cartocdn.com/rastertiles/voyager/${z}/${x}/${y}.png`

// Module-level tile image cache so pan/zoom doesn't refetch.
const tileCache = new Map()
function getTile(z, x, y) {
  const key = `${z}/${x}/${y}`
  let img = tileCache.get(key)
  if (!img) {
    img = new Image()
    img.crossOrigin = 'anonymous'
    img.src = tileUrl(z, x, y)
    tileCache.set(key, img)
  }
  return img
}

function makeTransform(width, height, view, worldHalf) {
  const scale = (Math.min(width, height) / (worldHalf * 2)) * 0.88 * view.zoom
  const cx = width / 2
  const cy = height / 2
  return {
    scale,
    toCanvas: (wx, wz) => ({
      x: cx + (wx - view.centerX) * scale + view.panX,
      y: cy + (wz - view.centerZ) * scale + view.panY,
    }),
    toWorld: (px, py) => ({
      x: (px - cx - view.panX) / scale + view.centerX,
      z: (py - cy - view.panY) / scale + view.centerZ,
    }),
  }
}

/** Current visible canvas extent as a WGS84 lat/lon bbox. */
function visibleBbox(width, height, view, worldHalf, origin) {
  if (!(width > 0) || !(height > 0)) return null
  const { toWorld } = makeTransform(width, height, view, worldHalf)
  const a = toWorld(0, 0)
  const b = toWorld(width, height)
  const c0 = localToLl(Math.min(a.x, b.x), Math.min(a.z, b.z), origin)
  const c1 = localToLl(Math.max(a.x, b.x), Math.max(a.z, b.z), origin)
  return {
    south: Math.min(c0.lat, c1.lat),
    north: Math.max(c0.lat, c1.lat),
    west: Math.min(c0.lon, c1.lon),
    east: Math.max(c0.lon, c1.lon),
  }
}

/**
 * Frame the loaded buildings (+ any placed anchors) inside the central `fit`
 * fraction of the canvas. Falls back to a ±worldHalf box around the origin
 * when nothing is loaded yet.
 */
function computeAutoFit(buildings, anchors, cssWidth, cssHeight, worldHalf, fit = 0.82) {
  const pts = []
  for (const b of buildings || []) {
    for (const p of b.polygon) pts.push(p)
  }
  for (const a of anchors || []) {
    if (a.mapPoint) pts.push({ x: a.mapPoint.x, z: a.mapPoint.z })
  }
  const baseScale = (Math.min(cssWidth, cssHeight) / (worldHalf * 2)) * 0.88
  if (pts.length === 0 || cssWidth <= 0 || cssHeight <= 0) {
    return { centerX: 0, centerZ: 0, zoom: 1, panX: 0, panY: 0 }
  }
  let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity
  for (const p of pts) {
    if (p.x < minX) minX = p.x
    if (p.x > maxX) maxX = p.x
    if (p.z < minZ) minZ = p.z
    if (p.z > maxZ) maxZ = p.z
  }
  const bboxW = Math.max(1e-3, maxX - minX)
  const bboxH = Math.max(1e-3, maxZ - minZ)
  const requiredScale = Math.min((fit * cssWidth) / bboxW, (fit * cssHeight) / bboxH)
  return {
    centerX: (minX + maxX) / 2,
    centerZ: (minZ + maxZ) / 2,
    zoom: requiredScale / baseScale,
    panX: 0,
    panY: 0,
  }
}

/**
 * Draw CARTO raster tiles covering the visible canvas. Tiles are Web-Mercator
 * squares; we place each by converting its lat/lon bounds to local metres
 * (an axis-aligned rect, since lon→x and lat→z are linear & independent), so
 * tiles register exactly with the footprint polygons.
 */
function drawTiles(ctx, width, height, view, worldHalf, origin, toCanvas) {
  const { toWorld } = makeTransform(width, height, view, worldHalf)
  const scale = (Math.min(width, height) / (worldHalf * 2)) * 0.88 * view.zoom

  // Choose a tile zoom so one tile-pixel ≈ one screen-pixel at this scale.
  const groundMPP = 1 / scale // metres per screen pixel
  const merc = 156543.03392 * Math.cos((origin.lat * Math.PI) / 180)
  let z = Math.round(Math.log2(merc / groundMPP))
  z = Math.max(14, Math.min(19, z))

  // Visible bounds in lat/lon (note z grows southward, so top-left of canvas
  // is min-z → max-lat).
  const tl = toWorld(0, 0)
  const br = toWorld(width, height)
  const nw = localToLl(Math.min(tl.x, br.x), Math.min(tl.z, br.z), origin)
  const se = localToLl(Math.max(tl.x, br.x), Math.max(tl.z, br.z), origin)

  const n = Math.pow(2, z)
  const xStart = Math.max(0, Math.floor(lonToTileX(nw.lon, z)))
  const xEnd = Math.min(n - 1, Math.floor(lonToTileX(se.lon, z)))
  const yStart = Math.max(0, Math.floor(latToTileY(nw.lat, z)))
  const yEnd = Math.min(n - 1, Math.floor(latToTileY(se.lat, z)))

  // Guard against pathological ranges (e.g. before first layout).
  if ((xEnd - xStart) * (yEnd - yStart) > 400) return

  for (let tx = xStart; tx <= xEnd; tx++) {
    for (let ty = yStart; ty <= yEnd; ty++) {
      const lonW = tileXToLon(tx, z)
      const lonE = tileXToLon(tx + 1, z)
      const latN = tileYToLat(ty, z)
      const latS = tileYToLat(ty + 1, z)
      const a = llToLocal(latN, lonW, origin) // north-west → min z, min x
      const b = llToLocal(latS, lonE, origin) // south-east → max z, max x
      const p0 = toCanvas(a.x, a.z)
      const p1 = toCanvas(b.x, b.z)
      const img = getTile(z, tx, ty)
      if (img.complete && img.naturalWidth > 0) {
        ctx.drawImage(img, p0.x, p0.y, p1.x - p0.x, p1.y - p0.y)
      }
    }
  }
}

function drawBuildings(ctx, buildings, toCanvas, activeAnchorId) {
  for (const b of buildings) {
    if (!b.polygon || b.polygon.length < 3) continue
    ctx.beginPath()
    b.polygon.forEach((p, i) => {
      const c = toCanvas(p.x, p.z)
      if (i === 0) ctx.moveTo(c.x, c.y)
      else ctx.lineTo(c.x, c.y)
    })
    ctx.closePath()
    // Tint by height: taller = warmer/darker so the user gets a height cue.
    const t = Math.max(0, Math.min(1, b.height / 60))
    const hue = 30 - t * 30
    const light = 62 - t * 22
    ctx.fillStyle = `hsla(${hue}, 55%, ${light}%, 0.55)`
    ctx.fill()
    ctx.strokeStyle = b.estimatedHeight ? 'rgba(140,90,40,0.7)' : 'rgba(120,60,20,0.9)'
    ctx.lineWidth = 1
    ctx.stroke()
  }
}

function drawAnchors(ctx, anchors, activeAnchorId, toCanvas) {
  anchors.forEach((a) => {
    if (!a.mapPoint) return
    const { x, y } = toCanvas(a.mapPoint.x, a.mapPoint.z)
    const isActive = a.id === activeAnchorId
    if (isActive) {
      ctx.beginPath()
      ctx.arc(x, y, 15, 0, Math.PI * 2)
      ctx.fillStyle = `${a.color}33`
      ctx.fill()
    }
    ctx.beginPath()
    ctx.arc(x, y, 9, 0, Math.PI * 2)
    ctx.fillStyle = a.color
    ctx.fill()
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = 2
    ctx.stroke()
    ctx.fillStyle = 'white'
    ctx.font = 'bold 11px monospace'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(String(a.id), x, y + 0.5)
  })
}

function drawEstimatorShape(ctx, shape, x, y, r, color) {
  ctx.save()
  ctx.lineWidth = 2.5
  ctx.strokeStyle = color
  ctx.fillStyle = `${color}40`
  ctx.beginPath()
  if (shape === 'square') ctx.rect(x - r, y - r, r * 2, r * 2)
  else if (shape === 'diamond') {
    ctx.moveTo(x, y - r); ctx.lineTo(x + r, y); ctx.lineTo(x, y + r); ctx.lineTo(x - r, y); ctx.closePath()
  } else if (shape === 'triangle') {
    ctx.moveTo(x, y - r); ctx.lineTo(x + r * 0.87, y + r * 0.5); ctx.lineTo(x - r * 0.87, y + r * 0.5); ctx.closePath()
  } else ctx.arc(x, y, r, 0, Math.PI * 2)
  ctx.fill()
  ctx.stroke()
  ctx.restore()
}

function drawFovTriangle(ctx, toCanvas, estimate, color) {
  if (!Number.isFinite(estimate.heading) || !Number.isFinite(estimate.fov)) return
  const len = 26
  const half = (estimate.fov * Math.PI / 180) / 2
  const p0 = toCanvas(estimate.px, estimate.pz)
  const p1 = toCanvas(estimate.px + Math.sin(estimate.heading - half) * len, estimate.pz - Math.cos(estimate.heading - half) * len)
  const p2 = toCanvas(estimate.px + Math.sin(estimate.heading + half) * len, estimate.pz - Math.cos(estimate.heading + half) * len)
  ctx.save()
  ctx.beginPath()
  ctx.moveTo(p0.x, p0.y); ctx.lineTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.closePath()
  ctx.fillStyle = `${color}1f`
  ctx.strokeStyle = `${color}aa`
  ctx.lineWidth = 1.5
  ctx.fill()
  ctx.stroke()
  ctx.restore()
}

/**
 * Run every estimator over the (photo↔map) correspondences. Real photos have
 * no ground-truth camera, so instead of error metrics we attach the estimated
 * WGS84 lat/lon of the camera for display. Results are computed for all
 * estimators regardless of the enabled toggle — toggling only hides the map
 * visualization, the panel keeps showing each estimate's numbers.
 */
function computeEstimatorResults(anchors, image, origin) {
  const observations = buildObservations(anchors)
  const ctx = { photoWidth: image.width, photoHeight: image.height }
  const out = {}

  for (const estimator of ESTIMATORS) {
    if (observations.length < estimator.minAnchors) {
      out[estimator.id] = null
      continue
    }
    let result = null
    try { result = estimator.fn(observations, ctx) } catch { result = null }
    if (!result) { out[estimator.id] = null; continue }
    const ll = Number.isFinite(result.px) && Number.isFinite(result.pz)
      ? localToLl(result.px, result.pz, origin)
      : { lat: NaN, lon: NaN }
    out[estimator.id] = {
      ...result,
      lat: ll.lat,
      lon: ll.lon,
      headingDeg: Number.isFinite(result.heading) ? (wrapAngle(result.heading) * 180 / Math.PI) : NaN,
      // result.py is the solved camera world y. Anchors carry absolute ASL
      // heights, so the camera's height comes out as its elevation ASL.
      elevation: Number.isFinite(result.py) ? result.py : NaN,
    }
  }
  return out
}

function anchorAtPixel(anchors, px, py, width, height, view, worldHalf) {
  const { toCanvas } = makeTransform(width, height, view, worldHalf)
  for (let i = anchors.length - 1; i >= 0; i--) {
    const anchor = anchors[i]
    if (!anchor.mapPoint) continue
    const p = toCanvas(anchor.mapPoint.x, anchor.mapPoint.z)
    const dx = px - p.x
    const dy = py - p.y
    if (dx * dx + dy * dy < 14 * 14) return anchor
  }
  return null
}

export default function Map2D() {
  const canvasRef = useRef(null)
  const anchors = useStore((s) => s.anchors)
  const activeAnchorId = useStore((s) => s.activeAnchorId)
  const buildings = useStore((s) => s.buildings)
  const enabledEstimators = useStore((s) => s.enabledEstimators)
  const setAnchorMapPoint = useStore((s) => s.setAnchorMapPoint)
  const image = useStore((s) => s.image)
  const origin = useStore((s) => s.origin)
  const radiusMeters = useStore((s) => s.radiusMeters)
  const buildingsLoading = useStore((s) => s.buildingsLoading)
  const buildingsError = useStore((s) => s.buildingsError)
  const ensureAreaLoaded = useStore((s) => s.ensureAreaLoaded)
  const captureVersion = useStore((s) => s.captureVersion)

  const worldHalf = Math.max(50, radiusMeters)

  const estimates = useMemo(
    () => computeEstimatorResults(anchors, image, origin),
    [anchors, image, origin, captureVersion]
  )
  const estimatesRef = useRef(estimates)
  useEffect(() => {
    estimatesRef.current = estimates
    poseState.estimates = estimates
  }, [estimates])

  const dragRef = useRef({ id: null })
  const panRef = useRef({ active: false, startX: 0, startY: 0, panX: 0, panY: 0, moved: false, pointerId: null })
  const viewRef = useRef({ centerX: 0, centerZ: 0, panX: 0, panY: 0, zoom: 1 })
  const autoFitKeyRef = useRef(null)
  const loadTimerRef = useRef(0)
  const [cursor, setCursor] = useState('default')
  const [readout, setReadout] = useState(null)  // { lat, lon, height, onBuilding, estimated }

  // Fetch buildings for whatever the map currently shows, debounced so a pan
  // or zoom gesture only triggers one request once it settles. Cells already
  // loaded/cached are no-ops inside ensureAreaLoaded, so this is cheap to call
  // liberally.
  const scheduleViewportLoad = (delay = 350) => {
    clearTimeout(loadTimerRef.current)
    loadTimerRef.current = setTimeout(() => {
      const canvas = canvasRef.current
      if (!canvas) return
      const bbox = visibleBbox(canvas.clientWidth, canvas.clientHeight, viewRef.current, worldHalf, origin)
      if (bbox) ensureAreaLoaded(bbox)
    }, delay)
  }
  // Stable handle so the native (effect-scoped) wheel listener always calls the
  // latest loader without being torn down on every render.
  const loaderRef = useRef(scheduleViewportLoad)
  loaderRef.current = scheduleViewportLoad

  // Initial load: guarantee a central-TLV area regardless of canvas timing,
  // then let viewport-driven loads take over.
  useEffect(() => {
    ensureAreaLoaded(bboxAround(origin, radiusMeters))
    return () => clearTimeout(loadTimerRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Dev-only imperative hooks for the scripted demo recorder (mirrors the
  // window.__store hook in main.jsx). The render loop reads viewRef every
  // frame, so set() animates live. Stripped from production builds.
  useEffect(() => {
    if (!import.meta.env?.DEV) return undefined
    window.__mapView = {
      get: () => ({ ...viewRef.current }),
      set: (v) => { viewRef.current = { ...viewRef.current, ...v } },
      canvasRect: () => canvasRef.current?.getBoundingClientRect() ?? null,
      worldHalf: () => Math.max(50, useStore.getState().radiusMeters),
      // Structure height at a local point (0 ⇒ no footprint loaded/here yet).
      heightAt: (x, z) => {
        let h = 0
        for (const b of useStore.getState().buildings) {
          if (pointInPolygon(x, z, b.polygon) && b.height > h) h = b.height
        }
        return h
      },
      // A small lat/lon bbox around a local point, for ensureAreaLoaded.
      llBboxAround: (x, z, half = 300) => {
        const origin = useStore.getState().origin
        const a = localToLl(x - half, z - half, origin)
        const b = localToLl(x + half, z + half, origin)
        return {
          south: Math.min(a.lat, b.lat), north: Math.max(a.lat, b.lat),
          west: Math.min(a.lon, b.lon), east: Math.max(a.lon, b.lon),
        }
      },
      // Lat/lon bbox covering a local min/max rectangle (one Overpass request).
      llRect: (minX, minZ, maxX, maxZ) => {
        const origin = useStore.getState().origin
        const a = localToLl(minX, minZ, origin)
        const b = localToLl(maxX, maxZ, origin)
        return {
          south: Math.min(a.lat, b.lat), north: Math.max(a.lat, b.lat),
          west: Math.min(a.lon, b.lon), east: Math.max(a.lon, b.lon),
        }
      },
      // Solved camera position (local x,z) of the first estimator with a result.
      cameraPoint: () => {
        for (const e of ESTIMATORS) {
          const r = poseState.estimates?.[e.id]
          if (r && Number.isFinite(r.px) && Number.isFinite(r.pz)) {
            return { x: r.px, z: r.pz, id: e.id, headingDeg: r.headingDeg }
          }
        }
        return null
      },
    }
    return () => { try { delete window.__mapView } catch { /* ignore */ } }
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    let frameId = 0

    const tick = () => {
      const rect = canvas.getBoundingClientRect()
      const cssWidth = rect.width
      const cssHeight = rect.height
      const pixelWidth = Math.round(cssWidth * DPR)
      const pixelHeight = Math.round(cssHeight * DPR)
      if (canvas.width !== pixelWidth) canvas.width = pixelWidth
      if (canvas.height !== pixelHeight) canvas.height = pixelHeight

      // Auto-fit only on first layout / resize — NOT when buildings stream in
      // from a viewport load, otherwise the user's pan/zoom would snap back
      // every time a new area arrives.
      const fitKey = `${Math.round(cssWidth)}x${Math.round(cssHeight)}`
      if (autoFitKeyRef.current !== fitKey && cssWidth > 0 && cssHeight > 0) {
        viewRef.current = computeAutoFit(buildings, anchors, cssWidth, cssHeight, worldHalf)
        autoFitKeyRef.current = fitKey
      }

      const ctx = canvas.getContext('2d')
      ctx.setTransform(1, 0, 0, 1, 0, 0)
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0)
      ctx.fillStyle = '#e8e6e1'
      ctx.fillRect(0, 0, cssWidth, cssHeight)

      const { toCanvas } = makeTransform(cssWidth, cssHeight, viewRef.current, worldHalf)
      drawTiles(ctx, cssWidth, cssHeight, viewRef.current, worldHalf, origin, toCanvas)
      drawBuildings(ctx, buildings, toCanvas, activeAnchorId)

      const currentEstimates = estimatesRef.current
      for (const estimator of ESTIMATORS) {
        if (!enabledEstimators.has(estimator.id)) continue
        const result = currentEstimates[estimator.id]
        if (!result) continue
        const end = toCanvas(result.px, result.pz)
        drawFovTriangle(ctx, toCanvas, result, estimator.color)
        drawEstimatorShape(ctx, estimator.shape, end.x, end.y, 9, estimator.color)
      }

      drawAnchors(ctx, anchors, activeAnchorId, toCanvas)
      frameId = requestAnimationFrame(tick)
    }

    frameId = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frameId)
  }, [anchors, activeAnchorId, buildings, enabledEstimators, image, origin, worldHalf, captureVersion])

  // Native wheel listener (pan + ctrl/pinch zoom around cursor).
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const preventGesture = (event) => event.preventDefault()
    const handleWheel = (event) => {
      event.preventDefault()
      const width = canvas.clientWidth
      const height = canvas.clientHeight
      if (event.ctrlKey) {
        const rect = canvas.getBoundingClientRect()
        const px = event.clientX - rect.left
        const py = event.clientY - rect.top
        const before = makeTransform(width, height, viewRef.current, worldHalf).toWorld(px, py)
        viewRef.current.zoom *= event.deltaY < 0 ? 1.1 : 1 / 1.1
        if (viewRef.current.zoom <= 1e-6) viewRef.current.zoom = 1e-6
        const after = makeTransform(width, height, viewRef.current, worldHalf).toWorld(px, py)
        viewRef.current.centerX += before.x - after.x
        viewRef.current.centerZ += before.z - after.z
        loaderRef.current()
        return
      }
      viewRef.current.panX -= event.deltaX
      viewRef.current.panY -= event.deltaY
      loaderRef.current()
    }
    canvas.addEventListener('gesturestart', preventGesture, { passive: false })
    canvas.addEventListener('gesturechange', preventGesture, { passive: false })
    canvas.addEventListener('gestureend', preventGesture, { passive: false })
    canvas.addEventListener('wheel', handleWheel, { passive: false })
    return () => {
      canvas.removeEventListener('gesturestart', preventGesture)
      canvas.removeEventListener('gesturechange', preventGesture)
      canvas.removeEventListener('gestureend', preventGesture)
      canvas.removeEventListener('wheel', handleWheel)
    }
  }, [worldHalf])

  function getLocalPoint(event) {
    const rect = canvasRef.current.getBoundingClientRect()
    return { px: event.clientX - rect.left, py: event.clientY - rect.top }
  }

  const onPointerDown = (event) => {
    const canvas = canvasRef.current
    const width = canvas.clientWidth
    const height = canvas.clientHeight
    const { px, py } = getLocalPoint(event)
    const hit = anchorAtPixel(anchors, px, py, width, height, viewRef.current, worldHalf)
    if (hit) {
      dragRef.current = { id: hit.id }
      canvas.setPointerCapture?.(event.pointerId)
      return
    }
    if (event.button !== 0 && event.button !== 1) return
    panRef.current = {
      active: true,
      startX: event.clientX,
      startY: event.clientY,
      panX: viewRef.current.panX,
      panY: viewRef.current.panY,
      moved: false,
      pointerId: event.pointerId,
    }
    canvas.setPointerCapture?.(event.pointerId)
  }

  const onPointerMove = (event) => {
    const canvas = canvasRef.current
    const width = canvas.clientWidth
    const height = canvas.clientHeight
    const { px, py } = getLocalPoint(event)

    // Live cursor readout: lat/lon + the height an anchor here would take
    // (rooftop height inside a footprint, else 0 m on the ground).
    const { toWorld } = makeTransform(width, height, viewRef.current, worldHalf)
    const wp = toWorld(px, py)
    const ll = localToLl(wp.x, wp.z, origin)
    const h = heightAt(wp.x, wp.z, buildings)
    setReadout({
      lat: ll.lat,
      lon: ll.lon,
      height: h.height,
      onBuilding: !!h.building,
      estimated: h.building ? h.building.estimatedHeight : false,
      groundEle: peekElevation(ll.lat, ll.lon),
    })

    if (panRef.current.active) {
      const dx = event.clientX - panRef.current.startX
      const dy = event.clientY - panRef.current.startY
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) panRef.current.moved = true
      viewRef.current.panX = panRef.current.panX + dx
      viewRef.current.panY = panRef.current.panY + dy
      setCursor('grabbing')
      return
    }
    const hover = anchorAtPixel(anchors, px, py, width, height, viewRef.current, worldHalf)
    if (dragRef.current.id !== null) {
      setCursor('grabbing')
      setAnchorMapPoint(dragRef.current.id, toWorld(px, py))
      return
    }
    if (hover) setCursor('grab')
    else if (activeAnchorId !== null) setCursor('crosshair')
    else setCursor('default')
  }

  const onPointerUp = (event) => {
    const pan = panRef.current
    if (pan.active && !pan.moved && event.button === 0 && activeAnchorId !== null) {
      const canvas = canvasRef.current
      const width = canvas.clientWidth
      const height = canvas.clientHeight
      const { px, py } = getLocalPoint(event)
      const { toWorld } = makeTransform(width, height, viewRef.current, worldHalf)
      setAnchorMapPoint(activeAnchorId, toWorld(px, py))
    }
    if (pan.pointerId !== null) canvasRef.current.releasePointerCapture?.(pan.pointerId)
    const wasPan = pan.active && pan.moved
    panRef.current = { active: false, startX: 0, startY: 0, panX: viewRef.current.panX, panY: viewRef.current.panY, moved: false, pointerId: null }
    if (dragRef.current.id !== null) canvasRef.current.releasePointerCapture?.(event.pointerId)
    dragRef.current = { id: null }
    if (wasPan) scheduleViewportLoad()
  }

  const onDoubleClick = (event) => {
    const canvas = canvasRef.current
    const width = canvas.clientWidth
    const height = canvas.clientHeight
    const { px, py } = getLocalPoint(event)
    const hit = anchorAtPixel(anchors, px, py, width, height, viewRef.current, worldHalf)
    if (hit) return
    viewRef.current = computeAutoFit(buildings, anchors, width, height, worldHalf)
    scheduleViewportLoad()
  }

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', background: '#e8e6e1' }}>
      <canvas
        ref={canvasRef}
        style={{ width: '100%', height: '100%', display: 'block', cursor }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={(e) => { onPointerUp(e); setReadout(null) }}
        onDoubleClick={onDoubleClick}
      />

      <div style={{ position: 'absolute', top: 8, left: 8, display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap', maxWidth: 'calc(100% - 16px)' }}>
        <span style={{ background: 'rgba(255,255,255,0.8)', color: '#444', fontSize: 11, padding: '3px 8px', borderRadius: 4 }}>
          {buildingsError
            ? `⚠ ${buildingsError}`
            : buildingsLoading
              ? 'Loading buildings…'
              : `${buildings.length} buildings · ${origin.lat.toFixed(4)}, ${origin.lon.toFixed(4)}`}
        </span>
      </div>

      {/* Live cursor readout. Both lines always render (the height line falls
          back to a non-breaking space) so the position line never shifts,
          whether or not there's height data at the point. */}
      <div style={{ position: 'absolute', bottom: 8, left: 8, background: 'rgba(255,255,255,0.88)', color: '#222', fontSize: 11, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', padding: '4px 8px', borderRadius: 4, lineHeight: 1.45, pointerEvents: 'none', boxShadow: '0 1px 3px rgba(0,0,0,0.15)' }}>
        <div>{readout ? `${readout.lat.toFixed(5)}, ${readout.lon.toFixed(5)}` : '—'}</div>
        <div style={{ color: '#666' }}>
          {readout
            ? `${readoutHeightLabel(readout)}${readout.groundEle != null ? ` · ${Math.round(readout.groundEle)} m ASL` : ''}`
            : ' '}
        </div>
      </div>

      <div style={{ position: 'absolute', bottom: 4, right: 6, background: 'rgba(255,255,255,0.7)', color: '#555', fontSize: 9, padding: '1px 5px', borderRadius: 3 }}>
        © OpenStreetMap · CARTO
      </div>
    </div>
  )
}
