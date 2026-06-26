"""
Metric-calibrated path profile visualizations from the VGGT camera path.

Generates four figures:
  path_horizontal.png  – top-down (plan view): lateral vs forward
  path_vertical.png    – side profile: forward vs height
  path_3d.png          – 3-D path with colour-coded time
  path_height_time.png – height above estimated ground vs time

Metric calibration: VGGT outputs are in arbitrary scene units.  We calibrate
by assuming the drone's average ground speed is ASSUMED_KMH.  Typical
Hezbollah FPV attack speed is 50–80 km/h; 60 km/h is used as the central
estimate.  The one obvious artifact step (frame 27→28, 15× the median) is
excluded from the length sum before scaling.  The resulting distances should
be treated as approximate (±30%).

Usage:  python path_profiles.py
"""
import os, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D          # noqa: F401

HERE   = os.path.dirname(os.path.abspath(__file__))
VGGT   = os.path.join(HERE, "..", "vggt")
OUT    = os.path.abspath(os.path.join(HERE, "..", "..", "..", "public", "img",
                                       "fpv-drone-strikes"))
os.makedirs(OUT, exist_ok=True)

CYAN, GOLD, GREEN, RED, MUTED = "#3fc1ff", "#ffd166", "#7CFC8A", "#ff5a5a", "#8b95a5"
BG = "#000000"; FG = "#ededed"

# ── load path ──────────────────────────────────────────────────────────────
raw = np.load(os.path.join(VGGT, "camera_path.npy")).astype(float)
N   = len(raw)            # 129 frames
FPS = 6                   # frames sampled at 6 fps
TOTAL_TIME = N / FPS      # ≈ 21.5 s  (two video segments: 10 + 11.5 s)

# ── metric calibration ─────────────────────────────────────────────────────
ASSUMED_KMH = 60.0        # assumed average attack speed (km/h)
speed_mps   = ASSUMED_KMH / 3.6

segs = np.linalg.norm(np.diff(raw, axis=0), axis=1)
outlier_mask = segs > np.median(segs) * 5     # flag artifact jumps
good_path_len = segs[~outlier_mask].sum()
good_time     = np.count_nonzero(~outlier_mask) / FPS

# scale so good_path_len * scale == expected_distance for the good frames
SCALE = (speed_mps * good_time) / good_path_len   # metres per scene unit
print(f"N frames      : {N}")
print(f"total time    : {TOTAL_TIME:.1f} s")
print(f"outlier steps : {outlier_mask.sum()} (excluded from scale fit)")
print(f"SCALE         : {SCALE:.1f} m / scene-unit  (at {ASSUMED_KMH} km/h)")

# convert to metres, origin at first camera
pm = (raw - raw[0]) * SCALE        # (N,3)  world metres
# world +y is up (confirmed by render_path.py); z is the main approach axis
forward  = -(pm[:, 2])             # forward distance (positive ahead); scene −z = fwd
lateral  =   pm[:, 0]              # lateral (positive = right)
height_y =   pm[:, 1]              # vertical metres relative to starting height

# ground reference: lowest recovered altitude ≈ near-impact height
ground_offset = height_y.min()     # typically slightly negative
height = height_y - ground_offset  # height above estimated ground

t = np.arange(N) / FPS             # time axis (seconds)

# ── time colouring helper ───────────────────────────────────────────────────
def time_rgba(n_pts, alpha=1.0):
    """Return (n_pts,4) RGBA array going cyan → gold."""
    f = np.linspace(0, 1, n_pts)
    r = 0.25 + 0.75 * f
    g = 0.76  * np.ones(n_pts)
    b = 1.0  - 0.60 * f
    a = np.full(n_pts, alpha)
    return np.column_stack([r, g, b, a])

def coloured_line_2d(ax, x, y, lw=2.0):
    from matplotlib.collections import LineCollection
    pts  = np.column_stack([x, y]).reshape(-1, 1, 2)
    segs_arr = np.concatenate([pts[:-1], pts[1:]], axis=1)
    cols = time_rgba(len(segs_arr))
    lc   = LineCollection(segs_arr, colors=cols, linewidths=lw,
                          capstyle="round", joinstyle="round")
    ax.add_collection(lc)
    return lc

