import { useStore } from '../store'
import styles from './AnchorPanel.module.css'

function getHint(active, anchors, hasPhoto) {
  if (!hasPhoto) return 'Upload a photo first to start placing anchors.'
  if (!active) {
    if (anchors.length === 0) return 'Click "+ Add" to create your first anchor.'
    return 'Select an anchor and place both photo + map points.'
  }
  if (!active.photoPixel && !active.mapPoint) return `Set photo + map points for #${active.id}.`
  if (!active.photoPixel) return `Set photo point for #${active.id} in photo view.`
  if (!active.mapPoint) return `Set map point for #${active.id} in map view.`
  return `Anchor #${active.id} complete.`
}

export default function AnchorPanel() {
  const anchors = useStore((s) => s.anchors)
  const activeAnchorId = useStore((s) => s.activeAnchorId)
  const addAnchor = useStore((s) => s.addAnchor)
  const removeAnchor = useStore((s) => s.removeAnchor)
  const setActiveAnchor = useStore((s) => s.setActiveAnchor)
  const clearAnchors = useStore((s) => s.clearAnchors)
  const setAnchorMapPointY = useStore((s) => s.setAnchorMapPointY)
  const hasPhoto = useStore((s) => Boolean(s.photoUrl))

  const active = anchors.find((a) => a.id === activeAnchorId) ?? null
  const hint = getHint(active, anchors, hasPhoto)

  return (
    <aside className={styles.panel}>
      <header className={styles.header}>
        <span className={styles.title}>Anchors · {anchors.length}</span>
        <button
          className={`primary ${styles.addBtn}`}
          onClick={addAnchor}
          disabled={!hasPhoto}
          title={hasPhoto ? 'Add an anchor' : 'Upload a photo first'}
        >
          + Add
        </button>
      </header>

      <div className={`${styles.hint} ${active ? styles.hintActive : ''}`}>{hint}</div>

      <div className={styles.list}>
        {anchors.length === 0 && <div className={styles.empty}>No anchors yet</div>}
        {anchors.map((a) => (
          <div
            key={a.id}
            className={`${styles.item} ${a.id === activeAnchorId ? styles.itemActive : ''}`}
            style={a.id === activeAnchorId ? { borderColor: a.color } : undefined}
            onClick={() => setActiveAnchor(a.id)}
          >
            <div className={styles.itemRow}>
              <span className={styles.swatch} style={{ background: a.color }}>{a.id}</span>
              <span className={styles.status}>
                <span className={a.photoPixel ? `${styles.dot} ${styles.on}` : styles.dot}>Photo</span>
                <span className={a.mapPoint ? `${styles.dot} ${styles.on}` : styles.dot}>Map</span>
              </span>
              <button
                className={styles.delete}
                onClick={(event) => {
                  event.stopPropagation()
                  removeAnchor(a.id)
                }}
              >
                x
              </button>
            </div>
            {a.mapPoint && (
              <div
                className={styles.heightRow}
                onClick={(event) => event.stopPropagation()}
                title="Height of this anchor above local ground, in metres. Auto-filled from the building footprint at the map click (rooftop = building height, ground = 0). Override if you clicked the base, the eaves, a facade point, etc. The terrain elevation under the point is added automatically, so world y stays a true height above the origin's ground."
              >
                <span className={styles.heightLabel}>h</span>
                <input
                  className={styles.heightInput}
                  type="number"
                  step="0.5"
                  value={Number.isFinite(a.mapPoint.structureY) ? a.mapPoint.structureY : (a.mapPoint.y ?? 0)}
                  onChange={(event) => {
                    const v = Number(event.target.value)
                    if (Number.isFinite(v)) setAnchorMapPointY(a.id, v)
                  }}
                  onClick={(event) => event.stopPropagation()}
                />
                <span className={styles.heightUnit}>m</span>
                {Number.isFinite(a.mapPoint.groundEle) && (
                  <span className={styles.heightUnit} title="Terrain elevation under this point (metres above sea level), from the DEM.">
                    · ground {Math.round(a.mapPoint.groundEle)} m
                  </span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {anchors.length > 0 && (
        <footer className={styles.footer}>
          <button onClick={clearAnchors} className={styles.clearBtn}>Clear all</button>
        </footer>
      )}
    </aside>
  )
}
