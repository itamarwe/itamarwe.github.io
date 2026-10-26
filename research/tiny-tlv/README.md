# Tiny Tel Aviv web export and sharing assets

The viewer uses the latest scene from the local Tiny Tel Aviv Claude session,
`out/orbit_final/tiny_tel_aviv_pilot_day.blend`. `model-source.json` records the
source commit, scene hash, export hash, and real counts from its Blender metadata.
This scene adds the osm2streets roads, detailed trees, and Rothschild buildings.
The source project and large Blender inputs remain in the separate Tiny Tel Aviv
project/data directories; they are not needed to build or serve this website.

## Model export

From the repository root, with Blender installed:

```sh
blender -b --factory-startup --disable-autoexec /path/to/tiny_tel_aviv_pilot_day.blend \
  -P research/tiny-tlv/export_web.py
python3 research/tiny-tlv/validate-model.py
```

Use the source project's `tools/blender_safe.sh` wrapper instead of `blender`
when its macOS memory watchdog is available. The default output is
`public/tiny-tlv/tiny_tel_aviv.glb`; an optional explicit output follows `--`.
The exporter removes cameras, lights, mask objects, and internal orthophoto roof
textures. Seven Commons facade textures are preserved, resized to at most
1024 pixels, and embedded. Procedural Blender materials (including window grids)
remain flattened to base colors, as in the previous artifact export. Roofs use a
plain material. This is the actual web model, not a screenshot of the richer
Blender render. Update the provenance hashes and counts deliberately after a new
export; validation checks them against the actual shipped GLB, including instance
triangle counts and the texture inventory.

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
