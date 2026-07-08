# FPV Dataset viewer (`/fpv`)

Read-only viewer for the [FPV drone strikes Lebanon dataset](https://github.com/itamarwe/fpv-drone-strikes-lebanon-dataset):
a video gallery, video pages with flight annotations, and a 3D point-cloud
viewer with playback, speed/height charts, and measurement.

Vite + React + three.js, styled after the site. Built into `public/fpv/` by the
site build (`npm run build:fpv-viewer`) and served at `/fpv` via the rewrites in
`next.config.ts` — same pattern as `apps/photo-geolocation`.

## Data

The app is fully static; **all data comes from CloudFront at runtime**:

- `data/videos.json` — the manifest (video list, annotations, scene index)
- `videos/`, `thumbnails/` — media
- `scenes/<slug>/<scene-id>/viewer/` — 3D scene data

**Updating the data does not require touching this repo.** In the dataset repo,
run `npm run publish-web` (or `publish-web:fast` for annotation/list-only
changes). The manifest is cached for 5 minutes, so changes appear on the site
shortly after publishing. See the dataset repo's README for details.

Env overrides for testing: `VITE_DATA_URL`, `VITE_SCENE_BASE`, `VITE_THUMB_BASE`.

## Development

```bash
cd apps/fpv-viewer
npm ci
npm run dev     # http://localhost:5185 — reads live CDN data
```
