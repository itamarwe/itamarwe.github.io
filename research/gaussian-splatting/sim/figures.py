#!/usr/bin/env python3
"""Static figures for the Gaussian Splatting post. Dark 3b1b-ish palette."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Polygon, FancyBboxPatch, Rectangle, Circle, Ellipse
from matplotlib.collections import LineCollection
import os

BG   = "#0e1116"
FG   = "#ededed"
MUT  = "#8b95a5"
CYAN = "#3fc1ff"
GOLD = "#ffd166"
GREEN= "#7CFC8A"
RED  = "#ff5a5a"
PURP = "#b48cff"

# Output dir is the post's public image folder, resolved relative to this script
# (research/gaussian-splatting/sim/ -> repo root -> public/img/gaussian-splatting).
OUT = os.path.normpath(os.path.join(os.path.dirname(__file__),
      "../../../public/img/gaussian-splatting"))
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial"],
    "text.color": FG, "axes.edgecolor": MUT, "axes.labelcolor": FG,
    "xtick.color": MUT, "ytick.color": MUT, "figure.dpi": 130,
})

def newfig(w, h):
    fig = plt.figure(figsize=(w, h)); fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor(BG)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    return fig, ax

def arrow(ax, p0, p1, color=FG, lw=2.0, ms=14, alpha=1.0, ls="-"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms,
                 color=color, lw=lw, alpha=alpha, linestyle=ls,
                 shrinkA=0, shrinkB=0, joinstyle="miter"))

def gauss_field(ax, cx, cy, cov, color, extent, peak=1.0, n=240):
    """Render an anisotropic 2D Gaussian as a soft glow via imshow alpha."""
    x = np.linspace(extent[0], extent[1], n); y = np.linspace(extent[2], extent[3], n)
    X, Y = np.meshgrid(x, y)
    inv = np.linalg.inv(cov)
    dx = X - cx; dy = Y - cy
    q = inv[0,0]*dx*dx + 2*inv[0,1]*dx*dy + inv[1,1]*dy*dy
    g = np.exp(-0.5*q) * peak
    rgb = matplotlib.colors.to_rgb(color)
    img = np.zeros((n, n, 4))
    img[..., 0] = rgb[0]; img[..., 1] = rgb[1]; img[..., 2] = rgb[2]
    img[..., 3] = np.clip(g, 0, 1)
    ax.imshow(img, extent=extent, origin="lower", zorder=2, interpolation="bilinear")

def cov_from(scale, angle):
    th = np.radians(angle)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    S = np.diag(np.array(scale)**2)
    return R @ S @ R.T

def camera_icon(ax, x, y, ang, color, scale=1.0):
    """A small camera glyph: square body + lens frustum, pointing along ang (deg)."""
    th = np.radians(ang)
    d = np.array([np.cos(th), np.sin(th)])      # toward target
    n = np.array([-d[1], d[0]])
    c = np.array([x, y])
    b = 0.22*scale                               # body half-size
    body = [c + d*(-b) + n*b, c + d*(-b) - n*b, c + d*b - n*b, c + d*b + n*b]
    ax.add_patch(Polygon(body, closed=True, facecolor="#161b22", edgecolor=color,
                 lw=1.6, zorder=5))
    # lens frustum opening toward target
    f = 0.34*scale; w = 0.28*scale
    lens = [c + d*b + n*(b*0.6), c + d*b - n*(b*0.6),
            c + d*(b+f) - n*w, c + d*(b+f) + n*w]
    ax.add_patch(Polygon(lens, closed=True, facecolor="none", edgecolor=color,
                 lw=1.6, zorder=5, joinstyle="round"))

# ---------------------------------------------------------------------------
# Figure 1: the problem — novel view synthesis
# ---------------------------------------------------------------------------
def fig_problem():
    fig, ax = newfig(9, 5.4)
    ax.set_xlim(-4.5, 4.5); ax.set_ylim(-3.0, 2.7)
    cxs, cys = 0.0, -0.55                          # scene centre (lower half)
    # the scene/object — a little cluster of soft blobs (a "teapot")
    blobs = [(cxs-0.3, cys+0.0, [0.5,0.4], 20, GOLD),
             (cxs+0.35, cys+0.12, [0.4,0.28], -15, "#ff9d5c"),
             (cxs+0.05, cys-0.32, [0.46,0.26], 5, "#ffd166"),
             (cxs-0.05, cys+0.35, [0.28,0.28], 0, "#ffe49c")]
    for bx, by, sc, an, col in blobs:
        gauss_field(ax, bx, by, cov_from(sc, an), col, [-4.5,4.5,-3.0,2.7], peak=0.9)
    ax.text(cxs, cys-1.1, "the scene", color=MUT, ha="center", fontsize=12, style="italic")

    # cameras on an ellipse around the scene; leave the top-left clear for the title
    Rx, Ry = 3.3, 1.85
    known_ang = [-170, -128, -86, -44, -2, 28]
    for a in known_ang:
        ar = np.radians(a)
        camera_icon(ax, cxs+Rx*np.cos(ar), cys+Ry*np.sin(ar), a+180, CYAN, scale=1.0)
    # the novel camera (gold) with a ?
    a = 60; ar = np.radians(a)
    nx, ny = cxs+Rx*np.cos(ar), cys+Ry*np.sin(ar)
    camera_icon(ax, nx, ny, a+180, GOLD, scale=1.15)
    ax.text(nx+0.5, ny+0.1, "?", color=GOLD, ha="center", va="center",
            fontsize=26, fontweight="bold")

    ax.text(-4.3, 2.5, "Novel-view synthesis", color=FG, fontsize=19, fontweight="bold", va="top")
    ax.text(-4.3, 1.95, "Given a handful of photos from known camera poses,",
            color=MUT, fontsize=12.5, va="top")
    ax.text(-4.3, 1.58, "render the scene from a viewpoint never captured.",
            color=MUT, fontsize=12.5, va="top")
    # legend chips
    ax.text(4.3, -2.55, "■ captured views", color=CYAN, ha="right", fontsize=11.5)
    ax.text(4.3, -2.88, "■ the view we want", color=GOLD, ha="right", fontsize=11.5)
    fig.savefig(f"{OUT}/problem.png", facecolor=BG); plt.close(fig)
    print("problem.png")

# ---------------------------------------------------------------------------
# Figure 2: how NeRF does it — ray marching through a neural field
# ---------------------------------------------------------------------------
def fig_nerf():
    fig, ax = newfig(10.0, 5.0)
    ax.set_xlim(0, 10.0); ax.set_ylim(0, 5.0)

    # camera eye + image plane
    eye = np.array([0.55, 2.5])
    ax.add_patch(Circle(eye, 0.12, color=CYAN, zorder=6))
    ax.text(eye[0], eye[1]-0.45, "camera", color=CYAN, ha="center", fontsize=11)
    # image plane (pixel column)
    px = 1.35
    for k in range(7):
        yy = 1.55 + k*0.27
        ax.add_patch(Rectangle((px, yy), 0.24, 0.24, fill=False, edgecolor=MUT, lw=1))
    ax.add_patch(Rectangle((px, 1.55+3*0.27), 0.24, 0.24, facecolor=GOLD, edgecolor=GOLD, lw=1, zorder=4))
    ax.text(px+0.12, 1.3, "image", color=MUT, ha="center", fontsize=10)

    # the ray through the highlighted pixel into the volume
    pix = np.array([px+0.12, 1.55+3*0.27+0.12])
    end = np.array([6.4, 3.7])
    ax.plot([eye[0], end[0]], [eye[1], end[1]], color=GOLD, lw=1.8, zorder=3)
    # volume box (the scene)
    ax.add_patch(FancyBboxPatch((3.0, 1.2), 3.5, 3.1, boxstyle="round,pad=0.02,rounding_size=0.1",
                 fill=True, facecolor="#161b22", edgecolor=MUT, lw=1.2, zorder=1))
    ax.text(4.75, 1.05, "scene volume", color=MUT, ha="center", fontsize=10)
    # sample points along the ray
    ts = np.linspace(0.42, 0.86, 9)
    samples = [eye + t*(end-eye) for t in ts]
    for i, s in enumerate(samples):
        inside = 3.0 < s[0] < 6.5 and 1.2 < s[1] < 4.3
        c = CYAN if inside else MUT
        ax.add_patch(Circle(s, 0.07, color=c, zorder=5))
    ax.text(4.9, 3.95, "sample points along the ray", color=CYAN, fontsize=10.5, ha="center")

    # one sample → MLP → (color, density)
    s0 = samples[5]
    mlp_xy = (7.05, 2.55)
    arrow(ax, (s0[0]+0.1, s0[1]-0.05), (mlp_xy[0]-0.02, mlp_xy[1]+0.35), color=PURP, lw=1.6, ms=11)
    ax.text(s0[0]+0.05, s0[1]+0.28, "(x,y,z, θ,φ)", color=PURP, fontsize=9.5, ha="center")
    # MLP as stacked nodes
    layers = [3, 4, 4, 2]
    lx = np.linspace(mlp_xy[0], mlp_xy[0]+1.1, len(layers))
    nodes = []
    for li, (xx, nn) in enumerate(zip(lx, layers)):
        ys = np.linspace(mlp_xy[1]-0.45, mlp_xy[1]+0.45, nn)
        col = []
        for yy in ys:
            ax.add_patch(Circle((xx, yy), 0.055, color=PURP, zorder=6))
            col.append((xx, yy))
        nodes.append(col)
    for a_, b_ in zip(nodes[:-1], nodes[1:]):
        for p in a_:
            for q in b_:
                ax.plot([p[0], q[0]], [p[1], q[1]], color=PURP, lw=0.4, alpha=0.4, zorder=5)
    ax.text(mlp_xy[0]+0.55, mlp_xy[1]+0.72, "MLP", color=PURP, ha="center", fontsize=12, fontweight="bold")
    # outputs
    ox = mlp_xy[0]+1.45
    arrow(ax, (lx[-1]+0.08, mlp_xy[1]), (ox-0.05, mlp_xy[1]), color=PURP, lw=1.6, ms=11)
    ax.text(ox+0.05, mlp_xy[1]+0.22, "color (RGB)", color=GREEN, fontsize=10, va="center")
    ax.text(ox+0.05, mlp_xy[1]-0.22, "density σ", color=GOLD, fontsize=10, va="center")

    ax.text(0.4, 4.75, "NeRF: the scene is a neural function", color=FG, fontsize=18, fontweight="bold", va="top")
    ax.text(0.4, 4.32, "March a ray, query the network at every sample, integrate.",
            color=MUT, fontsize=12.5, va="top")
    ax.text(4.75, 0.45, "hundreds of network queries per pixel  →  slow",
            color=RED, ha="center", fontsize=11.5, fontweight="bold")
    fig.savefig(f"{OUT}/nerf.png", facecolor=BG); plt.close(fig)
    print("nerf.png")

# ---------------------------------------------------------------------------
# Figure 3: implicit (NeRF) vs explicit (Gaussian splatting)
# ---------------------------------------------------------------------------
def fig_implicit_vs_explicit():
    fig, ax = newfig(9.2, 4.6)
    ax.set_xlim(0, 9.2); ax.set_ylim(0, 4.6)
    ax.plot([4.6, 4.6], [0.35, 4.0], color=MUT, lw=0.8, alpha=0.5)

    # LEFT: NeRF — a neural net
    ax.text(2.3, 4.25, "NeRF — implicit", color=CYAN, fontsize=15, fontweight="bold", ha="center")
    cx, cy = 2.3, 2.3
    layers = [3, 5, 5, 5, 2]
    lx = np.linspace(1.0, 3.6, len(layers))
    nodes = []
    for xx, nn in zip(lx, layers):
        ys = np.linspace(cy-1.1, cy+1.1, nn); col=[]
        for yy in ys:
            ax.add_patch(Circle((xx, yy), 0.07, color=PURP, zorder=6)); col.append((xx, yy))
        nodes.append(col)
    for a_, b_ in zip(nodes[:-1], nodes[1:]):
        for p in a_:
            for q in b_:
                ax.plot([p[0], q[0]], [p[1], q[1]], color=PURP, lw=0.35, alpha=0.35, zorder=5)
    ax.text(2.3, 0.75, "scene = network weights", color=MUT, ha="center", fontsize=11.5)
    ax.text(2.3, 0.42, "render = ray-march + many queries", color=MUT, ha="center", fontsize=10.5, style="italic")

    # RIGHT: Gaussian splatting — explicit blobs
    ax.text(6.9, 4.25, "Gaussian splatting — explicit", color=GOLD, fontsize=15, fontweight="bold", ha="center")
    rng = np.random.default_rng(7)
    ext = [4.9, 8.9, 1.0, 3.7]
    cols = [GOLD, "#ff9d5c", CYAN, GREEN, "#ffe49c", "#ff7ab8", PURP]
    for _ in range(46):
        bx = rng.uniform(5.6, 8.2); by = rng.uniform(1.7, 3.35)
        # cluster toward a blobby shape
        sc = [rng.uniform(0.10, 0.32), rng.uniform(0.06, 0.18)]
        an = rng.uniform(0, 180); col = cols[rng.integers(len(cols))]
        gauss_field(ax, bx, by, cov_from(sc, an), col, ext, peak=0.8)
    ax.text(6.9, 0.75, "scene = millions of 3D Gaussians", color=MUT, ha="center", fontsize=11.5)
    ax.text(6.9, 0.42, "render = rasterize / splat (real-time)", color=MUT, ha="center", fontsize=10.5, style="italic")
    fig.savefig(f"{OUT}/implicit_vs_explicit.png", facecolor=BG); plt.close(fig)
    print("implicit_vs_explicit.png")

# ---------------------------------------------------------------------------
# Figure 4: anatomy of a single 3D Gaussian
# ---------------------------------------------------------------------------
def fig_anatomy():
    fig, ax = newfig(9.4, 5.0)
    ax.set_xlim(-4.7, 4.7); ax.set_ylim(-2.5, 2.5)
    cx, cy = -2.0, -0.1
    scale = [1.05, 0.42]; angle = 30
    cov = cov_from(scale, angle)
    gauss_field(ax, cx, cy, cov, GOLD, [-4.7,4.7,-2.5,2.5], peak=1.0, n=300)

    # principal axes (eigenvectors) as arrows
    th = np.radians(angle)
    e1 = np.array([np.cos(th), np.sin(th)]); e2 = np.array([-np.sin(th), np.cos(th)])
    c = np.array([cx, cy])
    arrow(ax, c, c+e1*scale[0]*1.7, color=FG, lw=2.2, ms=13)
    arrow(ax, c, c+e2*scale[1]*2.2, color=FG, lw=2.2, ms=13)
    ax.add_patch(Circle(c, 0.07, color=RED, zorder=8))

    ax.annotate("position  (x, y, z)", xy=(cx, cy), xytext=(cx-0.2, cy-1.65),
                color=RED, fontsize=12, ha="center",
                arrowprops=dict(arrowstyle="-", color=RED, lw=1.2))
    ax.text(cx+e1[0]*scale[0]*1.7+0.15, cy+e1[1]*scale[0]*1.7+0.18,
            "scale + rotation", color=FG, fontsize=12, va="center")
    ax.text(cx+e1[0]*scale[0]*1.7+0.15, cy+e1[1]*scale[0]*1.7-0.12,
            "= the 3D covariance Σ", color=MUT, fontsize=10.5, va="center")
    ax.text(cx-0.1, cy+1.55, "anisotropic: stretch & squash freely",
            color=MUT, fontsize=10, va="center", ha="center")

    # right column: opacity + colour, well separated
    # view-dependent colour arc (spherical harmonics)
    ax.text(2.6, 2.05, "color  (spherical harmonics)", color=FG, fontsize=12, ha="center")
    ax.text(2.6, 1.7, "changes with view direction", color=MUT, fontsize=10, ha="center")
    arc_c = np.array([2.6, 0.55]); rr = 0.85
    for a_ in np.linspace(-55, 55, 70):
        ra = np.radians(a_)
        x = arc_c[0] + rr*np.sin(ra); y = arc_c[1] + rr*np.cos(ra)
        t = (a_+55)/110
        col = matplotlib.colors.hsv_to_rgb([0.08+0.5*t, 0.65, 1.0])
        ax.add_patch(Circle((x, y), 0.055, color=col, zorder=6))
    ax.add_patch(Circle(arc_c, 0.06, color=MUT, zorder=6))

    # opacity bar
    ax.text(2.6, -1.25, "opacity  α", color=FG, fontsize=12, ha="center")
    grad = np.linspace(0, 1, 100).reshape(1, -1)
    ax.imshow(np.dstack([np.ones_like(grad), np.ones_like(grad)*0.82,
              np.ones_like(grad)*0.4, grad]), extent=[1.5, 3.7, -1.85, -1.6],
              origin="lower", aspect="auto", zorder=4)
    ax.text(1.5, -2.05, "transparent", color=MUT, fontsize=8.5)
    ax.text(3.7, -2.05, "solid", color=MUT, fontsize=8.5, ha="right")

    ax.text(-4.5, 2.35, "Anatomy of one Gaussian", color=FG, fontsize=18, fontweight="bold", va="top")
    fig.savefig(f"{OUT}/anatomy.png", facecolor=BG); plt.close(fig)
    print("anatomy.png")

# ---------------------------------------------------------------------------
# Figure 5: the training pipeline
# ---------------------------------------------------------------------------
def fig_pipeline():
    fig, ax = newfig(9.4, 4.4)
    ax.set_xlim(0, 9.4); ax.set_ylim(0, 4.4)
    stages = [
        ("Capture", "photos / video\nof the scene", CYAN),
        ("SfM (COLMAP)", "camera poses +\nsparse point cloud", CYAN),
        ("Initialize", "a Gaussian at\neach sparse point", GOLD),
        ("Render", "project + sort +\nalpha-blend splats", GOLD),
        ("Loss + backprop", "compare to photo,\nupdate every param", GREEN),
        ("Densify & prune", "split where blurry,\ndelete the useless", PURP),
    ]
    bw, bh = 1.35, 1.1; y = 2.5
    xs = np.linspace(0.85, 8.55, len(stages))
    for i, ((t, d, col), x) in enumerate(zip(stages, xs)):
        ax.add_patch(FancyBboxPatch((x-bw/2, y-bh/2), bw, bh,
                     boxstyle="round,pad=0.02,rounding_size=0.12",
                     facecolor="#161b22", edgecolor=col, lw=1.6, zorder=3))
        ax.text(x, y+0.28, t, color=col, ha="center", va="center", fontsize=10.5, fontweight="bold", zorder=4)
        ax.text(x, y-0.18, d, color=MUT, ha="center", va="center", fontsize=8.3, zorder=4)
        if i < len(stages)-1:
            arrow(ax, (x+bw/2+0.02, y), (xs[i+1]-bw/2-0.02, y), color=MUT, lw=1.5, ms=11)
    # loop-back arrow from densify -> render, routed well below the boxes
    ylo = y - bh/2 - 0.12
    ax.annotate("", xy=(xs[3], ylo), xytext=(xs[5], ylo),
                arrowprops=dict(arrowstyle="-|>", color=GOLD, lw=1.6,
                connectionstyle="arc3,rad=-0.55", shrinkA=2, shrinkB=2))
    ax.text((xs[3]+xs[5])/2, ylo-1.15, "repeat for ~30k steps", color=GOLD,
            ha="center", fontsize=10.5, style="italic")
    ax.text(0.4, 4.1, "The training loop", color=FG, fontsize=18, fontweight="bold", va="top")
    fig.savefig(f"{OUT}/pipeline.png", facecolor=BG); plt.close(fig)
    print("pipeline.png")

# ---------------------------------------------------------------------------
# social card 1200x630
# ---------------------------------------------------------------------------
def fig_social():
    fig = plt.figure(figsize=(12, 6.3), dpi=100); fig.patch.set_facecolor("#000000")
    ax = fig.add_axes([0,0,1,1]); ax.set_facecolor("#000000")
    ax.set_xticks([]); ax.set_yticks([]); ax.set_xlim(0,12); ax.set_ylim(0,6.3)
    for s in ax.spines.values(): s.set_visible(False)
    # blob cloud forming a soft shape on the right
    rng = np.random.default_rng(3)
    cols = [GOLD, "#ff9d5c", CYAN, GREEN, "#ffe49c", "#ff7ab8", PURP, "#ffd166"]
    # arrange blobs roughly along a swirl
    for i in range(120):
        t = i/120*4*np.pi
        rad = 0.15 + 1.7*i/120
        bx = 8.6 + rad*np.cos(t)*0.55 + rng.normal(0,0.12)
        by = 3.3 + rad*np.sin(t)*0.55 + rng.normal(0,0.12)
        sc = [rng.uniform(0.12,0.4), rng.uniform(0.06,0.18)]
        an = rng.uniform(0,180); col = cols[rng.integers(len(cols))]
        gauss_field(ax, bx, by, cov_from(sc, an), col, [0,12,0,6.3], peak=0.75, n=200)
    ax.text(0.7, 4.3, "Gaussian", color=FG, fontsize=58, fontweight="bold", va="center")
    ax.text(0.7, 3.25, "Splatting", color=GOLD, fontsize=58, fontweight="bold", va="center")
    ax.text(0.72, 2.15, "a million soft blobs that learn to look like a scene",
            color=MUT, fontsize=20, va="center")
    fig.savefig(f"{OUT}/social.png", facecolor="#000000"); plt.close(fig)
    print("social.png")

# ---------------------------------------------------------------------------
# Figure: tile-based rasterization on the GPU
# ---------------------------------------------------------------------------
def fig_tiling():
    fig, ax = newfig(9.8, 5.0)
    ax.set_xlim(0, 9.8); ax.set_ylim(0, 5.0)

    # --- left: the image split into tiles, with splats binned across them ----
    ox, oy, IW, IH = 0.5, 0.7, 4.2, 3.2
    nx, ny = 7, 5; cw, chh = IW/nx, IH/ny
    ax.add_patch(Rectangle((ox, oy), IW, IH, facecolor="#0b0e12", edgecolor=MUT, lw=1.4, zorder=1))
    for i in range(1, nx):
        ax.plot([ox+i*cw, ox+i*cw], [oy, oy+IH], color="#2a323c", lw=0.8, zorder=2)
    for j in range(1, ny):
        ax.plot([ox, ox+IW], [oy+j*chh, oy+j*chh], color="#2a323c", lw=0.8, zorder=2)
    # a few elliptical splats overlapping several tiles
    splats = [(ox+1.4, oy+2.2, 1.5, 0.7, 25, GOLD),
              (ox+2.9, oy+1.3, 1.1, 0.6, -20, CYAN),
              (ox+2.2, oy+2.0, 0.8, 0.5, 60, GREEN),
              (ox+3.3, oy+2.4, 0.9, 0.55, 10, PURP)]
    for sx, sy, w, h, an, col in splats:
        ax.add_patch(Ellipse((sx, sy), w, h, angle=an, facecolor=col, alpha=0.30,
                     edgecolor=col, lw=1.3, zorder=3))
    # highlight one tile
    hc, hr = 3, 2
    ax.add_patch(Rectangle((ox+hc*cw, oy+hr*chh), cw, chh, fill=False,
                 edgecolor=GOLD, lw=2.6, zorder=6))
    ax.text(ox+IW/2, oy-0.3, "image → 16×16-pixel tiles", color=MUT, ha="center", fontsize=11)
    ax.text(ox+IW/2, oy+IH+0.22, "splats binned into every tile they touch",
            color=MUT, ha="center", fontsize=10, style="italic")

    # --- arrow ---------------------------------------------------------------
    arrow(ax, (ox+(hc+1)*cw, oy+(hr+0.5)*chh), (6.05, 2.75), color=GOLD, lw=1.7, ms=12)
    ax.text(5.55, 3.15, "each tile →\none GPU thread block", color=GOLD, ha="center",
            fontsize=10, fontweight="bold")

    # --- right: depth-sorted stack composited front-to-back ------------------
    stx, sty, sbw = 6.7, 3.7, 2.3
    layers = [(GOLD,"front"),(PURP,""),(CYAN,""),(GREEN,""),("#ff7ab8","back")]
    bh2 = 0.42
    for i,(col,lab) in enumerate(layers):
        yy = sty - i*(bh2+0.1)
        ax.add_patch(FancyBboxPatch((stx, yy-bh2), sbw, bh2,
                     boxstyle="round,pad=0.01,rounding_size=0.06",
                     facecolor=col, alpha=0.55, edgecolor=col, lw=1.2, zorder=4))
        if lab: ax.text(stx+sbw+0.12, yy-bh2/2, lab, color=col, va="center", fontsize=9)
    arrow(ax, (stx-0.18, sty+0.05), (stx-0.18, sty-4*(bh2+0.1)-bh2), color=FG, lw=1.6, ms=11)
    ax.text(stx-0.34, sty-2*(bh2+0.1), "blend front→back\nuntil α saturates",
            color=FG, ha="right", va="center", fontsize=9.5)
    ax.text(stx+sbw/2, sty+0.42, "this tile's Gaussians, depth-sorted",
            color=MUT, ha="center", fontsize=10)

    ax.text(0.4, 4.85, "How the GPU renders: tile-based rasterization",
            color=FG, fontsize=17, fontweight="bold", va="top")
    ax.text(4.9, 0.28, "one global depth sort per frame · all tiles run in parallel · no per-pixel network",
            color=GREEN, ha="center", fontsize=10.5)
    fig.savefig(f"{OUT}/tiling.png", facecolor=BG); plt.close(fig)
    print("tiling.png")

# ---------------------------------------------------------------------------
# Figure: adaptive density control (clone / split / prune) during training
# ---------------------------------------------------------------------------
def fig_densification():
    fig, ax = newfig(9.8, 3.7)
    ax.set_xlim(0, 9.8); ax.set_ylim(0, 3.7)
    ext = [0, 9.8, 0, 3.7]
    centers = [1.63, 4.9, 8.16]
    for x in (3.27, 6.53):
        ax.plot([x, x], [0.35, 3.05], color=MUT, lw=0.6, alpha=0.4)
    by = 1.75
    titles = [("Clone", "under-reconstructed", GREEN),
              ("Split", "Gaussian too large", GOLD),
              ("Prune", "near-transparent", RED)]
    for c, (t, sub, col) in zip(centers, titles):
        ax.text(c, 3.35, t, color=col, ha="center", fontsize=14, fontweight="bold")
        ax.text(c, 3.02, sub, color=MUT, ha="center", fontsize=9.5, style="italic")

    def tarrow(c):  # before -> after transform arrow
        arrow(ax, (c-0.02, by), (c+0.32, by), color=MUT, lw=1.4, ms=10)

    # CLONE: one small blob -> two small blobs (spread along the gradient)
    c = centers[0]
    gauss_field(ax, c-0.78, by, cov_from([0.30, 0.28], 0), GOLD, ext, peak=0.9)
    arrow(ax, (c-0.78, by), (c-0.45, by+0.42), color=GREEN, lw=1.3, ms=8)  # ∇ hint
    ax.text(c-0.30, by+0.52, "∇", color=GREEN, fontsize=12, ha="center")
    tarrow(c)
    gauss_field(ax, c+0.6, by+0.13, cov_from([0.29, 0.27], 0), GOLD, ext, peak=0.9)
    gauss_field(ax, c+0.98, by-0.13, cov_from([0.29, 0.27], 0), GOLD, ext, peak=0.9)

    # SPLIT: one large blob -> two smaller blobs
    c = centers[1]
    gauss_field(ax, c-0.72, by, cov_from([0.58, 0.5], 0), CYAN, ext, peak=0.9)
    tarrow(c)
    gauss_field(ax, c+0.62, by+0.18, cov_from([0.31, 0.27], 0), CYAN, ext, peak=0.9)
    gauss_field(ax, c+1.0, by-0.18, cov_from([0.31, 0.27], 0), CYAN, ext, peak=0.9)

    # PRUNE: a faint blob -> gone (red X)
    c = centers[2]
    gauss_field(ax, c-0.72, by, cov_from([0.33, 0.31], 0), PURP, ext, peak=0.30)
    tarrow(c)
    xx, yy, s = c+0.85, by, 0.2
    ax.plot([xx-s, xx+s], [yy-s, yy+s], color=RED, lw=2.6)
    ax.plot([xx-s, xx+s], [yy+s, yy-s], color=RED, lw=2.6)

    ax.text(4.9, 0.32, "every few hundred steps · driven by each Gaussian's view-space position gradient",
            color=MUT, ha="center", fontsize=10)
    fig.savefig(f"{OUT}/densification.png", facecolor=BG); plt.close(fig)
    print("densification.png")

# ---------------------------------------------------------------------------
# Figure: the CUDA rasterizer — kernels, data buffers, parallelism, operators
# ---------------------------------------------------------------------------
def fig_cuda():
    fig, ax = newfig(10, 6.7)
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.7)

    def box(cx, cy, w, h, title, sub, edge):
        ax.add_patch(FancyBboxPatch((cx-w/2, cy-h/2), w, h,
                     boxstyle="round,pad=0.02,rounding_size=0.07",
                     facecolor="#161b22", edgecolor=edge, lw=1.5, zorder=3))
        ax.text(cx, cy + (0.12 if sub else 0), title, color="#e8edf3", ha="center",
                va="center", fontsize=9, fontweight="bold", zorder=4, family="monospace")
        if sub:
            ax.text(cx, cy-0.15, sub, color=MUT, ha="center", va="center", fontsize=7.4, zorder=4)

    def chip(cx, cy, text, col):
        ax.text(cx, cy, text, color=col, ha="center", va="center", fontsize=7.6,
                fontweight="bold", zorder=5,
                bbox=dict(boxstyle="round,pad=0.22", fc="#0b0e12", ec=col, lw=1.0))

    ax.text(0.3, 6.62, "Inside the rasterizer — kernels, data, parallelism",
            color=FG, fontsize=13.5, fontweight="bold", va="top")

    # ---- forward lane (left column) ----
    fx, w, h = 2.55, 3.1, 0.56
    ys = [5.35, 4.52, 3.69, 2.86, 2.03, 1.20]
    fwd = [
        ("preprocessCUDA", "project · 2D cov Σ′ · conic · SH→RGB", GOLD, "1 thread / Gaussian", GOLD),
        ("InclusiveSum", "prefix-sum tiles_touched → offsets", GREEN, "CUB scan", GREEN),
        ("duplicateWithKeys", "key = (tileID«32 | depth) per tile hit", GOLD, "1 thread / Gaussian", GOLD),
        ("SortPairs", "sort (key, gaussianID): tile, then depth", GREEN, "CUB radix sort", GREEN),
        ("identifyTileRanges", "find each tile's slice of the list", CYAN, "1 thread / entry", CYAN),
        ("renderCUDA", "batch→shared mem · blend front→back", CYAN, "1 block / tile · 256 thr", CYAN),
    ]
    for (t, s, ec, ctxt, ccol), cy in zip(fwd, ys):
        box(fx, cy, w, h, t, s, ec)
        chip(fx + w/2 + 1.15, cy, ctxt, ccol)
    for a_, b_ in zip(ys[:-1], ys[1:]):
        arrow(ax, (fx, a_-h/2), (fx, b_+h/2), color=CYAN, lw=1.3, ms=9)

    # top buffers + bottom image
    ax.text(fx, 6.02, "VRAM:  per-Gaussian arrays  [ μ · scale · quat · α · SH ]",
            color="#cdd6e0", ha="center", fontsize=8.4, zorder=4,
            bbox=dict(boxstyle="round,pad=0.3", fc="#0b0e12", ec=PURP, lw=1.2))
    arrow(ax, (fx, 5.83), (fx, ys[0]+h/2), color=CYAN, lw=1.3, ms=9)
    box(fx, 0.45, 1.8, 0.42, "rendered image", "", "#e8edf3")
    arrow(ax, (fx, ys[-1]-h/2), (fx, 0.66), color=CYAN, lw=1.3, ms=9)

    # ---- backward lane (right column) ----
    bx = 8.15
    box(bx, 1.20, 3.0, 0.78, "renderCUDA (bwd)", "back-to-front · recompute α", RED)
    chip(bx, 0.45, "atomicAdd  → per-Gaussian grad buffers", RED)
    box(bx, 3.69, 3.0, 0.78, "preprocessCUDA (bwd)", "chain ∂L to  μ₃ · scale · quat · SH", RED)
    box(bx, 5.45, 2.4, 0.6, "Adam step (PyTorch)", "update every parameter", GOLD)
    arrow(ax, (bx, 1.59), (bx, 3.30), color=RED, lw=1.4, ms=10)
    arrow(ax, (bx, 4.08), (bx, 5.15), color=RED, lw=1.4, ms=10)
    # image → backward
    ax.annotate("", xy=(bx-1.5, 1.05), xytext=(fx+0.95, 0.45),
                arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.4,
                connectionstyle="arc3,rad=-0.18"))
    ax.text(5.55, 0.62, "∂L/∂image", color=RED, ha="center", fontsize=8)
    # Adam → buffers (loop), bowing down through the empty middle, clear of the title
    ax.annotate("", xy=(fx+1.55, 6.05), xytext=(bx-1.25, 5.62),
                arrowprops=dict(arrowstyle="-|>", color=GOLD, lw=1.4,
                connectionstyle="arc3,rad=-0.16"))
    ax.text(6.45, 5.92, "updated params → next step", color=GOLD, ha="center", fontsize=8)

    # legend (bottom)
    ax.text(5.05, 0.12, "cyan = forward kernel", color=CYAN, ha="right", fontsize=7.8)
    ax.text(5.2, 0.12, "·", color=MUT, ha="center", fontsize=7.8)
    ax.text(5.35, 0.12, "red = backward kernel", color=RED, ha="left", fontsize=7.8)
    ax.text(8.2, 0.12, "green = CUB library op", color=GREEN, ha="center", fontsize=7.8)

    fig.savefig(f"{OUT}/cuda_pipeline.png", facecolor=BG); plt.close(fig)
    print("cuda_pipeline.png")

if __name__ == "__main__":
    fig_problem(); fig_nerf(); fig_implicit_vs_explicit()
    fig_anatomy(); fig_pipeline(); fig_tiling(); fig_densification()
    fig_cuda(); fig_social()
    print("all figures done")
