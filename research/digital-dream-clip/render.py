"""Render a synthwave audio-reactive music video for 'Digital Dream' by giladchat.

Scene: neon sunset sun on the horizon, a city skyline whose towers act as a
reactive equaliser, a retro perspective grid floor that scrolls with the music,
a twinkling starfield, and a shimmering reflection below the horizon.

Frames are streamed as raw RGB24 to stdout for ffmpeg to mux with the audio.
Reactivity is driven entirely by features.npz (real audio analysis).

Usage:
  render.py                 -> stream all frames as rawvideo to stdout
  render.py --preview T     -> write preview_T.png for time T seconds (to stderr-safe)
"""
import sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
HORIZON = int(H * 0.60)
FPS = 30

# ---- palette (neon) ----
PINK   = (255, 60, 160)
MAG    = (255, 40, 120)
CYAN   = (63, 193, 255)
PURPLE = (180, 140, 255)
GOLD   = (255, 209, 102)
ORANGE = (255, 120, 70)

D = np.load("features.npz")
NF = int(D["nframes"])
BARS = D["bars"]; NBARS = BARS.shape[1]
RMS, LOW, MID, HIGH = D["rms"], D["low"], D["mid"], D["high"]
BEAT, FLUX = D["beat"], D["flux"]
DUR = float(D["dur"])

FONT_DIR = "/usr/share/fonts/truetype/liberation/"
def font(sz, bold=True):
    f = FONT_DIR + ("LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf")
    return ImageFont.truetype(f, sz)

# ---- static sky gradient (vertical) ----
def build_sky():
    top = np.array([8, 3, 22], float)       # deep indigo
    hor = np.array([70, 12, 74], float)      # magenta horizon glow
    bot = np.array([4, 2, 12], float)        # near black floor
    sky = np.zeros((H, W, 3), float)
    ys = np.arange(H)
    for y in ys:
        if y < HORIZON:
            t = y / HORIZON
            c = top*(1-t) + hor*t
        else:
            t = (y-HORIZON)/(H-HORIZON)
            c = hor*(1-t)*0.5 + bot*(0.5+0.5*t)
        sky[y] = c
    return (sky/255.0).astype(np.float32)
SKY = build_sky()

# static vignette (precomputed once)
_yy, _xx = np.mgrid[0:H, 0:W]
VIG = np.clip(1 - 0.35*(((_xx-W/2)/(W/2))**2 + ((_yy-H/2)/(H/2))**2), 0.35, 1)[..., None].astype(np.float32)
_COLIDX = np.arange(W)[None, :]

# ---- starfield ----
rng = np.random.default_rng(7)
NSTAR = 260
star_x = rng.integers(0, W, NSTAR)
star_y = (rng.random(NSTAR) ** 1.7 * (HORIZON - 20)).astype(int)
star_ph = rng.random(NSTAR) * math.tau
star_br = 0.3 + 0.7 * rng.random(NSTAR)
star_col = np.where(rng.random(NSTAR)[:, None] > 0.7, np.array(CYAN), np.array([255, 235, 245]))

# ---- skyline building layout (static x positions & widths & depth) ----
rng2 = np.random.default_rng(21)
NB = NBARS
build_w = W / NB
# assign a base height profile so skyline isn't flat when quiet
base_prof = 0.25 + 0.20 * np.abs(np.sin(np.linspace(0, math.pi, NB) * 1.3)) + 0.12*rng2.random(NB)
depth = rng2.random(NB)  # 0 far .. 1 near, affects brightness

def lerp(a, b, t):
    return tuple(int(a[i]*(1-t)+b[i]*t) for i in range(3))

