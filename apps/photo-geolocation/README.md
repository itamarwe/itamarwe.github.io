# GeoPhoto Tool

Geolocate a photograph by matching points in the image to known points on a
map, then solving for the camera pose (Perspective-n-Point).

The **v1** app (the active one) is a Tel Aviv geolocation tool: upload a photo
you took in TLV, drop anchors on building corners in both the photo and a real
map with building heights, and the Full-PnP pipeline estimates where the camera
was standing.

## Getting started

Requires Node.js 18+.

```bash
npm install     # install dependencies
npm run dev     # start the Vite dev server (http://localhost:5173)
```

Then open:

- **http://localhost:5173/** — redirects to v1
- **http://localhost:5173/v1.html** — Tel Aviv photo geolocation (current)
- **http://localhost:5173/v0.html** — earlier synthetic-scene prototype

### Other commands

```bash
npm run build     # production build into dist/
npm run preview   # serve the production build locally
```

## Using v1

1. **Upload a photo** in the left pane (click or drag-and-drop) — a picture you
   took in central Tel Aviv.
2. The right pane loads a real map with **OpenStreetMap building footprints and
   heights** for the default area (see below).
3. Click **+ Add** to create an anchor, then click the same physical point
   (e.g. a building corner) in both the photo and on the map. The map click
   auto-fills the anchor's height from the building footprint (rooftop =
   building height, ground = 0); override it in the anchor panel if needed.
4. With enough anchors (Full PnP needs 4, RANSAC 5), the estimated camera
   location is shown as latitude/longitude in the Pose Estimation panel and as
   a marker on the map.

### Map area: fixed default, dynamic-ready

On load, the map fetches buildings for a **fixed default area** centered on
central Tel Aviv:

- origin `32.0773, 34.7818` (Dizengoff / King George) — `DEFAULT_ORIGIN` in
  `src/v1/tlv/geo.js`
- radius `500` m (a 1 km × 1 km box) — `DEFAULT_RADIUS_M` in `src/v1/store.js`

The loader itself is dynamic: `loadTlvArea({ center, radiusMeters })` can target
any location, and `setOrigin()` moves the local coordinate frame. There is not
yet a UI control to recenter the map — "Reload buildings" re-fetches the same
default box.

## How it works

- **Coordinate frame** (`src/v1/tlv/geo.js`): WGS84 lat/lon is converted to a
  local ground-metres frame (equirectangular tangent plane, true scale) that the
  pose solver works in. `x` = east, `z` = -north, `y` = up.
- **Building data** (`src/v1/tlv/buildings.js`): footprints + heights come from
  OpenStreetMap via the **Overpass API**. Heights resolve from the `height` tag,
  else `building:levels × 3.2 m`, else a default. The source sits behind a
  `fetchBuildings(bbox, origin)` adapter so a higher-accuracy source (e.g. the
  Tel Aviv municipality GIS) can be swapped in without touching the solver.
- **Basemap**: CARTO Voyager raster tiles, drawn in the same local-metres
  transform as the footprints. © OpenStreetMap contributors, © CARTO.
- **Pose estimation** (`src/v1/pose/`): 6-DOF Full PnP (Gauss-Newton + LM) and a
  RANSAC variant solve camera `(x, z, height, heading, pitch, focal)` from the
  photo↔map correspondences.

## Tech stack

Vite · React · Zustand. (The v0 prototype additionally uses Three.js /
react-three-fiber for its synthetic 3D scene.)
