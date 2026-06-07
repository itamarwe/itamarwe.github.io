import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// This app is embedded in the itamar-weiss.com site and served at the
// /photo-geolocation/ sub-path. For the production build we emit relative
// asset URLs (base './') and write straight into the site's public/ dir, so
// `next build` ships the result at /photo-geolocation/. In dev (`vite`) we
// keep the root base so http://localhost:5173/ works as before.
export default defineConfig(({ command }) => ({
  base: command === 'build' ? './' : '/',
  build: {
    outDir: '../../public/photo-geolocation',
    emptyOutDir: true,
  },
  plugins: [react()],
}))
