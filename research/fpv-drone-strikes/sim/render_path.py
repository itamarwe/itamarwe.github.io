"""
Render the REAL VGGT output for the Sholef-howitzer FPV clip:

  - reconstruction_hero.png : the reconstructed scene point cloud + the drone's
    3-D flight path (one camera center per sampled frame).
  - path_extraction.mp4 : a synced side-by-side animation. Left = the actual FPV
    frame; right = the VGGT point cloud with the flight path drawing in and a
    marker at the camera pose VGGT recovered for that exact frame.

All geometry here is the model's own prediction (see ../vggt/). The only thing we
add is outlier rejection: VGGT mis-estimated 2 of the 38 poses on motion-blurred
frames; we flag those and interpolate the drawn flight line across them (the raw
rejected poses are still drawn, as red crosses).

Usage:  python render_path.py still   |   python render_path.py anim
"""
import os, sys, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.image import imread

HERE = os.path.dirname(os.path.abspath(__file__))
VGGT = os.path.join(HERE, "..", "vggt")
OUT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "public", "img", "fpv-drone-strikes"))
os.makedirs(OUT, exist_ok=True)

CYAN, GOLD, GREEN, RED, MUTED = "#3fc1ff", "#ffd166", "#7CFC8A", "#ff5a5a", "#8b95a5"
BG = "#000000"

def load():
    d = np.load(os.path.join(VGGT, "point_cloud.npz"))
    pts, cols = d["pts"].astype(float), d["cols"].astype(float) / 255.0
    path = np.load(os.path.join(VGGT, "camera_path.npy")).astype(float)
    return pts, cols, path

def to_view(P):
    """Map world (x,y,z) -> plot coords so that -y is up (camera above terrain)."""
    return np.stack([P[:, 0], P[:, 2], -P[:, 1]], axis=-1)

def find_outliers(path):
    """Flag interior poses that sit far from the midpoint of their neighbours."""
    steps = np.linalg.norm(np.diff(path, axis=0), axis=1)
    med = np.median(steps)
    bad = np.zeros(len(path), bool)
    for i in range(1, len(path) - 1):
        mid = 0.5 * (path[i - 1] + path[i + 1])
        if np.linalg.norm(path[i] - mid) > 4.0 * med:
            bad[i] = True
    return bad

def clean_path(path, bad):
    """Linear-interpolate the drawn line across rejected poses."""
    p = path.copy()
    idx = np.arange(len(p))
    good = ~bad
    for k in range(3):
        p[:, k] = np.interp(idx, idx[good], path[good, k])
    return p

def crop_scene(pts, cols, path):
    """Focus on the near-field scene the drone actually flies through, so the
    flight path is prominent instead of lost in the far depth fan."""
    pad = np.array([0.05, 0.02, 0.06])
    lo = path.min(0) - pad
    hi = path.max(0) + pad
    # let the scene extend further *ahead* (negative z) toward the target
    lo[2] = path[:, 2].min() - 0.05
    hi[2] = path[:, 2].max() + 0.03
    m = np.all((pts >= lo) & (pts <= hi), axis=1)
    return pts[m], cols[m]

def setup_3d(ax):
    ax.set_facecolor(BG)
    ax.set_axis_off()
    try:
        ax.set_box_aspect((1, 1, 0.45))
    except Exception:
        pass

def draw_scene(ax, vpts, cols, vpath, bad, upto=None, drone=None):
    setup_3d(ax)
    ax.scatter(vpts[:, 0], vpts[:, 1], vpts[:, 2], c=cols, s=0.5, alpha=0.4,
               linewidths=0, depthshade=False)
    n = len(vpath) if upto is None else upto
    if n >= 2:
        # path colored by time: cyan (early) -> gold (terminal)
        seg = vpath[:n]
        for j in range(len(seg) - 1):
            f = j / max(len(vpath) - 1, 1)
            col = (0.25 + 0.75 * f, 0.76, 1.0 - 0.6 * f)  # cyan->gold-ish
            ax.plot(seg[j:j + 2, 0], seg[j:j + 2, 1], seg[j:j + 2, 2],
                    color=col, lw=2.6, alpha=0.98, solid_capstyle="round")
        ax.scatter(seg[:, 0], seg[:, 1], seg[:, 2], color=CYAN, s=12,
                   edgecolors="white", linewidths=0.3, depthshade=False, zorder=8)
    # rejected raw poses revealed so far
    rb = bad.copy()
    if upto is not None:
        rb = rb & (np.arange(len(bad)) < n)
    if rb.any():
        ax.scatter(vpath[rb, 0], vpath[rb, 1], vpath[rb, 2], color=RED, s=26,
                   marker="x", linewidths=1.4, depthshade=False)
    # drone marker
    if drone is not None:
        ax.scatter([drone[0]], [drone[1]], [drone[2]], color=GOLD, s=70,
                   edgecolors="white", linewidths=0.8, depthshade=False, zorder=10)

