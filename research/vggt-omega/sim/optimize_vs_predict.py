#!/usr/bin/env python3
"""Split-screen animation: bundle adjustment grinding vs one forward pass.

STYLIZED RE-ENACTMENT (stated in the post): the left panel imitates the look of
an iterative optimizer converging (smooth decaying noise on points/cameras); it
is not real solver output. Right panel: inputs appear, one sweep, scene snaps in.
Output: public/img/vggt-omega/optimize-vs-predict.mp4 (1600x900, h264, loopable).
"""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.animation import FuncAnimation, FFMpegWriter

sys.path.append(os.path.dirname(__file__))
from figures import BG, FG, MUT, CYAN, GOLD, RED, house_cloud

FPS, SECS = 30, 9.0
N_FRAMES = int(FPS * SECS)

P = house_cloud(n=180, seed=3)                      # target scene points
CAMS = [(-5, 11.5, -38), (24, 13, 218), (-4.5, -3, 25), (22, -2.5, 155)]  # x,y,ang->scene

rng = np.random.default_rng(42)

def smooth_noise(n_items, n_keys=10, dim=2):
    """Per-item smooth random paths in [0,1]-time, unit scale."""
    keys = rng.normal(0, 1, (n_keys, n_items, dim))
    def at(t):  # t in [0,1]
        x = t * (n_keys - 1)
        i = int(np.clip(np.floor(x), 0, n_keys - 2)); f = x - i
        f = f*f*(3-2*f)  # smoothstep
        return keys[i]*(1-f) + keys[i+1]*f
    return at

pt_noise = smooth_noise(len(P))
cam_noise = smooth_noise(len(CAMS), dim=3)

def decay(t):          # optimization "progress": fast early, slow late
    return np.exp(-3.2 * t)

fig = plt.figure(figsize=(12.8, 7.2), dpi=125)
fig.patch.set_facecolor(BG)

axL = fig.add_axes([0.015, 0.02, 0.47, 0.86]); axR = fig.add_axes([0.515, 0.02, 0.47, 0.86])
for ax in (axL, axR):
    ax.set_facecolor(BG); ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlim(-14, 30); ax.set_ylim(-6, 20)
    for s in ax.spines.values():
        s.set_visible(True); s.set_color("#1a2029"); s.set_linewidth(1.2)

fig.text(0.25, 0.935, "bundle adjustment", color=GOLD, fontsize=17,
         ha="center", weight="bold")
fig.text(0.75, 0.935, "VGGT-Ω  —  one forward pass", color=CYAN, fontsize=17,
         ha="center", weight="bold")
fig.text(0.5, 0.965, "", color=FG, fontsize=1)  # keep top margin

# ---- left panel artists
scatL = axL.scatter([], [], s=10, c=GOLD, alpha=0.9, zorder=4)
camL = []
for _ in CAMS:
    l1, = axL.plot([], [], color=GOLD, lw=1.4, alpha=0.85, zorder=5)
    l2, = axL.plot([], [], color=GOLD, lw=1.4, alpha=0.85, zorder=5)
    camL.append((l1, l2))
iterTxt = axL.text(0.03, 0.04, "", transform=axL.transAxes, color=GOLD, fontsize=13)

# ---- right panel artists
scatR = axR.scatter([], [], s=10, c=CYAN, alpha=0.0, zorder=4)
camR = []
for _ in CAMS:
    l1, = axR.plot([], [], color=CYAN, lw=1.4, alpha=0.0, zorder=5)
    l2, = axR.plot([], [], color=CYAN, lw=1.4, alpha=0.0, zorder=5)
    camR.append((l1, l2))
