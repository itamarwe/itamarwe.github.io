import { useState } from 'react'
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

// Mobile shows one pane at a time, chosen by the tab bar below; desktop keeps
// the side-by-side layout and ignores this state (the tab bar is hidden via
// CSS). Every pane stays mounted regardless — only `data-mobile-view` toggles
// which one is visible — so the map's render loop and each view's pan/zoom
// state survive switching tabs.
const TABS = [
  { id: 'photo', icon: '📷', label: 'Photo' },
  { id: 'map', icon: '🗺️', label: 'Map' },
  { id: 'anchors', icon: '📍', label: 'Anchors' },
]

export default function App() {
  const [mobileView, setMobileView] = useState('photo')

  return (
    <div className={styles.shell} data-mobile-view={mobileView}>
      <header className={styles.header}>
        <span className={styles.logo}>📍 GeoPhoto Tool</span>
        <span className={styles.subtitle}>Tel Aviv photo geolocation</span>
        <span className={styles.badges}>
          <SessionControls />
        </span>
      </header>

      <nav className={styles.tabs} aria-label="Switch view">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`${styles.tab} ${mobileView === tab.id ? styles.tabActive : ''}`}
            aria-pressed={mobileView === tab.id}
            onClick={() => setMobileView(tab.id)}
          >
            <span className={styles.tabIcon} aria-hidden="true">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </nav>

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
