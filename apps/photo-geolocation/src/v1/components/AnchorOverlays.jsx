import { useStore } from '../store'

const DOT_R = 7   // radius of the anchor dot, in screen pixels

/**
 * Vector overlay for anchor dots / ID badges / hover crosshair.
 *
 * Rendered as a SIBLING of the scaled `stage` element (not a child), so the
 * stage's CSS scale never reaches the dots — they stay crisp at all zoom
 * levels (a fix for the dots pixelating along with the rasterised photo).
 *
 * Positions are computed in frame-local CSS pixels from the same view the
 * stage uses, so dots track the photo exactly. Math (one formula for both
 * modes — in edit mode image.w/h tracks frame.w/h via ResizeObserver):
 *
 *     s        = zoom * fitScale  (passed in as view.scale)
 *     stageCx  = frame.w/2 + panX,   stageCy = frame.h/2 + panY
 *     screenX  = stageCx + (imgX - image.w/2) * s
 *     screenY  = stageCy + (imgY - image.h/2) * s
 */
export default function AnchorOverlays({ hoverPos, showHover, view }) {
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
