import { useEffect, useRef, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Grid, OrbitControls, Sky } from '@react-three/drei'
import * as THREE from 'three'
import { useStore } from '../store'
import { cameraState } from '../cameraState'
import { photoState } from '../photoState'

const DPR = typeof window === 'undefined' ? 1 : Math.max(1, window.devicePixelRatio || 1)

function CameraSync({ isEdit }) {
  const { camera } = useThree()
  const dir = useRef(new THREE.Vector3())

  useFrame(() => {
    if (!isEdit) return
    camera.getWorldDirection(dir.current)
    cameraState.px = camera.position.x
    cameraState.py = camera.position.y
    cameraState.pz = camera.position.z
    cameraState.dx = dir.current.x
    cameraState.dy = dir.current.y
    cameraState.dz = dir.current.z
    cameraState.fov = camera.fov
  })

  return null
}

function CameraModeSync({ mode, fov, captureVersion }) {
  const { camera } = useThree()

  useEffect(() => {
    if (mode === 'edit') {
      camera.position.set(cameraState.px, cameraState.py, cameraState.pz)
      camera.fov = fov
      camera.lookAt(cameraState.px + cameraState.dx, cameraState.py + cameraState.dy, cameraState.pz + cameraState.dz)
      camera.updateProjectionMatrix()
      return
    }
    const c = photoState._capture.camera
    camera.position.set(c.px, c.py, c.pz)
    camera.fov = c.fov
    camera.lookAt(c.px + c.dx, c.py + c.dy, c.pz + c.dz)
    camera.updateProjectionMatrix()
  }, [camera, mode, fov, captureVersion])

  return null
}

function Building({ b }) {
  return (
    <group position={[b.x, b.height / 2, b.z]}>
      <mesh castShadow receiveShadow>
        <boxGeometry args={[b.width, b.height, b.depth]} />
        <meshLambertMaterial color={`hsl(${b.colorH}, 30%, 55%)`} />
      </mesh>
    </group>
  )
}

// Trees & people injected into the scene. Seeded indirectly via the buildings'
// positions so identical scenes stay identical across renders.
function Tree({ position, height }) {
  const trunkH = height * 0.35
  const crownH = height * 0.65
  return (
    <group position={position}>
      <mesh castShadow position={[0, trunkH / 2, 0]}>
        <cylinderGeometry args={[0.3, 0.35, trunkH, 8]} />
        <meshLambertMaterial color="#5a3a24" />
      </mesh>
      <mesh castShadow position={[0, trunkH + crownH / 2, 0]}>
        <coneGeometry args={[height * 0.28, crownH, 10]} />
        <meshLambertMaterial color="#2d5e2a" />
      </mesh>
    </group>
  )
}

function Person({ position }) {
  // Fixed-proportions stick figure-ish character. All people same height (1.8u).
  return (
    <group position={position}>
      <mesh castShadow position={[0, 0.45, 0]}>
        <boxGeometry args={[0.5, 0.9, 0.3]} />
        <meshLambertMaterial color="#2b6cb0" />
      </mesh>
      <mesh castShadow position={[0, 1.2, 0]}>
        <sphereGeometry args={[0.22, 12, 10]} />
        <meshLambertMaterial color="#e5c9a8" />
      </mesh>
      <mesh castShadow position={[0, 1.7, 0]}>
        <boxGeometry args={[0.5, 0.15, 0.5]} />
        <meshLambertMaterial color="#444" />
      </mesh>
    </group>
  )
}

function Scene({ buildings, decor }) {
  return (
    <>
      <ambientLight intensity={0.6} />
      <directionalLight castShadow position={[40, 60, 30]} intensity={1.2} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[300, 300]} />
        <meshLambertMaterial color="#3a5a3a" />
      </mesh>
      <Grid args={[200, 200]} position={[0, 0.01, 0]} cellSize={10} sectionSize={50} fadeDistance={150} />
      {buildings.map((b) => <Building key={b.id} b={b} />)}
      {decor.trees.map((t) => <Tree key={t.id} position={t.position} height={t.height} />)}
      {decor.people.map((p) => <Person key={p.id} position={p.position} />)}
    </>
  )
}

