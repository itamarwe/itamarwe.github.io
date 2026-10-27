# Tiny Tel Aviv web export and sharing assets

The viewer streams the latest scene from the local Tiny Tel Aviv Claude session,
`out/orbit_v2/tiny_tel_aviv_pilot_day.blend` (source commit `2b17063`): the street-level
round with roof items (solar heaters, AC units, water tanks), municipal street
furniture (lights, Tel-O-Fun stations), kerb paint, balconies, shopfronts, Hebrew
signs, bollards, zebra crossings, and static people and vehicles on every street.
`model-source.json` records the source commit, scene hash, model version, byte total
and real counts from the export. The source project and large Blender inputs remain
in the separate Tiny Tel Aviv project/data directories; they are not needed to
build or serve this website.

## Streaming model: how it is tiled, and why

The reference for this is how [tiny.london](https://tiny.london/) and
[isometric.nyc](https://cannoneyed.com/projects/isometric-nyc) serve their maps: one
canvas cut into a Deep Zoom pyramid of 512 px tiles, viewed with OpenSeadragon.
The viewer shows a coarse level everywhere, fetches sharp tiles only under the
view, keeps coarser levels resident so zooming never shows holes, and ships each
version in an immutable folder with immutable cache headers. That works for a
picture; a 3-D scene needs the same idea in geometry, so the export
(`export_web.py`) writes one content-addressed folder,
`public/tiny-tlv/model/<version>/`, with:

- `base.glb` (about 4.6 MB): the ground, every building and landmark, the tower,
  facade detail, and a decimated stand-in copy of every tree, grouped per grid cell
  under an empty named `coarse_trees_<i>_<j>`. It paints first, in a few seconds.
- `tiles/<i>_<j>.glb` (16 files, 1.7 to 3.3 MB each): the full-detail content of one
  117 m grid cell, which is everything the base leaves out: the LOD2 trees, roof
  items, street furniture, kerb paint, balconies, signs, bollards, people and
  vehicles. Meshes that span several cells (kerb paint, bollards, roof items) are
  cut per cell by face centroid; small or instanced objects go whole into the cell
  of their bounding-box centre. Trees and vehicles are written with
  `EXT_mesh_gpu_instancing`, so each tile draws them as instanced meshes.
- `manifest.json`: the grid, the tile centres, byte sizes, SHA-256 hashes, triangle
  counts, and the real object counts shown in the viewer's statistics.

The viewer (`public/tiny-tlv/index.html`) loads the manifest, shows the base, then
streams tiles four at a time, nearest to the orbit target first with a bonus for
tiles inside the view frustum, re-sorting the queue as the camera moves. When a
tile arrives its coarse trees in the base are hidden. If frames stay slow (phones,
integrated GPUs) a governor keeps detail tiles only near the camera and shows the
coarse trees elsewhere, like a map that keeps coarse levels under the view. The
folder name is a hash of every file in it, so `next.config.ts` serves everything
under `/tiny-tlv/model/<version>/` with a one-year immutable cache; a new export is
a new folder and a new `MODEL_VERSION` in the viewer.

What glTF cannot carry: the CC0 material sets are box-projected on world position
(the meshes have no UVs), so those and every procedural shader (window grids,
paving, asphalt noise) are flattened to their palette colour. Only UV-mapped
photo textures survive: the Commons tower facades (CC BY-SA), the CC0/CC-BY vehicle
kits, and the sign faces. The internal orthophoto roof texture is replaced with a
plain roof tone. This is the actual web model, not a screenshot of the richer
Blender render.

## Model export

From the repository root, with Blender installed:

```sh
blender -b --factory-startup --disable-autoexec /path/to/tiny_tel_aviv_pilot_day.blend \
  -P research/tiny-tlv/export_web.py
python3 research/tiny-tlv/validate-model.py
```

Use the source project's `tools/blender_safe.sh` wrapper instead of `blender`
when its macOS memory watchdog is available. The export takes about a minute and
prints `TTLV_VERSION <hash>`; set that hash as `MODEL_VERSION` in
`public/tiny-tlv/index.html`, copy the manifest's version, byte total, counts and
scene hash into `model-source.json`, and delete the previous version folder (the
repository ships exactly one). Validation checks the viewer, the manifest, every
GLB's size and hash, that each file is self-contained with no orthophoto texture,
instance-aware triangle counts, and that `model-source.json` matches.

## Social images

The committed captures are `public/img/tiny-tlv/social.png` (1200×630, used by
OpenGraph and Twitter) and `social-square.png` (1080×1080, for manual sharing).
Both show the actual shipped WebGL model on a black canvas. They contain no
Mappa branding or internal orthophoto imagery. The wide image's URL, dimensions,
and alt text are in the static HTML head so crawlers need no JavaScript.

Install the existing browser tooling with `npm run build:photo-geolocation`,
then serve `public` and capture from another terminal:

```sh
python3 -m http.server 3018 --bind 127.0.0.1 --directory public
node research/tiny-tlv/capture-social.cjs http://127.0.0.1:3018
```

If Playwright's Chromium is not installed, set `CHROME_BIN` to an installed
Chrome/Chromium executable. On macOS, for example:

```sh
CHROME_BIN='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  node research/tiny-tlv/capture-social.cjs http://127.0.0.1:3018
```

Capture injects its camera handle and typography only into the local browser
response. It never changes the viewer's runtime layout or adds a public capture
mode. Reduced motion freezes rotation, and the script waits for the model and
fonts before taking the images. The original Google Fonts require network access
for matching typography. All output paths are derived from the script location.

## Looping website video

`capture-orbit.cjs` records the live website at 1920×1080 and 30 fps. It makes
three complete turns in 36 seconds while easing from a near view to a wide view
and back. The website title, controls, credits, and data remain visible; a URL is
added for people watching the clip outside a browser. Changes to the camera and
capture layout exist only in the local browser response, not on the website.

```sh
CHROME_BIN='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  node research/tiny-tlv/capture-orbit.cjs --preview
CHROME_BIN='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  node research/tiny-tlv/capture-orbit.cjs
```

Requires the same Playwright tooling as the social captures, plus `ffmpeg` on
PATH. Output: `public/img/tiny-tlv/tiny-tlv-orbit.mp4`. Scratch frames and capture
metadata are saved to the ignored `research/tiny-tlv/out/orbit/` directory.
The script pipes actual browser frames into ffmpeg so rendering speed does not
cause dropped or duplicate video frames. It uses H.264, yuv420p, an 8 Mbps peak
rate, and MP4 fast-start metadata. The clip is silent.

The camera path is periodic: azimuth advances by three full turns, while zoom
and elevation follow `sin(pi*t)^2`. The virtual endpoint must be pixel-identical
to the first frame before rendering can continue. That duplicate endpoint is
excluded from the encoded clip, leaving a normal single-frame motion step across
the loop boundary. A video player must still have looping enabled.

## LinkedIn feed loop

The `--linkedin` preset captures a 1080×1080, 30 fps, 13-second MP4 from the same
viewer (live by default, or a local preview via `TINY_TLV_CAPTURE_URL`). The camera
holds an angled view for 3 seconds, rises to 85° over 2.5 seconds, holds overhead for 5 seconds, and returns over 2.5 seconds. Quintic
smootherstep easing gives each transition zero velocity and acceleration at its
ends. One full 360° orbit continues at constant angular speed through every phase,
including the overhead hold. Camera distance (6.5 scene units), target, and field
of view (34°) stay fixed, with no
zoom animation. The same pixel-identical endpoint check runs before encoding.

This pacing follows the repeating map transition on the
[Mappa reference](https://mappalabs.com/?drape=alpine&stereo=off), inspected on
2026-10-26. Its published animation uses the same 3 / 2.5 / 5 / 2.5-second phases
and quintic easing, followed by frame-dependent camera smoothing. This capture
uses deterministic easing directly, adapts the view angles to the city, and adds
a continuous full orbit. It omits the reference's zoom and initial reveal delay.
The 13-second
path and its derivatives close at the loop boundary. No reference branding or
scene assets are included.

```sh
CHROME_BIN='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  node research/tiny-tlv/capture-orbit.cjs --linkedin --preview
CHROME_BIN='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  node research/tiny-tlv/capture-orbit.cjs --linkedin
```

Outputs in `public/img/tiny-tlv/`:

- `tiny-tlv-linkedin-loop.mp4`: square H.264/yuv420p video, silent, with fast-start
  metadata and an 8 Mbps peak bitrate cap.
- `tiny-tlv-linkedin-thumbnail.png`: matching square opening frame for the upload
  thumbnail.

The square composition, larger heading, and persistent URL are designed for
mobile feed viewing without sound. Statistics and inactive controls are hidden
in the capture; the website's title, subtitle, and source credits remain. No
public viewer code is modified. Keep `linkedin-capture.json` with the recorded
source hash and settings. Scratch captures live in `out/linkedin/`.

Upload the MP4 as a native LinkedIn video and optionally select the accompanying
thumbnail. The file has a seamless loop boundary; whether it repeats automatically
is controlled by the platform/player, not an MP4 flag.

Export settings fall within LinkedIn's published native-video limits for
resolution, duration, aspect ratio, frame rate, bitrate, and file size:
[Share videos on LinkedIn](https://www.linkedin.com/help/linkedin/answer/a7494039)
(checked 2026-10-26). Square framing is a design choice for this asset, not a
LinkedIn requirement.

To capture the updated model before deployment, serve `public` locally and set
`TINY_TLV_CAPTURE_URL=http://127.0.0.1:3018/tiny-tlv/` when invoking the video
script. Capture provenance records both the source HTML and model SHA-256, so a
local export can be verified against the committed model.
