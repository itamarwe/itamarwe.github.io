#!/usr/bin/env bash
# Assemble public/img/fpv-viewer/viewer-demo.mp4 — the guided tour of the /fpv
# viewer (gallery -> flight-annotated player -> reconstructed 3-D scene), using
# the Biranit / Iron Dome strike as the demo clip.
#
# Prereqs:
#   - The viewer dev server running at http://localhost:5185 (serves scenes &
#     thumbnails from local disk):  cd apps/fpv-viewer && npm run dev   (in the
#     fpv-drone-strikes-lebanon-dataset repo, fpv-video-quality branch).
#   - Playwright + ffmpeg available (the site repo has both).
#
# Steps:
#   1. Record each interface after it is fully loaded (setup dead-time is at the
#      FRONT of each webm, so we trim to the last N seconds of "action").
#   2. Burn a small caption pill onto each clip and cross-fade them together.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out

# 1. record the three segments (gallery + scene) and the video segment
node capture_segments.mjs
node capture_video.mjs      # video segment scrolls the flight-annotation ribbon into view

G=$(ls out/gallery/*.webm); V=$(ls out/video/*.webm); S=$(ls out/scene/*.webm)
FF="-an -vf scale=1280:800,fps=30 -c:v libx264 -pix_fmt yuv420p -crf 22"
ffmpeg -y -sseof -3.6 -i "$G" $FF out/g.mp4
ffmpeg -y -sseof -5.2 -i "$V" $FF out/v.mp4
ffmpeg -y -sseof -5.2 -i "$S" $FF out/s.mp4

# 2. caption pills (transparent PNGs) — drawtext isn't compiled into brew ffmpeg
python3 - <<'PY'
from PIL import Image, ImageDraw, ImageFont
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 30)
caps = [("out/cap0", "Browse the gallery"), ("out/cap1", "Read the flight edit"),
        ("out/cap2", "Fly the reconstructed 3-D scene")]
for name, text in caps:
    d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    W, H = (r - l) + 44, (b - t) + 24
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dr.rounded_rectangle([0, 0, W - 1, H - 1], radius=H // 2,
                         fill=(0, 0, 0, 160), outline=(255, 255, 255, 40), width=1)
    dr.text((22 - l, 12 - t), text, font=font, fill=(255, 255, 255, 255))
    im.save(name + ".png")
PY

ffmpeg -y -i out/g.mp4 -i out/v.mp4 -i out/s.mp4 \
  -i out/cap0.png -i out/cap1.png -i out/cap2.png -filter_complex "
[0:v][3:v]overlay=40:40[c0];
[1:v][4:v]overlay=40:40[c1];
[2:v][5:v]overlay=40:40[c2];
[c0][c1]xfade=transition=fade:duration=0.5:offset=3.1[x1];
[x1][c2]xfade=transition=fade:duration=0.5:offset=7.8[v]
" -map "[v]" -c:v libx264 -pix_fmt yuv420p -crf 22 -movflags +faststart \
  ../../../public/img/fpv-viewer/viewer-demo.mp4

echo "wrote public/img/fpv-viewer/viewer-demo.mp4"
