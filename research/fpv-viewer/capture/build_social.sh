#!/usr/bin/env bash
# Build the 8 social-media videos for the /fpv viewer from live captures:
#
#   out/social/fpv-tour-linkedin.mp4      1080x1080  gallery→video→scene tour
#   out/social/fpv-tour-twitter.mp4       1280x720
#   out/social/fpv-gallery-{linkedin,twitter}.mp4    scroll / search / filter
#   out/social/fpv-video-{linkedin,twitter}.mp4      a clip playing in the player
#   out/social/fpv-scene-{linkedin,twitter}.mp4      3-D scene playback + orbit
#
# Prereqs: Playwright + ffmpeg (same as build_demo.sh). Records from the LIVE
# site by default; set BASE=http://localhost:5185 to use the local dev server.
set -euo pipefail
cd "$(dirname "$0")"
OUTDIR=out/social
mkdir -p "$OUTDIR"

# 1. record the six source takes (3 scenarios x {16:9, square})
node capture_social.mjs

# 2. trim the setup dead-time (it's at the FRONT; keep the last N seconds of
#    action) and encode per platform. Black pad bars are invisible on the
#    app's black background. The scene take plays the scene start->end twice,
#    so its window is measured by the capture script (2x duration + margin).
GAL_S=13; VID_S=10.5
SCN_S=$(cat out/social-src/scene_keep.txt 2>/dev/null || echo 27)
TW="-vf scale=1280:720:flags=lanczos,fps=30 -c:v libx264 -profile:v high -pix_fmt yuv420p -crf 21 -movflags +faststart -an"
LI="-vf scale=1080:1080:flags=lanczos,fps=30 -c:v libx264 -profile:v high -pix_fmt yuv420p -crf 20 -movflags +faststart -an"

src() { ls out/social-src/"$1"/*.webm; }
ffmpeg -y -sseof -$GAL_S -i "$(src gallery-169)" $TW "$OUTDIR/fpv-gallery-twitter.mp4"
ffmpeg -y -sseof -$GAL_S -i "$(src gallery-sq)"  $LI "$OUTDIR/fpv-gallery-linkedin.mp4"
ffmpeg -y -sseof -$VID_S -i "$(src video-169)"   $TW "$OUTDIR/fpv-video-twitter.mp4"
ffmpeg -y -sseof -$VID_S -i "$(src video-sq)"    $LI "$OUTDIR/fpv-video-linkedin.mp4"
ffmpeg -y -sseof -$SCN_S -i "$(src scene-169)"   $TW "$OUTDIR/fpv-scene-twitter.mp4"
ffmpeg -y -sseof -$SCN_S -i "$(src scene-sq)"    $LI "$OUTDIR/fpv-scene-linkedin.mp4"

# 3. caption pills for the tour (drawtext isn't compiled into brew ffmpeg)
python3 - <<'PY'
from PIL import Image, ImageDraw, ImageFont
import os
FONTS = ["/System/Library/Fonts/Supplemental/Arial.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
font = ImageFont.truetype(next(f for f in FONTS if os.path.exists(f)), 30)
caps = [("out/social/cap0", "Browse the gallery"),
        ("out/social/cap1", "Watch the flight, annotated"),
        ("out/social/cap2", "Explore the 3-D scene")]
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

# 4. tour = the three platform clips cross-faded with caption pills.
#    Segment lengths are the trimmed durations above; offsets are cumulative
#    minus the 0.5 s fades.
tour() { # $1 platform suffix
  local A="$OUTDIR/fpv-gallery-$1.mp4" B="$OUTDIR/fpv-video-$1.mp4" C="$OUTDIR/fpv-scene-$1.mp4"
  local O1 O2
  O1=$(python3 -c "print($GAL_S-0.5)"); O2=$(python3 -c "print($GAL_S+$VID_S-1.0)")
  ffmpeg -y -i "$A" -i "$B" -i "$C" \
    -i "$OUTDIR/cap0.png" -i "$OUTDIR/cap1.png" -i "$OUTDIR/cap2.png" -filter_complex "
[0:v][3:v]overlay=40:40[c0];
[1:v][4:v]overlay=40:40[c1];
[2:v][5:v]overlay=40:40[c2];
[c0][c1]xfade=transition=fade:duration=0.5:offset=$O1[x1];
[x1][c2]xfade=transition=fade:duration=0.5:offset=$O2[v]
" -map "[v]" -c:v libx264 -profile:v high -pix_fmt yuv420p -crf 20 \
    -movflags +faststart -an "$OUTDIR/fpv-tour-$1.mp4"
}
tour twitter
tour linkedin
rm -f "$OUTDIR"/cap*.png

echo "wrote 8 videos to $OUTDIR/"
