import { useEffect, useRef } from 'react'
import { useStore } from '../store'
import { poseState } from '../poseState'
import { ESTIMATORS } from '../pose/registry'
import styles from './PosePanel.module.css'

function ShapeGlyph({ shape, color }) {
  const s = 16, r = 6, c = s / 2
  let path
  switch (shape) {
    case 'square':   path = <rect x={c-r} y={c-r} width={r*2} height={r*2} />; break
    case 'diamond':  path = <polygon points={`${c},${c-r} ${c+r},${c} ${c},${c+r} ${c-r},${c}`} />; break
    case 'triangle': path = <polygon points={`${c},${c-r} ${c+r*0.87},${c+r*0.5} ${c-r*0.87},${c+r*0.5}`} />; break
    default:         path = <circle cx={c} cy={c} r={r} />
  }
  return (
    <svg width={s} height={s} style={{ flexShrink: 0 }} aria-hidden="true">
      <g fill={color + '40'} stroke={color} strokeWidth={2}>{path}</g>
      <circle cx={c} cy={c} r={1.8} fill={color} />
    </svg>
  )
}

function ErrorBadge({ estId }) {
  const ref = useRef(null)

  useEffect(() => {
    let frameId = 0
    const tick = () => {
      const el = ref.current
      if (!el) return
      const estimate = poseState.estimates[estId]
      if (!estimate || !Number.isFinite(estimate.lat) || !Number.isFinite(estimate.lon)) {
        el.textContent = '-'
        el.dataset.state = 'off'
      } else {
        // No ground truth for a real uploaded photo — show the estimated
        // camera location (lat, lon) and heading instead of an error.
        const heading = Number.isFinite(estimate.headingDeg)
          ? ` · ${((estimate.headingDeg % 360) + 360) % 360 | 0}°`
          : ''
        // Camera elevation (m ASL), solved by PnP from the terrain-aware anchors.
        const elev = Number.isFinite(estimate.elevation)
          ? ` · ${Math.round(estimate.elevation)} m asl`
          : ''
        el.textContent = `${estimate.lat.toFixed(5)}, ${estimate.lon.toFixed(5)}${heading}${elev}`
        el.dataset.state = 'ok'
      }
      frameId = requestAnimationFrame(tick)
    }
    frameId = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frameId)
  }, [estId])

  return <span ref={ref} className={styles.error} data-state="off">-</span>
}

export default function PosePanel() {
  const enabled = useStore((s) => s.enabledEstimators)
  const toggleEstimator = useStore((s) => s.toggleEstimator)
  const observationCount = useStore((s) => s.anchors.filter((a) => a.photoPixel && a.mapPoint).length)

  return (
    <aside className={styles.panel}>
      <header className={styles.header}>
        <span className={styles.title}>Pose Estimation</span>
        <span className={styles.count}>{observationCount} obs</span>
      </header>

      <div className={styles.list}>
        {ESTIMATORS.map((e) => {
          const enabledRow = enabled.has(e.id)
          const notEnough = observationCount < e.minAnchors
          return (
            <div
              key={e.id}
              className={`${styles.item} ${enabledRow ? styles.itemOn : ''}`}
              onClick={() => toggleEstimator(e.id)}
            >
              <input
                className={styles.cb}
                type="checkbox"
                checked={enabledRow}
                onChange={() => toggleEstimator(e.id)}
                onClick={(event) => event.stopPropagation()}
                style={{ accentColor: e.color }}
              />
              <ShapeGlyph shape={e.shape} color={e.color} />
              <div className={styles.meta}>
                <div
                  className={styles.name}
                  style={{ color: enabledRow ? e.color : undefined }}
                >
                  {e.name}
                </div>
                <div className={styles.blurb}>{e.blurb}</div>
              </div>
              <div className={styles.stats}>
                {notEnough ? <span className={styles.notEnough}>min {e.minAnchors}</span> : <ErrorBadge estId={e.id} />}
              </div>
            </div>
          )
        })}
      </div>
    </aside>
  )
}
