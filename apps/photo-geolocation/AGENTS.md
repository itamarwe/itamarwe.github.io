# Photo Geolocation Tool - Agent Guide

## Why this repo exists

This project is a controlled testbed for photo geolocation.

The app generates synthetic urban scenes (boxes/buildings), renders a camera view ("photo"), and shows a 2D orthophoto-style map of the same world. A user picks corresponding anchors in the photo and map, then runs pose estimators to compare:
- estimated camera position on map
- actual camera position on map (ground truth, display only)

Primary goal: evaluate localization algorithms in a clean, reproducible setup.

## Product model (important)

There are two strict phases:

1. Photo generation (edit mode)
- Inputs: seed, building count, camera params, FOV.
- Output: a frozen photo capture and image size.

2. Pose estimation (view mode)
- Inputs allowed: `anchors[].photoPixel`, `anchors[].mapPoint`, `photo.width`, `photo.height`.
- Inputs forbidden: capture camera pose, live scene camera, scene internals, FOV priors.

This separation should be enforced in code structure, not only by UI.

## Current repo status (Apr 2026)

- Tooling: Vite + React + Zustand + Three.js + React Three Fiber.
- Multi-page app wiring exists:
  - `index.html` redirects to `v1.html`
  - `v0.html` loads `src/v0/main.jsx`
  - `v1.html` expects `src/v1/main.jsx`
- `v0` is the working baseline implementation.
- `v1` is partially scaffolded:
  - present: `src/v1/photoState.js`, `src/v1/cameraState.js`, `src/v1/poseState.js`, `src/v1/pose/algorithms.js`
  - missing: `src/v1/main.jsx`, `src/v1/App.jsx`, components, store wiring, registry/UI flow

## Existing architecture snapshot

### v0 (working baseline)

- Global state in `src/v0/store.js` with scene, camera FOV, anchors, and enabled estimators.
- Main layout in `src/v0/App.jsx`:
  - 3D viewport
  - 2D map
  - anchor and pose side panels
  - controls footer
- Pose registry in `src/v0/pose/registry.js`.
- Shared utilities under `src/shared/utils/` for scene generation and anchor color handling.

### v1 (new boundary design, in progress)

- `photoState` splits:
  - `_capture`: frozen scene/camera info for rendering photo view only
  - `image`: width/height exposed to estimation pipeline
- `cameraState`: mutable scene camera while editing only.
- `poseState`: estimator outputs for panel/map rendering.
- `pose/algorithms.js` currently includes:
  - Centroid baseline
  - Joint Gauss-Newton (pose + focal)
  - Ratio Gauss-Newton (intrinsics-free)
- Design intent: algorithm modules remain blind to scene/capture camera.

## Algorithm lineup for v1

Keep exactly these three:
- A: Centroid (min anchors 1)
- B: Joint GN pose + focal (min anchors 4)
- C: Ratio GN intrinsics-free (min anchors 4)

Removed and should not return:
- Snellius-Pothenot assumed-FOV variants
- any assumed-FOV store field or UI

## Hard invariants

1. No leakage from capture state into estimators.
2. Ground truth is display-only (red dot + error metrics), never estimator input.
3. After "Take Photo", scene edit controls are hidden until re-entering edit mode.
4. If photo anchors exist and user edits scene, confirm and clear photo-side anchors.
5. Estimator availability/row state respects min-anchor thresholds.

## Recommended v1 file structure

Keep files short and story-like (high-level first), split by concern.

- `src/v1/main.jsx`
- `src/v1/App.jsx`
- `src/v1/store/`
  - `uiStore.js` (mode, panel state, viewport size)
  - `anchorStore.js` (anchor CRUD and selection)
- `src/v1/state/`
  - `photoState.js`
  - `cameraState.js`
  - `poseState.js`
- `src/v1/components/`
  - `PhotoView.jsx`
  - `Map2D.jsx`
  - `AnchorPanel.jsx`
  - `PosePanel.jsx`
  - `TopBar.jsx`
- `src/v1/pose/`
  - `algorithms.js`
  - `registry.js`
  - `buildObservations.js` (optional extraction)

## Gradual implementation plan

### Step 1 - Stabilize entry points
- Ensure `v1.html` boots cleanly with `src/v1/main.jsx`.
- Render a minimal `App` shell with empty placeholders.
- Confirm `v0.html` still works unchanged.

### Step 2 - Implement v1 app skeleton
- Build top-level layout: photo pane, map pane, side pane.
- Add default "view mode" launch behavior.
- Add top-right "Edit Scene" action.

### Step 3 - Add photo generation and freeze flow
- Implement edit mode controls: seed, building count, camera orbit, FOV.
- Add "Take Photo" to freeze to `photoState._capture`.
- Compute `photoState.image` width/height from viewport and keep stable.

### Step 4 - Add anchors and mode-safe clearing
- Anchor model supports both `photoPixel` and `mapPoint`.
- On entering edit mode with existing photo anchors, show confirm dialog.
- If confirmed, clear photo-side anchors and keep map anchors if intended.

### Step 5 - Hook map/photo interaction
- Photo click places/updates selected anchor pixel coordinates.
- Map click places/updates selected anchor map coordinates.
- Visual feedback for selected/complete/incomplete anchors.

### Step 6 - Integrate estimator pipeline
- Build observations from completed anchors.
- Wire registry for A/B/C algorithms only.
- Pass estimator input contract:
  - observations with `photoX` and map points
  - `photoWidth`, `photoHeight`
- Explicitly avoid imports from capture/camera state into `pose/algorithms.js`.

### Step 7 - Pose display and diagnostics
- Draw actual camera marker from capture state (display-only channel).
- Draw estimator markers and compute errors:
  - position error
  - heading error when available
  - FOV error only when algorithm outputs it
- Gray out rows below min-anchor thresholds.

### Step 8 - Verification pass
- Manual scenarios: sparse anchors, degenerate anchor geometry, retake flow, resize behavior.
- Ensure no estimator accesses forbidden state.
- Add smoke checks for all pages (`/`, `/v0.html`, `/v1.html`).

## Practical coding rules for agents

- Prefer small functions with one level of abstraction.
- Return early over nested conditionals.
- Keep comments minimal and meaningful.
- Keep files under ~200 lines; split modules aggressively when needed.
- Do not refactor v0 unless needed for shared utilities or build wiring.
- Avoid mixing v0 compatibility concerns into v1 estimator logic.

## Definition of done for current "v1 boundary" milestone

1. `v1` boots and is usable end-to-end.
2. User can edit scene, take photo, and then place anchors in photo+map.
3. Only A/B/C estimators run; each respects min anchors.
4. Ground-truth dot is shown but not used by estimation.
5. Clear evidence in module boundaries that estimation sees only photo rectangle + anchor correspondences.
