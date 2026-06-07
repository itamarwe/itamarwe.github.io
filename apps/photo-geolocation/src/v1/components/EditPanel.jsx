import { useEffect, useState } from 'react'
import { useStore } from '../store'
import styles from './EditPanel.module.css'

export default function EditPanel() {
  const mode = useStore((s) => s.mode)
  const seed = useStore((s) => s.seed)
  const count = useStore((s) => s.count)
  const fov = useStore((s) => s.fov)
  const setFov = useStore((s) => s.setFov)
  const regenerate = useStore((s) => s.regenerate)
  const takePhoto = useStore((s) => s.takePhoto)

  const [localSeed, setLocalSeed] = useState(String(seed))
  const [localCount, setLocalCount] = useState(String(count))

  useEffect(() => { setLocalSeed(String(seed)) }, [seed])
  useEffect(() => { setLocalCount(String(count)) }, [count])

  function handleRegenerate() {
    const nextSeed = parseInt(localSeed, 10)
    const nextCount = parseInt(localCount, 10)
    if (Number.isNaN(nextSeed) || Number.isNaN(nextCount)) return
    if (nextCount < 1 || nextCount > 100) return
    regenerate(nextSeed, nextCount)
  }

  if (mode !== 'edit') {
    return (
      <div className={styles.panel}>
        <div className={styles.note}>View mode: estimation sees only photo pixel anchors + map points.</div>
      </div>
    )
  }

  return (
    <div className={styles.panel}>
      <div className={styles.group}>
        <label>Seed</label>
        <input type="number" value={localSeed} onChange={(e) => setLocalSeed(e.target.value)} />
      </div>

      <div className={styles.group}>
        <label>Buildings</label>
        <input type="number" value={localCount} onChange={(e) => setLocalCount(e.target.value)} />
      </div>

      <div className={styles.group}>
        <label>FOV</label>
        <input type="range" min={1} max={120} step={1} value={Math.max(1, Math.min(120, fov))} onChange={(e) => setFov(Number(e.target.value))} />
        <input
          type="number"
          step="0.1"
          value={Number.isFinite(fov) ? fov : 60}
          onChange={(e) => {
            const next = Number(e.target.value)
            if (!Number.isFinite(next) || next <= 0) return
            setFov(next)
          }}
          style={{ width: 64 }}
        />
        <span>{fov}deg</span>
      </div>

      <button
        onClick={handleRegenerate}
        className="primary"
      >
        Regenerate
      </button>
      <button onClick={takePhoto} className="primary">Take Photo</button>
    </div>
  )
}
