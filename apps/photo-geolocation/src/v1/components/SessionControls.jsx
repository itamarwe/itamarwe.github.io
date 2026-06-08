import { useRef } from 'react'
import { useStore } from '../store'
import styles from './SessionControls.module.css'

/** Read an object/blob URL back into a portable base64 data URL. */
async function urlToDataUrl(url) {
  const res = await fetch(url)
  const blob = await res.blob()
  return await new Promise((resolve, reject) => {
    const fr = new FileReader()
    fr.onload = () => resolve(fr.result)
    fr.onerror = () => reject(fr.error)
    fr.readAsDataURL(blob)
  })
}

function timestamp() {
  return new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
}

/**
 * Save / load the whole working session as a single self-contained .json file.
 * The uploaded photo is embedded as a base64 data URL so the file is portable
 * (no broken object-URL references), alongside every anchor, the enabled
 * estimators, and the map framing. Lives in the top navigation bar as icons.
 */
export default function SessionControls() {
  const fileRef = useRef(null)
  const hasPhoto = useStore((s) => Boolean(s.photoUrl))

  async function handleSave() {
    const s = useStore.getState()
    let photo = null
    if (s.photoUrl) {
      try { photo = await urlToDataUrl(s.photoUrl) } catch { photo = null }
    }
    const session = {
      app: 'geophoto-tlv',
      version: 1,
      savedAt: new Date().toISOString(),
      origin: s.origin,
      radiusMeters: s.radiusMeters,
      anchors: s.anchors,
      activeAnchorId: s.activeAnchorId,
      nextAnchorId: s.nextAnchorId,
      enabledEstimators: [...s.enabledEstimators],
      image: s.image,
      photoName: s.photoName,
      photo,
    }
    const blob = new Blob([JSON.stringify(session)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `geophoto-session-${timestamp()}.json`
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => { try { URL.revokeObjectURL(url) } catch { /* ignore */ } }, 0)
    useStore.getState().markSaved()
  }

  function onFile(event) {
    const file = event.target.files?.[0]
    event.target.value = '' // allow re-loading the same file
    if (!file) return
    const fr = new FileReader()
    fr.onload = () => {
      try {
        const data = JSON.parse(fr.result)
        useStore.getState().loadSession(data)
      } catch {
        // eslint-disable-next-line no-alert
        alert('Could not read this session file — it may be corrupt or not a GeoPhoto session.')
      }
    }
    fr.readAsText(file)
  }

  return (
    <span className={styles.group}>
      <button type="button" className={styles.iconBtn} title={hasPhoto ? 'Save session' : 'Upload a photo first'} aria-label="Save session" onClick={handleSave} disabled={!hasPhoto}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
          <polyline points="17 21 17 13 7 13 7 21" />
          <polyline points="7 3 7 8 15 8" />
        </svg>
      </button>
      <button type="button" className={styles.iconBtn} title="Load session" aria-label="Load session" onClick={() => fileRef.current?.click()}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          <polyline points="12 17 12 11" />
          <polyline points="9 14 12 11 15 14" />
        </svg>
      </button>
      <input
        ref={fileRef}
        type="file"
        accept="application/json,.json"
        onChange={onFile}
        style={{ display: 'none' }}
      />
    </span>
  )
}