thumbs, thumb_pts = [], []
Psub = P[::3]
for i in range(3):
    r = Polygon([(0, 0)], closed=True, facecolor="#10141b", edgecolor=MUT,
                lw=1.2, alpha=0.0, zorder=6)
    axR.add_patch(r); thumbs.append(r)
    # a tiny "photo" of the scene inside each thumbnail, slightly shifted per view
    x0, y0, w, h = -13.2, 15.5 - i*5.6, 6.5, 4.4
    sh = (i - 1) * 0.35
    tx = x0 + 0.5 + (Psub[:, 0] + 8 + sh*4) / 27 * (w - 1.0)
    ty = y0 + 0.5 + (Psub[:, 1] + 2) / 13 * (h - 1.0)
    sc = axR.scatter(tx, ty, s=1.5, c=MUT, alpha=0.0, zorder=7)
    thumb_pts.append(sc)
sweep, = axR.plot([], [], color=CYAN, lw=2.5, alpha=0.0, zorder=7)
passTxt = axR.text(0.72, 0.06, "", transform=axR.transAxes, color=CYAN,
                   fontsize=15, weight="bold")

def frustum_lines(x, y, ang, ln=5.0, spread=16):
    th = np.radians(ang)
    a1, a2 = np.radians(ang-spread), np.radians(ang+spread)
    return ([x, x+ln*np.cos(a1)], [y, y+ln*np.sin(a1)],
            [x, x+ln*np.cos(a2)], [y, y+ln*np.sin(a2)])

def update(k):
    t = k / N_FRAMES
    # ---------- LEFT: converging optimizer
    d = decay(t)
    jitter = 0.14 * d * rng.normal(0, 1, P.shape)      # per-frame shiver
    off = pt_noise(t) * 6.5 * d + jitter
    scatL.set_offsets(P + off)
    cd = cam_noise(t) * np.array([7, 7, 55]) * d
    for (l1, l2), (cx, cy, ca), dv in zip(camL, CAMS, cd):
        x1, y1, x2, y2 = frustum_lines(cx+dv[0], cy+dv[1], ca+dv[2])
        l1.set_data(x1, y1); l2.set_data(x2, y2)
    iterTxt.set_text(f"iteration {int(t*2400):,}")
    # ---------- RIGHT: inputs, one sweep, snap
    ts = t * SECS
    for i, (th, tp) in enumerate(zip(thumbs, thumb_pts)):
        a = np.clip((ts - 0.4*i - 0.2) / 0.35, 0, 1)
        x0, y0, w, h = -13.2, 15.5 - i*5.6, 6.5, 4.4
        th.set_xy([(x0, y0), (x0+w, y0), (x0+w, y0+h), (x0, y0+h)])
        th.set_alpha(0.85 * a)
        tp.set_alpha(0.9 * a)
    sw = np.clip((ts - 2.0) / 0.6, 0, 1)
    if 0 < sw < 1:
        sx = -14 + 44 * sw
        sweep.set_data([sx, sx], [-6, 20]); sweep.set_alpha(0.9 * np.sin(np.pi*sw))
    else:
        sweep.set_alpha(0.0)
    snap = np.clip((ts - 2.35) / 0.35, 0, 1)
    scatR.set_offsets(P); scatR.set_alpha(0.9 * snap)
    for (l1, l2), (cx, cy, ca) in zip(camR, CAMS):
        x1, y1, x2, y2 = frustum_lines(cx, cy, ca)
        l1.set_data(x1, y1); l2.set_data(x2, y2)
        l1.set_alpha(0.85*snap); l2.set_alpha(0.85*snap)
    passTxt.set_text("1 pass  ✓" if ts > 2.75 else "")
    return []

anim = FuncAnimation(fig, update, frames=N_FRAMES, blit=False)
out = os.path.normpath(os.path.join(os.path.dirname(__file__),
      "../../../public/img/vggt-omega/optimize-vs-predict.mp4"))
anim.save(out, writer=FFMpegWriter(fps=FPS, codec="libx264",
          extra_args=["-pix_fmt", "yuv420p", "-crf", "22"]),
          savefig_kwargs={"facecolor": BG})
print("wrote", out)
