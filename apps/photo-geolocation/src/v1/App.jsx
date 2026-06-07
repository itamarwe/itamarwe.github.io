import styles from './App.module.css'
import PhotoUpload from './components/PhotoUpload'
import Map2D from './components/Map2D'
import AnchorPanel from './components/AnchorPanel'
import PosePanel from './components/PosePanel'
import SessionControls from './components/SessionControls'

// PhotoView owns image dimensions: its ResizeObserver and captureVersion
// effects sync image.w/h to the actual frame size. We deliberately do NOT
// call initializePhotoImage from here — doing so used to overwrite the
// frame-derived size with a heuristic `window.innerWidth * 0.5`, leaving
// the photo at half-pane forever in view mode.

export default function App() {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <span className={styles.logo}>📍 GeoPhoto Tool</span>
        <span className={styles.subtitle}>Tel Aviv photo geolocation</span>
        <span className={styles.badges}>
          <SessionControls />
        </span>
      </header>

      <main className={styles.body}>
        <section className={styles.photoPane}><PhotoUpload /></section>
        <section className={styles.mapPane}><Map2D /></section>
        <aside className={styles.sidebar}>
          <AnchorPanel />
          <PosePanel />
        </aside>
      </main>
    </div>
  )
}