const DOT_R = 7   // radius of the anchor dot, in screen pixels

/**
 * Vector overlay for anchor dots / ID badges / hover crosshair.
 *
 * Rendered as a SIBLING of the scaled `stage` element (not a child), so the
 * stage's CSS scale never reaches the dots — they stay crisp at all zoom
 * levels (a fix for the dots pixelating along with the rasterised photo).
 *
 * Positions are computed in frame-local CSS pixels from the same viewRef the
 * stage uses, so dots track the photo exactly. Math (one formula for both
 * modes — in edit mode image.w/h tracks frame.w/h via ResizeObserver):
 *
 *     s        = zoom * fitScale
 *     stageCx  = frame.w/2 + panX,   stageCy = frame.h/2 + panY
 *     screenX  = stageCx + (imgX - image.w/2) * s
 *     screenY  = stageCy + (imgY - image.h/2) * s
 */
function AnchorOverlays({ hoverPos, showHover, view }) {
  const anchors = useStore((s) => s.anchors)
  const activeAnchorId = useStore((s) => s.activeAnchorId)
  const setActiveAnchor = useStore((s) => s.setActiveAnchor)

  const handleDotPointerDown = (event, id) => {
    event.stopPropagation()
    if (activeAnchorId !== id) setActiveAnchor(id)
  }

  const { panX, panY, scale, frameW, frameH, imageW, imageH } = view
  if (!(frameW > 0) || !(frameH > 0) || !(imageW > 0) || !(imageH > 0)) return null

  const stageCx = frameW / 2 + panX
  const stageCy = frameH / 2 + panY
  const toScreen = (ix, iy) => ({
    x: stageCx + (ix - imageW / 2) * scale,
    y: stageCy + (iy - imageH / 2) * scale,
  })
  // Visible photo extent in frame coords (so the crosshair clips to the photo).
  const photoLeft   = stageCx - (imageW / 2) * scale
  const photoTop    = stageCy - (imageH / 2) * scale
  const photoRight  = stageCx + (imageW / 2) * scale
  const photoBottom = stageCy + (imageH / 2) * scale

  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
      {/* Crosshair shown while hovering before placing a dot. Spans the
          visible photo rectangle (not the entire frame), so the hairs end at
          the photo edge regardless of pan/zoom. */}
      {showHover && hoverPos && Number.isFinite(hoverPos.x) && Number.isFinite(hoverPos.y) && (() => {
        const p = toScreen(hoverPos.x, hoverPos.y)
        return (
          <>
            {/* vertical hair */}
            <div style={{
              position: 'absolute',
              top: photoTop, height: photoBottom - photoTop,
              left: p.x, width: 1,
              transform: 'translateX(-0.5px)',
              background: 'rgba(255,255,255,0.45)',
              pointerEvents: 'none',
            }} />
            {/* horizontal hair */}
            <div style={{
              position: 'absolute',
              left: photoLeft, width: photoRight - photoLeft,
              top: p.y, height: 1,
              transform: 'translateY(-0.5px)',
              background: 'rgba(255,255,255,0.45)',
              pointerEvents: 'none',
            }} />
          </>
        )
      })()}

      {/* Placed anchor dots — fixed-size CSS circles, never scaled. */}
      {anchors.filter((a) => a.photoPixel).map((a) => {
        const { x, y } = a.photoPixel
        const p = toScreen(x, y)
        const isActive = a.id === activeAnchorId
        return (
          <div key={a.id}>
            {/* Dot */}
            <div
              onPointerDown={(event) => handleDotPointerDown(event, a.id)}
              onPointerUp={(event) => event.stopPropagation()}
              onClick={(event) => event.stopPropagation()}
              title={`Anchor ${a.id}`}
              style={{
                position: 'absolute',
                left: p.x - DOT_R,
                top: p.y - DOT_R,
                width: DOT_R * 2,
                height: DOT_R * 2,
                borderRadius: '50%',
                background: isActive ? a.color : `${a.color}cc`,
                border: `2px solid #fff`,
                boxShadow: isActive ? `0 0 0 3px ${a.color}88` : `0 1px 3px #0008`,
                cursor: 'pointer',
                pointerEvents: 'auto',
              }}
            />
            {/* ID badge — offset up-right from the dot */}
            <div
              onPointerDown={(event) => handleDotPointerDown(event, a.id)}
              onPointerUp={(event) => event.stopPropagation()}
              onClick={(event) => event.stopPropagation()}
              style={{
                position: 'absolute',
                left: p.x + DOT_R - 2,
                top: p.y - DOT_R - 16,
                minWidth: 16,
                height: 16,
                paddingInline: 3,
                borderRadius: 4,
                border: `1.5px solid ${a.color}`,
                color: 'white',
                fontSize: 10,
                fontWeight: 700,
                display: 'grid',
                placeItems: 'center',
                background: '#000b',
                cursor: 'pointer',
                pointerEvents: 'auto',
                userSelect: 'none',
                whiteSpace: 'nowrap',
              }}
            >
              {a.id}
            </div>
          </div>
        )
      })}
    </div>
  )
}