def draw_sun(draw, cx, cy, R, pulse):
    # vertical gradient disc (pink top -> gold bottom) with scanline gaps in lower half
    steps = 60
    for i in range(steps):
        t = i/steps
        y0 = cy - R + t*2*R
        y1 = cy - R + (i+1)/steps*2*R
        col = lerp(PINK, GOLD, t)
        # widen darkening near edges via circle mask handled by clipping ellipse per band
        dx = math.sqrt(max(R*R - (y0-cy)**2, 0))
        draw.rectangle([cx-dx, y0, cx+dx, y1+1], fill=col)
    # scanline gaps (retro) in lower 55%
    ng = 9
    for i in range(ng):
        yy = cy - R*0.05 + i*(R*1.05/ng)
        gap = 2 + i*0.7
        draw.rectangle([cx-R, yy, cx+R, yy+gap], fill=(6,3,16))

def render_frame(fi):
    t = fi / FPS
    rms = float(RMS[fi]); low=float(LOW[fi]); mid=float(MID[fi]); high=float(HIGH[fi])
    beat=float(BEAT[fi]); flux=float(FLUX[fi]); bars=BARS[fi]

    img = SKY.copy()

    # --- stars (twinkle with high band) ---
    tw = 0.5 + 0.5*np.sin(star_ph + t*2.5)
    sb = star_br * (0.4 + 0.6*tw) * (0.7 + 0.6*high)
    sb = np.clip(sb, 0, 1)
    img[star_y, star_x] = np.clip(img[star_y, star_x] + star_col*sb[:, None]/255.0, 0, 1)

    # everything neon drawn on an RGBA layer for glow
    layer = Image.new("RGB", (W, H), (0, 0, 0))
    dr = ImageDraw.Draw(layer)

    # --- sun --- (large backdrop rising above the skyline)
    R = int(120 + 12*low + 16*beat)
    scx, scy = W//2, HORIZON - 52
    draw_sun(dr, scx, scy, R, beat)

    # --- skyline EQ towers ---
    smooth_bars = bars.copy()
    heights = (base_prof*0.42 + bars*0.72 + 0.08*rms)
    heights = np.clip(heights, 0, 1.0)
    for b in range(NB):
        x0 = b*build_w; x1 = x0+build_w-2
        h = heights[b] * (HORIZON*0.40)
        y0 = HORIZON - h
        # tower colour depends on band index (bass=pink -> treble=cyan) and depth
        cc = lerp(MAG, CYAN, b/(NB-1))
        bri = 0.35 + 0.65*depth[b]
        col = tuple(int(c*bri) for c in cc)
        dr.rectangle([x0, y0, x1, HORIZON], fill=col)
        # bright rim / windows
        rim = lerp(cc, (255,255,255), 0.35)
        dr.rectangle([x0, y0, x1, y0+2], fill=rim)
        # window dots
        wy = y0+6
        while wy < HORIZON-3:
            if (int(wy)+b) % 3 == 0:
                dr.rectangle([x0+2, wy, x0+3, wy+1], fill=GOLD)
            wy += 7

    layer_np = np.asarray(layer, np.float32)/255.0

    # --- reflection of sun+skyline into the floor ---
    top_region = layer_np[:HORIZON]
    refl = top_region[::-1].copy()
    rh = refl.shape[0]
    fade = np.linspace(0.55, 0.0, rh)[:, None, None]
    # horizontal shimmer: roll each row by a sine offset (vectorised gather)
    off = (6*np.sin(np.arange(rh)/9.0 + t*4)*(0.6+0.8*rms)).astype(int)
    cols = (_COLIDX - off[:, None]) % W
    refl = refl[np.arange(rh)[:, None], cols]
    refl *= fade
    fy0 = HORIZON
    fy1 = min(H, HORIZON+rh)
    reg = np.zeros((H, W, 3), np.float32)
    reg[fy0:fy1] = refl[:fy1-fy0]

    # --- grid floor ---
    grid = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(grid)
    gcol = lerp(CYAN, PURPLE, 0.3)
    vx = W//2
    # vertical converging lines
    NVL = 22
    for i in range(-NVL, NVL+1):
        bx = vx + i*(W/ (NVL))
        gd.line([(vx, HORIZON), (bx, H)], fill=gcol, width=1)
    # horizontal scrolling lines (perspective). phase scroll speed reacts to energy
    phase = (t*(0.35+0.9*rms)) % 1.0
    NHL = 16
    for i in range(NHL):
        f = (i+phase)/NHL
        yy = HORIZON + (H-HORIZON)*(f**2.2)
        b = 0.25 + 0.75*(f)
        gd.line([(0, yy), (W, yy)], fill=tuple(int(c*b) for c in gcol), width=1)
    grid_np = np.asarray(grid, np.float32)/255.0

    # --- composite ---
    out = img  # reuse
    # reflection (screen-ish add) in floor
    out[fy0:] = np.clip(out[fy0:] + reg[fy0:]*0.9, 0, 1)
    # grid add
    out = np.clip(out + grid_np*0.55, 0, 1)
    # neon content add (above horizon dominant)
    out = np.clip(out + layer_np*1.0, 0, 1)

    # --- glow pass ---
    bright = (layer_np*255).astype(np.uint8)
    gimg = Image.fromarray(bright).filter(ImageFilter.GaussianBlur(9))
    glow = np.asarray(gimg, np.float32)/255.0
    out = 1 - (1-out)*(1-glow*0.75)   # screen blend

    # extra beat bloom on sun
    if beat > 0.15:
        b2 = Image.fromarray(bright).filter(ImageFilter.GaussianBlur(20))
        out = 1 - (1-out)*(1-np.asarray(b2,np.float32)/255.0*0.5*beat)

    out = np.clip(out, 0, 1)

    # --- text overlay (title card + persistent lower-third) ---
    ov = Image.new("RGBA", (W, H), (0,0,0,0))
    od = ImageDraw.Draw(ov)
    # intro title card: 1.5s -> 8s big centred, then fade to corner
    def neon_text(d, xy, txt, fnt, col, anchor="mm", glow_a=180):
        d.text(xy, txt, font=fnt, fill=col+(255,), anchor=anchor)
    if t < 9.0:
        a = 1.0
        if t < 1.5: a = t/1.5
        elif t > 7.0: a = max(0, (9.0-t)/2.0)
        f1 = font(88); f2 = font(34, bold=False)
        alpha = int(255*a)
        od.text((W//2, H//2-24), "DIGITAL DREAM", font=f1, fill=PINK+(alpha,), anchor="mm")
        od.text((W//2, H//2+44), "giladchat", font=f2, fill=CYAN+(alpha,), anchor="mm")
    else:
        f1 = font(40); f2 = font(24, bold=False)
        a = min(1.0, (t-9.0)/1.5)
        alpha = int(220*a)
        od.text((46, H-70), "DIGITAL DREAM", font=f1, fill=PINK+(alpha,), anchor="lm")
        od.text((48, H-38), "giladchat", font=f2, fill=CYAN+(alpha,), anchor="lm")
    # glow for text
    txt_rgb = np.asarray(ov.convert("RGB"), np.float32)/255.0
    tglow = np.asarray(Image.fromarray((txt_rgb*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)),np.float32)/255.0
    out = 1 - (1-out)*(1-tglow*0.6)
    # hard text on top
    amask = np.asarray(ov.split()[3], np.float32)/255.0
    out = out*(1-amask[...,None]) + txt_rgb*amask[...,None]

    # --- vignette + beat flash ---
    out = out*VIG*(1+0.06*beat)
    out = np.clip(out, 0, 1)

    return (out*255).astype(np.uint8)

def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--preview":
        tsec = float(sys.argv[2])
        fi = min(NF-1, int(tsec*FPS))
        arr = render_frame(fi)
        Image.fromarray(arr).save(f"preview_{int(tsec)}.png")
        print(f"wrote preview_{int(tsec)}.png (frame {fi})", file=sys.stderr)
        return
    out = sys.stdout.buffer
    for fi in range(NF):
        out.write(render_frame(fi).tobytes())
        if fi % 300 == 0:
            print(f"frame {fi}/{NF}", file=sys.stderr)

if __name__ == "__main__":
    main()
