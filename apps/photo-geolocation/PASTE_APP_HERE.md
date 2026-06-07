# Photo Geolocation app — paste source here

This directory is the home for the **photo-geolocation** app source
(from `~/Documents/code/photo-geolocation`).

## What to do

1. Copy the contents of `~/Documents/code/photo-geolocation` into this
   directory (`apps/photo-geolocation/`), **excluding**:
   - `node_modules/`
   - any build output (`dist/`, `build/`, `.next/`, etc.)
   - local env files with secrets (`.env`, `.env.local`)
2. Keep the app's own `package.json`, lockfile, source, and config.
3. Commit and push to the `claude/photo-geolocation-app` branch.

Once pushed, I'll:
- Wire the app's build into the site build so `npm run build` also builds
  this app and emits its static output to `public/photo-geolocation/`.
- Add the rewrite + sitemap entry so it's served at `/photo-geolocation/`,
  exactly like `/solar-system/`.
- Delete this placeholder file.