/**
 * Layout:
 *   frame       (100% × 100% — whatever the flex layout gives)
 *     stage     (fixed image.width × image.height in view mode, centered;
 *                fills the frame in edit mode). This is the "photo" — pan/zoom
 *                transforms this element relative to its center. All anchor
 *                coordinates are stored in stage-local pixels [0, image.width]
 *                so they stay welded to the rendered scene regardless of how
 *                the outer frame resizes.
 *       Canvas, AnchorOverlays
 *
 * Click handling converts clientX to stage-local pixels using the stage's
 * actual getBoundingClientRect — robust to any combination of pan/zoom and
 * centering.
 */
export default function PhotoView() {
  const mode = useStore((s) => s.mode)
  const fov = useStore((s) => s.fov)
  const buildings = useStore((s) => s.buildings)
  const decor = useStore((s) => s.decor)
  const captureVersion = useStore((s) => s.captureVersion)
  const activeAnchorId = useStore((s) => s.activeAnchorId)
  const setAnchorPhotoPixel = useStore((s) => s.setAnchorPhotoPixel)
  // setImageSize is intentionally NOT subscribed via useStore — we access it
  // through useStore.getState() inside effect callbacks so it never enters a
  // dep array.  An action reference sneaking into deps (HMR, devtools
  // instrumentation, future Zustand changes) would cause the effects below to
  // re-fire and resnap image to whatever the frame happens to measure at that
  // instant, potentially halving the photo if a transient layout state is
  // captured.
  const image = useStore((s) => s.image)
  const [hoverPos, setHoverPos] = useState(null)   // {x, y} in stage-local px
  const frameRef = useRef(null)
  const stageRef = useRef(null)
  const viewRef = useRef({ zoom: 1, panX: 0, panY: 0 })
  const panRef = useRef({ active: false, startX: 0, startY: 0, panX: 0, panY: 0, moved: false, pointerId: null })
  const [, rerender] = useState(0)

  const isEdit = mode === 'edit'
  const canPlaceAnchor = !isEdit && activeAnchorId !== null

  // Convert a raw clientX/Y to stage-local pixels using the stage's actual
  // on-screen rect. This is invariant under any pan/zoom/centering, so we
  // don't have to reason about CSS transforms to recover image coordinates.
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
    if (isEdit) return
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
    frameRef.current?.setPointerCapture?.(event.pointerId)
  }

  const handlePointerMove = (event) => {
    if (!isEdit && panRef.current.active) {
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

  const handlePointerLeave = () => {
    setHoverPos(null)
  }

  const handlePointerUp = (event) => {
    const pointerId = panRef.current.pointerId
    const panned = panRef.current.moved
    const wasActive = panRef.current.active
    panRef.current = { active: false, startX: 0, startY: 0, panX: viewRef.current.panX, panY: viewRef.current.panY, moved: false, pointerId: null }
    if (pointerId !== null) frameRef.current?.releasePointerCapture?.(pointerId)
    if (isEdit) return
    if (!wasActive) return
    if (panned) return
    if (!canPlaceAnchor) return
    const p = stagePointFromClient(event)
    if (!p) return
    setAnchorPhotoPixel(activeAnchorId, { x: p.x, y: p.y })
  }

  // Native non-passive wheel listener (React's onWheel is passive; calling
  // preventDefault() inside it triggers a console warning).
  useEffect(() => {
    const frame = frameRef.current
    if (!frame) return
    const onWheel = (event) => {
      if (isEdit) return
      event.preventDefault()
      const stage = stageRef.current
      if (!stage) return
      const rect = stage.getBoundingClientRect()
      const px = event.clientX
      const py = event.clientY

      if (event.ctrlKey) {
        // Keep the stage-local point under the cursor fixed across the zoom.
        // We derive everything from the stage's *actual* bounding rect, which
        // already accounts for fitScale, any previous zoom, and pan — no need
        // to reason about fitScale separately.
        const factor = event.deltaY < 0 ? 1.1 : 1 / 1.1
        const prev = viewRef.current.zoom
        const next = Math.max(0.05, prev * factor)
        const ratio = next / prev
        viewRef.current.zoom = next
        // Fraction of the stage the cursor sits over (0..1), independent of
        // image pixel dimensions. After scaling by `ratio` around the stage's
        // center, that same fraction will appear `ratio` farther from center,
        // so we shift the pan to cancel the drift.
        const fx = (px - rect.left) / rect.width - 0.5
        const fy = (py - rect.top) / rect.height - 0.5
        const drift = { x: fx * rect.width * (ratio - 1), y: fy * rect.height * (ratio - 1) }
        viewRef.current.panX -= drift.x
        viewRef.current.panY -= drift.y
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
  }, [isEdit, image.width, image.height])

  // Image dimensions are the coordinate frame anchors live in. They MUST only
  // change at well-defined moments:
  //   • While composing in edit mode, image tracks the frame live so the user
  //     sees what aspect they'll capture.
  //   • On takePhoto (captureVersion bump while exiting edit mode), image
  //     snapshots the frame once.
  //   • Initial mount with no captured photo: image syncs to the frame once
  //     so the default _capture has somewhere sensible to draw into.
  // In view mode after a photo is taken, image is FROZEN. Window resizes,
  // mode toggles, footer reflows (the EditPanel renders different heights in
  // edit vs view), nothing — all are absorbed by the fitScale on the stage,
  // not by reshaping the coordinate frame anchors are stored in.
  const [frameSize, setFrameSize] = useState({ w: 0, h: 0 })

  // Frame-size tracker — runs always, just to keep frameSize state in sync
  // with the on-screen rect so fitScale can react to resizes.
  useEffect(() => {
    const frame = frameRef.current
    if (!frame) return
    const update = () => {
      const rect = frame.getBoundingClientRect()
      if (rect.width <= 0 || rect.height <= 0) return
      setFrameSize((s) =>
        s.w === rect.width && s.h === rect.height ? s : { w: rect.width, h: rect.height },
      )
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

  // Image-size writer (edit mode only). In edit mode the user is composing —
  // image must follow the frame so takePhoto records the correct aspect.
  useEffect(() => {
    if (!isEdit) return
    const frame = frameRef.current
    if (!frame) return
    const sync = () => {
      const rect = frame.getBoundingClientRect()
      if (rect.width > 0 && rect.height > 0) {
        useStore.getState().setImageSize(rect.width, rect.height)
      }
    }
    sync()
    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', sync)
      return () => window.removeEventListener('resize', sync)
    }
    const ro = new ResizeObserver(sync)
    ro.observe(frame)
    return () => ro.disconnect()
  }, [isEdit])

  // One-shot sync on takePhoto. Deferred to the next animation frame so the
  // exit-edit-mode reflow (footer EditPanel shrinks from input panel back to
  // single-line note, photo frame grows vertically) has settled before we
  // measure. Without the rAF, getBoundingClientRect can return the previous
  // edit-mode frame height, locking image.height at a too-small value.
  // Initial mount also runs this branch (captureVersion=1, isEdit=false)
  // so the default _capture has correct image dimensions on first paint.
  useEffect(() => {
    if (isEdit) return
    const frame = frameRef.current
    if (!frame) return
    const handle = requestAnimationFrame(() => {
      const rect = frame.getBoundingClientRect()
      if (rect.width > 0 && rect.height > 0) {
        useStore.getState().setImageSize(rect.width, rect.height)
      }
    })
    return () => cancelAnimationFrame(handle)
  }, [captureVersion, isEdit])

  // Double-click empty area resets pan/zoom.
  const handleDoubleClick = () => {
    viewRef.current = { zoom: 1, panX: 0, panY: 0 }
    rerender((v) => v + 1)
  }

  // Compute a fit scale so the stage shrinks to fit frames smaller than the
  // photo, but never grows past 1× on its own (user can ctrl+zoom past 1).
  const fitScale = (isEdit || frameSize.w <= 0 || frameSize.h <= 0)
    ? 1
    : Math.min(1, frameSize.w / image.width, frameSize.h / image.height)

  // Stage CSS: in edit mode, fill the frame; in view mode, fixed-size centered
  // rectangle with pan+zoom applied. transformOrigin center means zoom scales
  // around the stage's center, which makes the centering math simple.
  const stageStyle = isEdit
    ? {
        position: 'absolute',
        inset: 0,
        transformOrigin: 'center center',
        transform: `translate(${viewRef.current.panX}px, ${viewRef.current.panY}px) scale(${viewRef.current.zoom})`,
      }
    : {
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
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerLeave}
      onPointerCancel={handlePointerUp}
      onDoubleClick={handleDoubleClick}
    >
      <div ref={stageRef} style={stageStyle}>
        <Canvas
          shadows
          dpr={DPR}
          camera={{ position: [0, 45, 90], fov: 60, near: 0.1, far: 5000 }}
          style={{ background: '#87ceeb' }}
        >
          <Sky sunPosition={[100, 60, 30]} />
          <Scene buildings={buildings} decor={decor} />
          <CameraSync isEdit={isEdit} />
          <CameraModeSync mode={mode} fov={fov} captureVersion={captureVersion} />
          {isEdit && (
            <OrbitControls
              makeDefault
              enableDamping
              dampingFactor={0.08}
              minDistance={2}
              maxDistance={3000}
              maxPolarAngle={Math.PI / 2 - 0.02}
              zoomToCursor
            />
          )}
        </Canvas>
      </div>

      {/* Vector overlay — sibling of the (raster, scaled) stage so dot
          glyphs and the crosshair stay crisp at any zoom. Positions are
          recomputed on every render from the same viewRef the stage uses. */}
      <AnchorOverlays
        hoverPos={hoverPos}
        showHover={canPlaceAnchor}
        view={{
          panX:   viewRef.current.panX,
          panY:   viewRef.current.panY,
          scale:  viewRef.current.zoom * fitScale,
          frameW: frameSize.w,
          frameH: frameSize.h,
          imageW: image.width,
          imageH: image.height,
        }}
      />

      <div style={{ position: 'absolute', top: 8, left: 8, background: 'rgba(0,0,0,0.55)', color: '#ddd', fontSize: 11, padding: '3px 8px', borderRadius: 4 }}>
        {isEdit ? 'PHOTO EDIT MODE · move camera then Take Photo' : 'PHOTO VIEW MODE · drag pan · wheel pan · ctrl+wheel zoom · dblclick reset · click place anchor'}
      </div>
      <div style={{ position: 'absolute', top: 8, right: 8, background: 'rgba(0,0,0,0.55)', color: '#ddd', fontSize: 11, padding: '3px 8px', borderRadius: 4 }}>
        {image.width} x {image.height}
      </div>
    </div>
  )
}
