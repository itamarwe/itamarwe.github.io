#!/usr/bin/env python3
"""Split-screen animation: bundle adjustment grinding vs one forward pass.

STYLIZED RE-ENACTMENT (stated in the post): the left panel imitates the look of
an iterative optimizer converging — the real house model's surfaces start
scattered and jitter into place; it is not real solver output. Right panel:
input views appear, one sweep, and the same model snaps in whole.
The 3D house is `building_home_B` from the KayKit Medieval Hexagon Pack (CC0).
Output: public/img/vggt-omega/optimize-vs-predict.mp4 (1600x900, h264, loopable).
"""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PolyCollection
from matplotlib.animation import FuncAnimation, FFMpegWriter

sys.path.append(os.path.dirname(__file__))
from figures import BG, FG, MUT, CYAN, GOLD, RED, house_mesh_2d, house_view

FPS, SECS = 30, 9.0
N_FRAMES = int(FPS * SECS)

# The panel axes have unequal data units (x: 44 units over ~6", y: 26 over
# ~6.2"), so scale y by ~0.57 to keep the house's true proportions on screen.
AR_Y = 0.57
TRI, TDEPTH, TSHADE = house_mesh_2d(az=34, el=16)      # far-to-near sorted
T0 = TRI * np.array([24.0, 24.0 * AR_Y]) + np.array([-2.0, -3.5])
NT = len(T0)

def shaded_colors(hexcolor):
    base = np.array(mcolors.to_rgb(hexcolor))
    bright = (0.22 + 0.78*TSHADE) * (1.0 - 0.18*TDEPTH)
    return np.clip(base[None, :] * bright[:, None] * 1.30, 0, 1)

CAMS = [(-6, 12, -35), (24, 13, 218), (-5.5, -3, 25), (22, -2.5, 155)]

rng = np.random.default_rng(42)

def smooth_noise(n_items, n_keys=10, dim=2):
    keys = rng.normal(0, 1, (n_keys, n_items, dim))
    def at(t):  # t in [0,1]
        x = t * (n_keys - 1)
        i = int(np.clip(np.floor(x), 0, n_keys - 2)); f = x - i
        f = f*f*(3-2*f)
        return keys[i]*(1-f) + keys[i+1]*f
    return at

tri_noise = smooth_noise(NT)
cam_noise = smooth_noise(len(CAMS), dim=3)

def decay(t):
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

# ---- left panel: the house's surfaces, scattered and converging
meshL = PolyCollection(T0, facecolors=shaded_colors(GOLD), edgecolors="none",
                       zorder=4)
axL.add_collection(meshL)
camL = []
for _ in CAMS:
    l1, = axL.plot([], [], color=GOLD, lw=1.4, alpha=0.85, zorder=5)
    l2, = axL.plot([], [], color=GOLD, lw=1.4, alpha=0.85, zorder=5)
    camL.append((l1, l2))
iterTxt = axL.text(0.03, 0.04, "", transform=axL.transAxes, color=GOLD, fontsize=13)

# ---- right panel: inputs, one sweep, the model snaps in whole
meshR = PolyCollection(T0, facecolors=shaded_colors(CYAN), edgecolors="none",
                       zorder=4, alpha=0.0)
axR.add_collection(meshR)
camR = []
for _ in CAMS:
    l1, = axR.plot([], [], color=CYAN, lw=1.4, alpha=0.0, zorder=5)
    l2, = axR.plot([], [], color=CYAN, lw=1.4, alpha=0.0, zorder=5)
    camR.append((l1, l2))
thumbs, thumb_pts = [], []
for i in range(3):
    r = Polygon([(0, 0)], closed=True, facecolor="#10141b", edgecolor=MUT,
                lw=1.2, alpha=0.0, zorder=6)
    axR.add_patch(r); thumbs.append(r)
    # each thumbnail is the house genuinely rendered from a different viewpoint
    x0, y0, w, h = -13.2, 15.5 - i*5.6, 6.5, 4.4
    vt, vd, vs = house_mesh_2d(az=-15 + 48*i, el=12 + 5*i)
    base = np.array(mcolors.to_rgb("#b9c4d4"))
    bright = (0.22 + 0.78*vs) * (1.0 - 0.18*vd)
    cols = np.clip(base[None, :] * bright[:, None] * 1.15, 0, 1)
    V = vt.copy()
    V[..., 0] = x0 + 0.9 + V[..., 0] * (w - 1.8)
    V[..., 1] = y0 + 0.3 + V[..., 1] * (w - 1.8) * AR_Y * 0.82
    pc = PolyCollection(V, facecolors=cols, edgecolors="none", zorder=7, alpha=0.0)
    axR.add_collection(pc)
    thumb_pts.append(pc)
sweep, = axR.plot([], [], color=CYAN, lw=2.5, alpha=0.0, zorder=7)
passTxt = axR.text(0.72, 0.06, "", transform=axR.transAxes, color=CYAN,
                   fontsize=15, weight="bold")

def frustum_lines(x, y, ang, ln=5.0, spread=16):
    a1, a2 = np.radians(ang-spread), np.radians(ang+spread)
    return ([x, x+ln*np.cos(a1)], [y, y+ln*np.sin(a1)],
            [x, x+ln*np.cos(a2)], [y, y+ln*np.sin(a2)])

def update(k):
    t = k / N_FRAMES
    # ---------- LEFT: surfaces drifting home under an optimizer
    d = decay(t)
    off = tri_noise(t) * 5.5 * d + 0.10 * d * rng.normal(0, 1, (NT, 2))
    meshL.set_verts(T0 + off[:, None, :])
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
    meshR.set_alpha(float(snap))
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