def style_ax(ax, xlabel, ylabel, title):
    ax.set_facecolor(BG)
    ax.tick_params(colors=FG, which="both")
    for spine in ax.spines.values():
        spine.set_edgecolor(MUTED)
    ax.set_xlabel(xlabel, color=FG, fontsize=11)
    ax.set_ylabel(ylabel, color=FG, fontsize=11)
    ax.set_title(title, color=FG, fontsize=12, pad=8)
    ax.grid(True, color="#1a1a2e", linewidth=0.6, alpha=0.9)

def add_legend_markers(ax, forward, lateral, height):
    ax.scatter(forward[0], lateral[0] if lateral is not None else height[0],
               color=GREEN, s=50, zorder=6, label="launch", edgecolors="w", lw=0.5)
    ax.scatter(forward[-1], lateral[-1] if lateral is not None else height[-1],
               color=RED, s=50, zorder=6, marker="x", lw=1.5, label="terminal")

def colorbar_strip(fig, ax):
    """Add a thin cyan→gold colour bar showing time direction."""
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "cg", [(0.25, 0.76, 1.0), (1.0, 0.82, 0.35)])
    sm = plt.cm.ScalarMappable(cmap=cmap,
                                norm=plt.Normalize(vmin=0, vmax=TOTAL_TIME))
    sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, orientation="vertical",
                      fraction=0.02, pad=0.02, aspect=25)
    cb.set_label("time (s)", color=FG, fontsize=9)
    cb.ax.yaxis.set_tick_params(color=FG)
    plt.setp(cb.ax.yaxis.get_ticklabels(), color=FG, fontsize=8)
    cb.outline.set_edgecolor(MUTED)

# ─────────────────────────────────────────────────────────────────────────────
# 1. Horizontal profile (top-down: forward × lateral)
# ─────────────────────────────────────────────────────────────────────────────
fig1, ax1 = plt.subplots(figsize=(9, 5), facecolor=BG)
coloured_line_2d(ax1, forward, lateral, lw=2.2)
add_legend_markers(ax1, forward, lateral, None)
ax1.autoscale()
style_ax(ax1, "forward distance (m)", "lateral displacement (m)",
         "Horizontal profile — top-down view")
ax1.set_aspect("equal", adjustable="datalim")
ax1.legend(facecolor="#111", edgecolor=MUTED, labelcolor=FG, fontsize=9,
           loc="upper left")
colorbar_strip(fig1, ax1)
fig1.text(0.5, 0.01, f"Metric scale estimated at {ASSUMED_KMH:.0f} km/h average speed (±30%)",
          color=MUTED, ha="center", fontsize=8)
fig1.savefig(os.path.join(OUT, "path_horizontal.png"), dpi=150,
             facecolor=BG, bbox_inches="tight")
print("saved path_horizontal.png")
plt.close(fig1)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Vertical profile (side view: forward × height)
# ─────────────────────────────────────────────────────────────────────────────
fig2, ax2 = plt.subplots(figsize=(9, 5), facecolor=BG)
coloured_line_2d(ax2, forward, height, lw=2.2)
add_legend_markers(ax2, forward, None, height)
ax2.autoscale()
ax2.axhline(0, color=MUTED, lw=0.8, ls="--", label="est. ground level")
style_ax(ax2, "forward distance (m)", "height above ground (m, est.)",
         "Vertical profile — side view")
ax2.legend(facecolor="#111", edgecolor=MUTED, labelcolor=FG, fontsize=9,
           loc="upper right")
colorbar_strip(fig2, ax2)
fig2.text(0.5, 0.01, f"Metric scale estimated at {ASSUMED_KMH:.0f} km/h average speed (±30%)",
          color=MUTED, ha="center", fontsize=8)
fig2.savefig(os.path.join(OUT, "path_vertical.png"), dpi=150,
             facecolor=BG, bbox_inches="tight")
print("saved path_vertical.png")
plt.close(fig2)

# ─────────────────────────────────────────────────────────────────────────────
# 3. 3-D path
# ─────────────────────────────────────────────────────────────────────────────
fig3 = plt.figure(figsize=(9, 7), facecolor=BG)
ax3  = fig3.add_subplot(111, projection="3d")
ax3.set_facecolor(BG)
ax3.set_axis_off()

# draw white underlay then coloured segments
ax3.plot(forward, lateral, height, color="white", lw=3.5, alpha=0.35,
         solid_capstyle="round")
