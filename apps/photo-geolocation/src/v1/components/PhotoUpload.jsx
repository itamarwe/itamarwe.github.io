import { useEffect, useRef, useState } from 'react'
import { useStore } from '../store'
import AnchorOverlays from './AnchorOverlays'

const ACCEPT = 'image/*,.heic,.heif'

/** iPhone photos are often HEIC/HEIF, which Chrome/Firefox can't decode natively. */
function isHeic(file) {
  const t = (file.type || '').toLowerCase()
  if (t.includes('heic') || t.includes('heif')) return true
  return /\.(heic|heif)$/i.test(file.name || '')
}

/**
 * Photo pane for the real-world TLV geolocation flow.
 *
 * Replaces the synthetic 3D <Canvas> with an uploaded <img>. Reuses the exact
 * pan/zoom + crisp vector anchor-overlay machinery from PhotoView:
 *
 *   frame   (100% × 100%)
 *     stage (fixed image.width × image.height, centered, pan+zoom)
 *       <img>
 *     AnchorOverlays  (sibling of stage → dots stay crisp at any zoom)
 *
 * Anchor coordinates are stored in the image's natural pixel space [0,width]×
 * [0,height], so the assumed principal point (width/2, 0) and focal length fed
 * to Full PnP are in real sensor pixels.
 */