def set_limits(ax, vpts, vpath):
    allp = np.vstack([vpts, vpath])
    for k, fn in enumerate([ax.set_xlim, ax.set_ylim, ax.set_zlim]):
        lo, hi = allp[:, k].min(), allp[:, k].max()
        pad = 0.05 * (hi - lo + 1e-6)
        fn(lo - pad, hi + pad)

def still():
    pts, cols, path = load()
    sp, sc = crop_scene(pts, cols, path)
    bad = find_outliers(path)
    cp = clean_path(path, bad)
    vpts, vpath, vcp = to_view(sp), to_view(path), to_view(cp)
    fig = plt.figure(figsize=(11, 7), facecolor=BG)
    ax = fig.add_subplot(111, projection="3d")
    draw_scene(ax, vpts, sc, vcp, bad)
    ax.scatter([vpath[0, 0]], [vpath[0, 1]], [vpath[0, 2]], color=GREEN, s=60,
               edgecolors="white", linewidths=0.8, depthshade=False, label="launch view")
    ax.scatter([vcp[-1, 0]], [vcp[-1, 1]], [vcp[-1, 2]], color=GOLD, s=80,
               edgecolors="white", linewidths=0.8, depthshade=False, label="terminal")
    set_limits(ax, vpts, vcp)
    ax.view_init(elev=14, azim=-155)
    ax.set_title("VGGT reconstruction: scene point cloud + recovered FPV flight path",
                 color="#ededed", fontsize=13, pad=0)
    fig.text(0.5, 0.04, "Real model output — facebook/vggt-omega, 38 frames of the "
             "2026-06-06 Sholef-howitzer strike", color=MUTED, ha="center", fontsize=9)
    fig.savefig(os.path.join(OUT, "reconstruction_hero.png"), dpi=150,
                facecolor=BG, bbox_inches="tight")
    print("saved reconstruction_hero.png")

def anim():
    import matplotlib.animation as animation
    pts, cols, path = load()
    sp, sc = crop_scene(pts, cols, path)
    bad = find_outliers(path)
    cp = clean_path(path, bad)
    vpts, vpath, vcp = to_view(sp), to_view(path), to_view(cp)

    frames_dir = os.path.join(VGGT, "frames")
    fpv = [imread(os.path.join(frames_dir, f"f_{i+1:03d}.jpg")) for i in range(len(path))]

    N = len(path)
    sub = 3                      # sub-frames per pose (for a slow orbit)
    total = N * sub
    fig = plt.figure(figsize=(12, 5.2), facecolor=BG)
    axL = fig.add_subplot(1, 2, 1); axL.set_facecolor(BG); axL.axis("off")
    axR = fig.add_subplot(1, 2, 2, projection="3d")
    imL = axL.imshow(fpv[0])
    axL.set_title("FPV feed (the enemy's view)", color="#ededed", fontsize=12)

    def render(t):
        i = min(t // sub, N - 1)
        imL.set_data(fpv[i])
        axR.cla()
        draw_scene(axR, vpts, sc, vcp, bad, upto=i + 1, drone=vcp[i])
        set_limits(axR, vpts, vcp)
        azim = -185 + 60 * (t / total)
        axR.view_init(elev=15, azim=azim)
        axR.set_title("VGGT 3-D reconstruction + flight path", color="#ededed", fontsize=12)
        axR.text2D(0.02, 0.02, f"frame {i+1}/{N}", transform=axR.transAxes,
                   color=MUTED, fontsize=9)
        return [imL]

    anim = animation.FuncAnimation(fig, render, frames=total, interval=120, blit=False)
    out = os.path.join(OUT, "path_extraction.mp4")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.02, wspace=0.02)
    anim.save(out, fps=12, dpi=120, savefig_kwargs={"facecolor": BG},
              extra_args=["-pix_fmt", "yuv420p"])
    print("saved path_extraction.mp4")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "still"
    (still if mode == "still" else anim)()