for j in range(len(forward) - 1):
    f  = j / max(N - 1, 1)
    c  = (0.25 + 0.75 * f, 0.76, 1.0 - 0.60 * f)
    ax3.plot(forward[j:j+2], lateral[j:j+2], height[j:j+2],
             color=c, lw=2.4, solid_capstyle="round")

ax3.scatter([forward[0]],  [lateral[0]],  [height[0]],
            color=GREEN, s=70, edgecolors="w", lw=0.8, depthshade=False, zorder=9)
ax3.scatter([forward[-1]], [lateral[-1]], [height[-1]],
            color=RED, s=70, marker="x", lw=1.8, depthshade=False, zorder=9)

# add a faint ground plane at z=0
gx = np.array([forward.min(), forward.max()])
gy = np.array([lateral.min(), lateral.max()])
GX, GY = np.meshgrid(gx, gy)
GZ = np.zeros_like(GX)
ax3.plot_surface(GX, GY, GZ, color=MUTED, alpha=0.08)

ax3.view_init(elev=18, azim=-145)
ax3.set_xlabel("forward (m)", color=FG, fontsize=9, labelpad=4)
ax3.set_ylabel("lateral (m)", color=FG, fontsize=9, labelpad=4)
ax3.set_zlabel("height (m)", color=FG, fontsize=9, labelpad=4)
ax3.tick_params(colors=FG, labelsize=8)
ax3.set_title("3-D flight path (metric estimate)", color=FG, fontsize=12, pad=6)
fig3.text(0.5, 0.02, f"Metric scale estimated at {ASSUMED_KMH:.0f} km/h average speed (±30%)",
          color=MUTED, ha="center", fontsize=8)
fig3.savefig(os.path.join(OUT, "path_3d.png"), dpi=150,
             facecolor=BG, bbox_inches="tight")
print("saved path_3d.png")
plt.close(fig3)

# ─────────────────────────────────────────────────────────────────────────────
# 4. Height above ground vs time
# ─────────────────────────────────────────────────────────────────────────────
fig4, ax4 = plt.subplots(figsize=(9, 4.5), facecolor=BG)
coloured_line_2d(ax4, t, height, lw=2.5)
ax4.autoscale()
ax4.axhline(0, color=MUTED, lw=0.8, ls="--")

# mark launch and terminal
ax4.scatter([t[0]],  [height[0]],  color=GREEN, s=55, zorder=7, edgecolors="w", lw=0.5)
ax4.scatter([t[-1]], [height[-1]], color=RED,   s=55, zorder=7, marker="x", lw=1.8)

# annotate key moments
ax4.annotate("launch",   xy=(t[0],  height[0]),  color=GREEN, fontsize=9, xytext=(1, height[0]+0.5))
ax4.annotate("terminal", xy=(t[-1], height[-1]), color=RED,   fontsize=9,
             xytext=(t[-1]-3, height[-1]+0.8))

# segment boundary annotation
seg_bnd_t = 60 / FPS  # frame 60
ax4.axvline(seg_bnd_t, color=MUTED, lw=0.7, ls=":", alpha=0.7)
ax4.text(seg_bnd_t + 0.2, ax4.get_ylim()[1] if False else height.max() * 0.95,
         "clip gap", color=MUTED, fontsize=8, va="top")

style_ax(ax4, "time (s)", "height above ground (m, est.)",
         "Height above ground vs time")
colorbar_strip(fig4, ax4)
ax4.set_xlim(left=-0.5)
fig4.text(0.5, 0.01,
          f"Ground ≈ min recovered altitude; metric scale at {ASSUMED_KMH:.0f} km/h (±30%)",
          color=MUTED, ha="center", fontsize=8)
fig4.savefig(os.path.join(OUT, "path_height_time.png"), dpi=150,
             facecolor=BG, bbox_inches="tight")
print("saved path_height_time.png")
plt.close(fig4)

# summary stats
print(f"\n--- Path summary (at {ASSUMED_KMH} km/h / {SCALE:.0f} m per scene-unit) ---")
print(f"  total forward range : {forward.max():.1f} m")
print(f"  lateral swing       : {lateral.min():.1f}  to  {lateral.max():.1f} m")
print(f"  height range        : {height.min():.1f}  to  {height.max():.1f} m  (above est. ground)")
print(f"  flight duration     : {TOTAL_TIME:.1f} s  ({N} frames @ {FPS} fps)")