export default function PhotoUpload() {
  const photoUrl = useStore((s) => s.photoUrl)
  const photoName = useStore((s) => s.photoName)
  const image = useStore((s) => s.image)
  const activeAnchorId = useStore((s) => s.activeAnchorId)
  const setAnchorPhotoPixel = useStore((s) => s.setAnchorPhotoPixel)
  const setPhoto = useStore((s) => s.setPhoto)
  const clearPhoto = useStore((s) => s.clearPhoto)
  const dirty = useStore((s) => s.dirty)

  const [hoverPos, setHoverPos] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [busy, setBusy] = useState(null)   // status text while converting/loading, else null
  const [confirmRemove, setConfirmRemove] = useState(false)
  const [frameSize, setFrameSize] = useState({ w: 0, h: 0 })
  const frameRef = useRef(null)
  const stageRef = useRef(null)
  const fileInputRef = useRef(null)
  const viewRef = useRef({ zoom: 1, panX: 0, panY: 0 })
  const panRef = useRef({ active: false, startX: 0, startY: 0, panX: 0, panY: 0, moved: false, pointerId: null })
  // Live touch points (pointerId → client x/y) for multi-touch gestures, the
  // in-flight pinch state, and a flag so the final lift of a two-finger gesture
  // isn't mistaken for a tap that would drop an anchor.
  const pointersRef = useRef(new Map())
  const pinchRef = useRef({ active: false, dist: 0, midX: 0, midY: 0 })
  const multiTouchRef = useRef(false)
  const [, rerender] = useState(0)

  const hasPhoto = Boolean(photoUrl)
  const canPlaceAnchor = hasPhoto && activeAnchorId !== null

  // Dev-only imperative hooks for the scripted demo recorder (mirrors the
  // window.__store hook in main.jsx). Stripped from production builds.
  useEffect(() => {
    if (!import.meta.env?.DEV) return undefined
    window.__photoView = {
      get: () => ({ ...viewRef.current }),
      set: (v) => { viewRef.current = { ...viewRef.current, ...v }; rerender((x) => x + 1) },
      imgRect: () => stageRef.current?.querySelector('img')?.getBoundingClientRect() ?? null,
      frameRect: () => frameRef.current?.getBoundingClientRect() ?? null,
    }
    return () => { try { delete window.__photoView } catch { /* ignore */ } }
  }, [])

  // ---- file ingestion -----------------------------------------------------
  async function ingestFile(file) {
    if (!file) return
    const heic = isHeic(file)
    // HEIC files frequently report an empty MIME type, so accept those by
    // extension; everything else must be an image/* type.
    if (!heic && !file.type?.startsWith('image/')) return

    let blob = file
    if (heic) {
      setBusy('Converting HEIC…')
      try {
        // heic-to bundles a current libheif build; the older heic2any choked
        // on modern iPhone HEVC HEICs with "ERR_LIBHEIF format not supported".
        const { heicTo } = await import('heic-to')
        blob = await heicTo({ blob: file, type: 'image/jpeg', quality: 0.92 })
      } catch (err) {
        console.error('[PhotoUpload] HEIC conversion failed:', err)
        setBusy('Could not read this HEIC image')
        return
      }
    }

    const url = URL.createObjectURL(blob)
    const img = new Image()
    img.onload = () => {
      setBusy(null)
      setPhoto(url, img.naturalWidth, img.naturalHeight, file.name)
      viewRef.current = { zoom: 1, panX: 0, panY: 0 }
      rerender((v) => v + 1)
    }
    img.onerror = () => {
      try { URL.revokeObjectURL(url) } catch { /* ignore */ }
      setBusy('Could not load this image')
    }
    img.src = url
  }

  const onFileChange = (event) => {
    const file = event.target.files?.[0]
    ingestFile(file)
    event.target.value = ''   // allow re-selecting the same file
  }

  const onDrop = (event) => {
    event.preventDefault()
    setDragOver(false)
    const file = event.dataTransfer.files?.[0]
    ingestFile(file)
  }

  // ---- remove photo (with a guard when there's unsaved work) --------------
  function requestRemove() {
    if (dirty) setConfirmRemove(true)
    else clearPhoto()
  }

  // ---- pan / zoom (only meaningful once a photo is loaded) ---------------
  function stagePointFromClient(event) {
    const stage = stageRef.current
    if (!stage) return null
    const rect = stage.getBoundingClientRect()
    if (rect.width <= 0 || rect.height <= 0) return null
    const x = (event.clientX - rect.left) / rect.width * image.width
    const y = (event.clientY - rect.top) / rect.height * image.height
    return { x, y }
  }

  const handlePointerDown = (event) => {
    if (!hasPhoto) return
    // Don't hijack pointer-downs that land on the overlay controls (Remove
    // button, etc.). Capturing the pointer on the frame here would redirect the
    // pointerup and swallow the control's click, so those buttons would appear
    // dead.
    if (event.target.closest?.('button, input, label, select, a')) return
    pointersRef.current.set(event.pointerId, { x: event.clientX, y: event.clientY })
    frameRef.current?.setPointerCapture?.(event.pointerId)

    // Second finger down → start a pinch, abandoning any single-finger pan so
    // the view doesn't lurch as the gesture changes character.
    if (pointersRef.current.size === 2) {
      multiTouchRef.current = true
      panRef.current.active = false
      const [a, b] = [...pointersRef.current.values()]
      pinchRef.current = {
        active: true,
        dist: Math.hypot(a.x - b.x, a.y - b.y) || 1,
        midX: (a.x + b.x) / 2,
        midY: (a.y + b.y) / 2,
      }
      return
    }

    // Single pointer → pan. For a mouse, only the left/middle buttons pan.
    if (event.pointerType === 'mouse' && event.button !== 0 && event.button !== 1) return
    panRef.current = {
      active: true,
      startX: event.clientX,
      startY: event.clientY,
      panX: viewRef.current.panX,
      panY: viewRef.current.panY,
      moved: false,
      pointerId: event.pointerId,
    }
  }

  const handlePointerMove = (event) => {
    if (pointersRef.current.has(event.pointerId)) {
      pointersRef.current.set(event.pointerId, { x: event.clientX, y: event.clientY })
    }

    // Two-finger pinch: scale around the gesture midpoint (same anchor-point
    // math as the ctrl+wheel zoom) and pan along with the midpoint's drift.
    if (pinchRef.current.active && pointersRef.current.size >= 2) {
      const [a, b] = [...pointersRef.current.values()]
      const dist = Math.hypot(a.x - b.x, a.y - b.y) || 1
      const midX = (a.x + b.x) / 2
      const midY = (a.y + b.y) / 2
      const prev = viewRef.current.zoom
      const next = Math.max(0.05, prev * (dist / pinchRef.current.dist))
      const ratio = next / prev
      viewRef.current.zoom = next
      const rect = stageRef.current?.getBoundingClientRect()
      if (rect && rect.width > 0 && rect.height > 0) {
        const fx = (midX - rect.left) / rect.width - 0.5
        const fy = (midY - rect.top) / rect.height - 0.5
        viewRef.current.panX -= fx * rect.width * (ratio - 1)
        viewRef.current.panY -= fy * rect.height * (ratio - 1)
      }
      viewRef.current.panX += midX - pinchRef.current.midX
      viewRef.current.panY += midY - pinchRef.current.midY
      pinchRef.current = { active: true, dist, midX, midY }
      rerender((v) => v + 1)
      return
    }

    if (panRef.current.active) {
      const dx = event.clientX - panRef.current.startX
      const dy = event.clientY - panRef.current.startY
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) panRef.current.moved = true
      viewRef.current.panX = panRef.current.panX + dx
      viewRef.current.panY = panRef.current.panY + dy
      rerender((v) => v + 1)
      return
    }
    if (!canPlaceAnchor) return
    const p = stagePointFromClient(event)
    if (!p) return
    setHoverPos(p)
  }

  const handlePointerLeave = () => setHoverPos(null)

  const handlePointerUp = (event) => {
    pointersRef.current.delete(event.pointerId)
    try { frameRef.current?.releasePointerCapture?.(event.pointerId) } catch { /* ignore */ }

    // Winding down a pinch. If one finger is still down, hand the gesture back
    // to single-finger panning without a jump (and not as a tap).
    if (pinchRef.current.active) {
      if (pointersRef.current.size < 2) {
        pinchRef.current.active = false
        const [id, p] = [...pointersRef.current.entries()][0] ?? []
        if (id !== undefined) {
          panRef.current = { active: true, startX: p.x, startY: p.y, panX: viewRef.current.panX, panY: viewRef.current.panY, moved: true, pointerId: id }
        }
      }
      if (pointersRef.current.size === 0) multiTouchRef.current = false
      return
    }

    const panned = panRef.current.moved
    const wasActive = panRef.current.active
    const wasMulti = multiTouchRef.current
    panRef.current = { active: false, startX: 0, startY: 0, panX: viewRef.current.panX, panY: viewRef.current.panY, moved: false, pointerId: null }
    if (pointersRef.current.size === 0) multiTouchRef.current = false
    if (!wasActive || panned || wasMulti || !canPlaceAnchor) return
    const p = stagePointFromClient(event)
    if (!p) return
    setAnchorPhotoPixel(activeAnchorId, { x: p.x, y: p.y })
  }

  const handleDoubleClick = () => {
    viewRef.current = { zoom: 1, panX: 0, panY: 0 }
    rerender((v) => v + 1)
  }

  // Native non-passive wheel listener (pan + ctrl/pinch zoom around cursor).
  useEffect(() => {
    const frame = frameRef.current
    if (!frame) return
    const onWheel = (event) => {
      if (!hasPhoto) return
      event.preventDefault()
      const stage = stageRef.current
      if (!stage) return
      const rect = stage.getBoundingClientRect()
      if (event.ctrlKey) {
        const factor = event.deltaY < 0 ? 1.1 : 1 / 1.1
        const prev = viewRef.current.zoom
        const next = Math.max(0.05, prev * factor)
        const ratio = next / prev
        viewRef.current.zoom = next
        const fx = (event.clientX - rect.left) / rect.width - 0.5
        const fy = (event.clientY - rect.top) / rect.height - 0.5
        viewRef.current.panX -= fx * rect.width * (ratio - 1)
        viewRef.current.panY -= fy * rect.height * (ratio - 1)
      } else {
        viewRef.current.panX -= event.deltaX
        viewRef.current.panY -= event.deltaY
      }
      rerender((v) => v + 1)
    }
    const preventGesture = (e) => e.preventDefault()
    frame.addEventListener('wheel', onWheel, { passive: false })
    frame.addEventListener('gesturestart', preventGesture, { passive: false })
    frame.addEventListener('gesturechange', preventGesture, { passive: false })
    frame.addEventListener('gestureend', preventGesture, { passive: false })
    return () => {
      frame.removeEventListener('wheel', onWheel)
      frame.removeEventListener('gesturestart', preventGesture)
      frame.removeEventListener('gesturechange', preventGesture)
      frame.removeEventListener('gestureend', preventGesture)
    }
  }, [hasPhoto, image.width, image.height])

  // Frame-size tracker so fitScale reacts to layout/resize.
  useEffect(() => {
    const frame = frameRef.current
    if (!frame) return
    const update = () => {
      const rect = frame.getBoundingClientRect()
      if (rect.width <= 0 || rect.height <= 0) return
      setFrameSize((s) => (s.w === rect.width && s.h === rect.height ? s : { w: rect.width, h: rect.height }))
    }
    update()
    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', update)
      return () => window.removeEventListener('resize', update)
    }
    const ro = new ResizeObserver(update)
    ro.observe(frame)
    return () => ro.disconnect()
  }, [])

  // Shrink-to-fit, never auto-grow past 1× (user can ctrl+zoom in).
  const fitScale = (frameSize.w <= 0 || frameSize.h <= 0 || !hasPhoto)
    ? 1
    : Math.min(1, frameSize.w / image.width, frameSize.h / image.height)

  const stageStyle = {
    position: 'absolute',
    left: '50%',
    top: '50%',
    width: image.width,
    height: image.height,
    transformOrigin: 'center center',
    transform: `translate(-50%, -50%) translate(${viewRef.current.panX}px, ${viewRef.current.panY}px) scale(${viewRef.current.zoom * fitScale})`,
  }

  return (
    <div
      ref={frameRef}
      style={{
        width: '100%',
        height: '100%',
        position: 'relative',
        overflow: 'hidden',
        background: '#0a0a0a',
        cursor: canPlaceAnchor ? 'crosshair' : 'auto',
        touchAction: 'none',
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerLeave}
      onPointerCancel={handlePointerUp}
      onDoubleClick={handleDoubleClick}
      onDragOver={(e) => { e.preventDefault(); if (!dragOver) setDragOver(true) }}
      onDragLeave={(e) => { e.preventDefault(); setDragOver(false) }}
      onDrop={onDrop}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPT}
        onChange={onFileChange}
        style={{ display: 'none' }}
      />

      {busy && hasPhoto && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.6)', color: '#eee', fontSize: 13, zIndex: 5 }}>
          {busy}
        </div>
      )}

      {hasPhoto ? (
        <>
          <div ref={stageRef} style={stageStyle}>
            <img
              src={photoUrl}
              alt={photoName || 'uploaded photo'}
              draggable={false}
              style={{ width: '100%', height: '100%', display: 'block', userSelect: 'none' }}
            />
          </div>

          <AnchorOverlays
            hoverPos={hoverPos}
            showHover={canPlaceAnchor}
            view={{
              panX: viewRef.current.panX,
              panY: viewRef.current.panY,
              scale: viewRef.current.zoom * fitScale,
              frameW: frameSize.w,
              frameH: frameSize.h,
              imageW: image.width,
              imageH: image.height,
            }}
          />

          <button
            type="button"
            onClick={requestRemove}
            title="Remove photo"
            aria-label="Remove photo"
            style={{
              position: 'absolute', top: 8, left: 8,
              width: 26, height: 26, padding: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              border: '1px solid rgba(255,255,255,0.25)', borderRadius: 4,
              background: 'rgba(0,0,0,0.55)', color: '#ddd', cursor: 'pointer', lineHeight: 1,
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
              <line x1="6" y1="6" x2="18" y2="18" />
              <line x1="18" y1="6" x2="6" y2="18" />
            </svg>
          </button>
          <div style={{ position: 'absolute', top: 8, right: 8, display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={{ background: 'rgba(0,0,0,0.55)', color: '#ddd', fontSize: 11, padding: '3px 8px', borderRadius: 4 }}>
              {image.width} x {image.height}
            </span>
          </div>

          {confirmRemove && (
            <div
              onPointerDown={(e) => e.stopPropagation()}
              style={{ position: 'absolute', inset: 0, zIndex: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.6)' }}
            >
              <div style={{ background: '#1c1c1c', border: '1px solid #444', borderRadius: 8, padding: 20, maxWidth: 300, color: '#eee', boxShadow: '0 8px 30px rgba(0,0,0,0.5)' }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Remove this photo?</div>
                <div style={{ fontSize: 12, color: '#bbb', lineHeight: 1.5, marginBottom: 16 }}>
                  You have unsaved changes (anchors or estimators). All of it will be lost. Save the session first if you want to keep your work.
                </div>
                <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                  <button type="button" onClick={() => setConfirmRemove(false)} style={{ fontSize: 12 }}>Cancel</button>
                  <button
                    type="button"
                    className="primary"
                    onClick={() => { setConfirmRemove(false); clearPhoto() }}
                    style={{ fontSize: 12, background: '#c0392b', borderColor: '#c0392b' }}
                  >
                    Discard &amp; remove
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          style={{
            position: 'absolute',
            inset: 24,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
            border: `2px dashed ${dragOver ? 'var(--accent, #5b9eff)' : '#444'}`,
            borderRadius: 12,
            background: dragOver ? 'rgba(91,158,255,0.08)' : 'transparent',
            color: '#bbb',
            cursor: 'pointer',
            transition: 'border-color 120ms, background 120ms',
            font: 'inherit',
          }}
        >
          <div style={{ fontSize: 40, lineHeight: 1 }}>📷</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#eee' }}>
            {dragOver ? 'Drop your photo to upload' : 'Click to upload a Tel Aviv photo'}
          </div>
          <div style={{ fontSize: 12, color: '#888' }}>
            {busy || 'or drag & drop an image here (JPG, PNG, HEIC)'}
          </div>
          <div style={{ fontSize: 11, color: '#666', maxWidth: 320, textAlign: 'center' }}>
            Then place anchors on building corners and match them to the map to geolocate the camera.
          </div>
        </button>
      )}
    </div>
  )
}
