#!/usr/bin/env python3
"""Static figures for the VGGT-Omega post. 3b1b-ish style on pure black (#000).

All figures are qualitative schematics EXCEPT fig_scaling, which plots the
point-error values published in the VGGT-Omega paper (Fig. 1); its x-positions
for the data-scaling curve are interpolated on the log axis between the
reported endpoints (2K -> 2M sequences), as noted in the post.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import (FancyArrowPatch, Polygon, FancyBboxPatch,
                                Rectangle, Circle, FancyArrow)
from matplotlib.collections import LineCollection
import matplotlib.colors as mcolors
import os

BG   = "#000000"
CARD = "#0b0e13"          # panels may sit a hair lighter than black
FG   = "#ededed"
MUT  = "#8b95a5"
CYAN = "#3fc1ff"
GOLD = "#ffd166"
GREEN= "#7CFC8A"
RED  = "#ff5a5a"
PURP = "#b48cff"

OUT = os.path.normpath(os.path.join(os.path.dirname(__file__),
      "../../../public/img/vggt-omega"))
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "text.color": FG, "axes.edgecolor": MUT, "axes.labelcolor": FG,
    "xtick.color": MUT, "ytick.color": MUT, "figure.dpi": 130,
    "figure.facecolor": BG, "savefig.facecolor": BG,
})

def newfig(w, h, xlim=(0, 100), ylim=(0, 100)):
    fig = plt.figure(figsize=(w, h)); fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor(BG)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    for s in ax.spines.values(): s.set_visible(False)
    return fig, ax

def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p, facecolor=BG, dpi=130)
    plt.close(fig)
    print("wrote", p)

def arrow(ax, p0, p1, color=FG, lw=2.0, ms=14, alpha=1.0, ls="-", rad=0.0, z=4):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms,
                 color=color, lw=lw, alpha=alpha, linestyle=ls, zorder=z,
                 shrinkA=0, shrinkB=0, connectionstyle=f"arc3,rad={rad}"))

def box(ax, x, y, w, h, ec=MUT, fc=CARD, lw=1.5, z=2, r=1.6):
    b = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                       facecolor=fc, edgecolor=ec, lw=lw, zorder=z)
    ax.add_patch(b); return b

def camera(ax, x, y, ang, color, s=1.0, z=5):
    """Camera glyph: body + frustum opening toward `ang` (deg)."""
    th = np.radians(ang); d = np.array([np.cos(th), np.sin(th)])
    n = np.array([-d[1], d[0]]); c = np.array([x, y]); b = 1.1 * s
    body = [c - d*b + n*b*0.8, c - d*b - n*b*0.8, c + d*b*0.4 - n*b*0.8, c + d*b*0.4 + n*b*0.8]
    ax.add_patch(Polygon(body, closed=True, facecolor=CARD, edgecolor=color, lw=1.5, zorder=z))
    f = 2.6*s; w = 1.7*s
    tip = c + d*b*0.4
    fr = [tip + n*0.5*s, tip - n*0.5*s, tip + d*f - n*w, tip + d*f + n*w]
    ax.add_patch(Polygon(fr, closed=True, facecolor=color, alpha=0.10, edgecolor=color,
                 lw=1.4, zorder=z))

def photo(ax, x, y, w, h, seed=0, ec=MUT, z=3):
    """Stylized photo thumbnail: card + tiny skyline/hill scene."""
    rng = np.random.default_rng(seed)
    box(ax, x, y, w, h, ec=ec, fc="#10141b", z=z, r=0.9)
    gy = y + h*0.32
    ax.plot([x+w*0.07, x+w*0.93], [gy, gy], color=MUT, lw=1.0, alpha=0.7, zorder=z+1)
    bx = x + w*0.14
    for i in range(3):
        bw = w*0.16; bh = h*(0.18 + 0.3*rng.random())
        ax.add_patch(Rectangle((bx, gy), bw, bh, facecolor="#232a35",
                     edgecolor=MUT, lw=0.7, zorder=z+1))
        bx += bw + w*0.09
    ax.add_patch(Circle((x+w*0.8, y+h*0.78), min(w,h)*0.075, facecolor=GOLD,
                 edgecolor="none", alpha=0.9, zorder=z+1))

# ---- real 3D house: KayKit Medieval Hexagon Pack (CC0), building_home_B ----
HOUSE_OBJ = os.path.normpath(os.path.join(os.path.dirname(__file__),
            "../assets/building_home_B_red.obj"))

def load_obj(path):
    """Vertices + triangulated faces from a Wavefront OBJ (v/f lines only)."""
    verts, faces = [], []
    with open(path) as fh:
        for line in fh:
            if line.startswith("v "):
                verts.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("f "):
                idx = [int(tok.split("/")[0]) - 1 for tok in line.split()[1:]]
                for i in range(1, len(idx) - 1):        # fan-triangulate
                    faces.append((idx[0], idx[i], idx[i+1]))
    return np.array(verts), np.array(faces)

def sample_mesh(n=700, seed=3):
    """Area-weighted random points on the house surface (3D, y-up).
    Returns (points, per-point face normals)."""
    rng = np.random.default_rng(seed)
    V, F = load_obj(HOUSE_OBJ)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    nrm = np.cross(b - a, c - a)
    area = 0.5 * np.linalg.norm(nrm, axis=1)
    nrm = nrm / (np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12)
    tri = rng.choice(len(F), size=n, p=area / area.sum())
    u, v = rng.random(n), rng.random(n)
    flip = u + v > 1; u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
    P = a[tri] + u[:, None]*(b[tri]-a[tri]) + v[:, None]*(c[tri]-a[tri])
    return P, nrm[tri]

def house_view(n=700, seed=3, az=32, el=16):
    """Project the sampled house to 2D. Returns (pts, depth, shade):
    pts in a unit-wide box, depth 0=near..1=far, shade = lambertian 0..1."""
    P, Nrm = sample_mesh(n, seed)
    ta, te = np.radians(az), np.radians(el)
    def view(v3):
        x = v3[:, 0]*np.cos(ta) + v3[:, 2]*np.sin(ta)
        z = -v3[:, 0]*np.sin(ta) + v3[:, 2]*np.cos(ta)
        y = v3[:, 1]*np.cos(te) - z*np.sin(te)
        d = v3[:, 1]*np.sin(te) + z*np.cos(te)
        return x, y, d
    x, y, d = view(P)
    nx, ny, nd = view(Nrm)
    light = np.array([-0.35, 0.85, -0.4]); light /= np.linalg.norm(light)
    shade = np.abs(nx*light[0] + ny*light[1] + nd*light[2])
    x -= x.min(); y -= y.min()
    s = x.max()
    x, y = x/s, y/s
    d = (d - d.min()) / (d.max() - d.min() + 1e-9)
    # poor-man's z-buffer: drop points hidden behind nearer surfaces, else the
    # cloud reads as an X-ray (interior/back faces bleed through the facade)
    G = 72
    gx = np.clip((x * G).astype(int), 0, G - 1)
    gy = np.clip((y / max(y.max(), 1e-9) * G).astype(int), 0, G - 1)
    key = gx * G + gy
    dmin = np.full(G * G, np.inf)
    np.minimum.at(dmin, key, d)
    vis = d <= dmin[key] + 0.045
    return np.c_[x, y][vis], d[vis], shade[vis]

def house_mesh_2d(az=38, el=18):
    """Project the house mesh: returns (tri_xy [n,3,2], depth [n], shade [n]),
    triangles sorted far-to-near for painter's-algorithm rendering."""
    V, F = load_obj(HOUSE_OBJ)
    ta, te = np.radians(az), np.radians(el)
    x = V[:, 0]*np.cos(ta) + V[:, 2]*np.sin(ta)
    z = -V[:, 0]*np.sin(ta) + V[:, 2]*np.cos(ta)
    y = V[:, 1]*np.cos(te) - z*np.sin(te)
    d = V[:, 1]*np.sin(te) + z*np.cos(te)
    x -= x.min(); y -= y.min(); s = x.max()
    P2 = np.c_[x/s, y/s]
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    nrm = np.cross(b - a, c - a)
    nrm /= (np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12)
    def rot(v3):
        rx = v3[:, 0]*np.cos(ta) + v3[:, 2]*np.sin(ta)
        rz = -v3[:, 0]*np.sin(ta) + v3[:, 2]*np.cos(ta)
        ry = v3[:, 1]*np.cos(te) - rz*np.sin(te)
        rd = v3[:, 1]*np.sin(te) + rz*np.cos(te)
        return np.c_[rx, ry, rd]
    nv = rot(nrm)
    light = np.array([-0.35, 0.85, -0.45]); light /= np.linalg.norm(light)
    shade = np.abs(nv @ light)
    td = d[F].mean(axis=1)
    order = np.argsort(-td)                    # far first
    tri = P2[F][order]
    tdn = (td[order] - td.min()) / (td.max() - td.min() + 1e-9)
    return tri, tdn, shade[order]

def house_poly(ax, ox, oy, w, color, az=38, el=18, ar=1.0, zorder=4):
    """Shaded solid render of the real house model (painter's algorithm)."""
    from matplotlib.collections import PolyCollection
    tri, d, shade = house_mesh_2d(az, el)
    base = np.array(mcolors.to_rgb(color))
    bright = (0.22 + 0.78*shade) * (1.0 - 0.18*d)
    cols = np.clip(base[None, :] * bright[:, None] * 1.30, 0, 1)
    T = tri.copy()
    T[..., 0] = ox + T[..., 0]*w
    T[..., 1] = oy + T[..., 1]*w*ar
    ax.add_collection(PolyCollection(T, facecolors=cols, edgecolors="none",
                                     zorder=zorder))

def house_scatter(ax, ox, oy, w, color, n=700, seed=3, az=32, el=16, s=6,
                  ar=1.0):
    """Scatter the projected house at (ox, oy), width w. Points are shaded by
    surface orientation (lambertian) and drawn far-to-near, so roof planes and
    walls read as distinct surfaces. `ar` corrects for non-square axis units."""
    pts, d, shade = house_view(n, seed, az, el)
    order = np.argsort(-d)                      # far first
    pts, d, shade = pts[order], d[order], shade[order]
    base = np.array(mcolors.to_rgb(color))
    bright = (0.30 + 0.70*shade) * (1.0 - 0.25*d)
    rgba = np.empty((len(pts), 4))
    rgba[:, :3] = np.clip(base[None, :] * bright[:, None] * 1.35, 0, 1)
    rgba[:, 3] = 0.95
    ax.scatter(ox + pts[:, 0]*w, oy + pts[:, 1]*w*ar, s=s, c=rgba,
               edgecolors="none", zorder=4)

def token_col(ax, x, y, cols, rows, s, gap, color=CYAN, alpha=0.9, z=4, ec="none"):
    """Grid of small square tokens; returns centers."""
    cs = []
    for r in range(rows):
        for c in range(cols):
            px, py = x + c*(s+gap), y - r*(s+gap)
            ax.add_patch(Rectangle((px, py), s, s, facecolor=color, alpha=alpha,
                         edgecolor=ec, lw=0.5, zorder=z))
            cs.append((px+s/2, py+s/2))
    return np.array(cs)

# ---------------------------------------------------------------- fig 2: problem
def fig_problem():
    fig, ax = newfig(12.3, 5.6)
    ax.text(3, 93, "the reconstruction problem", color=FG, fontsize=16, weight="bold")
    ax.text(3, 86.5, "from photos alone, recover where the cameras were and where every point is",
            color=MUT, fontsize=11.5)
    # left: stack of photos
    for i, (dx, dy) in enumerate([(0, 0), (3.5, -9), (7, -18)]):
        photo(ax, 5+dx, 47+dy, 17, 22, seed=i, z=3+i)
    ax.text(16, 18, "input photos", color=MUT, fontsize=12, ha="center")
    arrow(ax, (33, 50), (44, 50), color=FG, lw=2.4, ms=20)
    ax.text(38.5, 54, "?", color=GOLD, fontsize=20, ha="center", weight="bold")
    # right: shared 3D frame — the real house model, shaded render
    house_poly(ax, 58, 13, 19, "#b9c4d4", az=38, el=18, ar=12.3/5.6)
    cams = [(50, 20, 14), (52, 74, -32), (88, 76, -137), (94, 30, 158)]
    for cx, cy, a in cams:
        camera(ax, cx, cy, a, CYAN, s=1.5)
    ax.text(73, 10, "camera poses  +  3D geometry, in one shared frame",
            color=FG, fontsize=12.5, ha="center")
    ax.text(73, 4.5, "every method below is a different way to produce this",
            color=MUT, fontsize=10.5, ha="center")
    save(fig, "problem.png")

# ---------------------------------------------------------- fig 3: sfm pipeline
def fig_sfm_pipeline():
    fig, ax = newfig(12.3, 4.9)
    ax.text(3, 91, "classical SfM + MVS: match, then optimize", color=FG,
            fontsize=16, weight="bold")
    y0, h = 22, 47
    # stage 1
    box(ax, 4, y0, 26, h, ec=MUT)
    ax.text(17, y0+h+5, "1 · feature matching", color=FG, fontsize=12.5, ha="center")
    photo(ax, 6.5, y0+22, 9.5, 15, seed=1, z=3)
    photo(ax, 18.5, y0+8, 9.5, 15, seed=2, z=3)
    rng = np.random.default_rng(5)
    for i in range(6):
        p0 = (8+rng.random()*6, y0+25+rng.random()*9)
        p1 = (20+rng.random()*6, y0+11+rng.random()*9)
        good = i != 4
        ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=GREEN if good else RED,
                lw=1.1, alpha=0.9, zorder=6)
        for p in (p0, p1):
            ax.add_patch(Circle(p, 0.45, facecolor=GREEN if good else RED,
                         edgecolor="none", zorder=7))
    arrow(ax, (31, y0+h/2), (36.5, y0+h/2), color=FG, lw=2.2, ms=17)
    # stage 2 (gold, iterative core)
    box(ax, 37.5, y0, 26, h, ec=GOLD, lw=2.0)
    ax.text(50.5, y0+h+5, "2 · bundle adjustment", color=GOLD, fontsize=12.5,
            ha="center", weight="bold")
    rng = np.random.default_rng(11)
    pts = rng.random((14, 2)) * np.array([12, 11]) + np.array([44.5, y0+13])
    ax.scatter(pts[:, 0], pts[:, 1], s=12, c=GOLD, alpha=0.95, zorder=6)
    for p in pts[:6]:
        d = rng.normal(0, 1.3, 2)
        ax.plot([p[0], p[0]+d[0]], [p[1], p[1]+d[1]], color=RED, lw=1.5,
                alpha=0.9, zorder=5)
    camera(ax, 41.5, y0+6, 50, CYAN, s=1.1); camera(ax, 59.5, y0+7, 130, CYAN, s=1.1)
    # iterate loop: a near-closed circular arrow
    from matplotlib.patches import Arc
    lc, lyc, lr = 50.5, y0+37.5, 3.4
    ax.add_patch(Arc((lc, lyc), lr*2.4, lr*1.6, angle=0, theta1=-55, theta2=235,
                 color=GOLD, lw=1.8, zorder=6))
    tip = np.radians(-55)
    tx, ty = lc + 1.2*lr*np.cos(tip), lyc + 0.8*lr*np.sin(tip)
    ax.add_patch(FancyArrowPatch((tx-0.7, ty+0.9), (tx+0.25, ty-0.35),
                 arrowstyle="-|>", mutation_scale=13, color=GOLD, lw=1.6, zorder=6))
    ax.text(50.5, y0+29.5, "iterate until convergence", color=GOLD, fontsize=9.5,
            ha="center", style="italic")
    ax.text(50.5, y0-6.5, "slow · needs a good initial guess", color=MUT,
            fontsize=10, ha="center")
    arrow(ax, (64.5, y0+h/2), (70, y0+h/2), color=FG, lw=2.2, ms=17)
    # stage 3
    box(ax, 71, y0, 26, h, ec=MUT)
    ax.text(84, y0+h+5, "3 · dense multi-view stereo", color=FG, fontsize=12.5, ha="center")
    house_scatter(ax, 79, y0+3, 10, CYAN, n=2000, seed=8, s=2.2, az=38, el=18,
                  ar=12.3/4.9)
    ax.text(84, y0-6.5, "sparse points → dense surface", color=MUT, fontsize=10, ha="center")
    save(fig, "sfm-pipeline.png")

# ------------------------------------------------------ fig 4: sfm limitations
def fig_sfm_limitations():
    fig, ax = newfig(12.3, 6.2)
    ax.text(3, 94, "where the optimizer breaks", color=FG, fontsize=16, weight="bold")
    y0, h, w = 50, 34, 28.5
    panels = [(4, "a · textureless surfaces"), (35.75, "b · repeated structure"),
              (67.5, "c · too little overlap")]
    for x, _t in panels:
        box(ax, x, y0, w, h, ec=MUT)
    # (a) blank wall, failed matches
    x = 4
    ax.add_patch(Rectangle((x+4, y0+8), w-8, h-16, facecolor="#151a22",
                 edgecolor=MUT, lw=1.0, zorder=3))
    for px, py in [(x+9, y0+17), (x+15, y0+13), (x+21, y0+19)]:
        ax.plot([px-1.1, px+1.1], [py-1.1, py+1.1], color=RED, lw=1.8, zorder=5)
        ax.plot([px-1.1, px+1.1], [py+1.1, py-1.1], color=RED, lw=1.8, zorder=5)
    ax.text(x+w/2, y0+3.5, "nothing to match", color=RED, fontsize=10.5, ha="center")
    ax.text(panels[0][0]+w/2, y0-5, panels[0][1], color=FG, fontsize=12, ha="center")
    # (b) identical windows, crossed matches
    x = 35.75
    for i in range(4):
        ax.add_patch(Rectangle((x+4.2+i*5.6, y0+12), 4.0, 9, facecolor="#151a22",
                     edgecolor=CYAN, lw=1.2, zorder=3))
        ax.plot([x+6.2+i*5.6]*2, [y0+12, y0+21], color=CYAN, lw=0.7, alpha=0.6, zorder=4)
        ax.plot([x+4.2+i*5.6, x+8.2+i*5.6], [y0+16.5]*2, color=CYAN, lw=0.7, alpha=0.6, zorder=4)
    # wrong correspondences: arcs pairing window 0->2 and 1->3, arcing ABOVE
    ax.add_patch(FancyArrowPatch((x+6.2, y0+21.5), (x+17.4, y0+21.5), arrowstyle="-",
                 connectionstyle="arc3,rad=-0.42", color=RED, lw=1.6, zorder=5))
    ax.add_patch(FancyArrowPatch((x+11.8, y0+21.5), (x+23.0, y0+21.5), arrowstyle="-",
                 connectionstyle="arc3,rad=-0.42", color=RED, lw=1.6, zorder=5))
    ax.text(x+w/2, y0+3.5, "which window is which?", color=RED, fontsize=10.5, ha="center")
    ax.text(panels[1][0]+w/2, y0-5, panels[1][1], color=FG, fontsize=12, ha="center")
    # (c) two barely-overlapping frustums
    x = 67.5
    camera(ax, x+6, y0+9, 38, MUT, s=1.15)
    camera(ax, x+23, y0+9, 142, MUT, s=1.15)
    for cx, aa in [(x+6, 38), (x+23, 142)]:
        th = np.radians(aa)
        for spread in (-14, 14):
            t2 = np.radians(aa+spread)
            ax.plot([cx, cx+16*np.cos(t2)], [y0+9, y0+9+16*np.sin(t2)],
                    color=MUT, lw=0.9, ls=":", alpha=0.9, zorder=4)
    ax.add_patch(Circle((x+14.5, y0+22), 1.1, facecolor=GOLD, edgecolor="none", zorder=5))
    ax.text(x+17.5, y0+24, "?", color=GOLD, fontsize=13, ha="center", weight="bold")
    ax.text(x+w/2, y0+3.5, "depth is ambiguous", color=RED, fontsize=10.5, ha="center")
    ax.text(panels[2][0]+w/2, y0-5, panels[2][1], color=FG, fontsize=12, ha="center")
    # bottom strip: local minimum
    xs = np.linspace(8, 92, 400)
    ys = 20 - 7*np.exp(-((xs-64)/7.5)**2) - 4.4*np.exp(-((xs-33)/5.5)**2) \
         + 1.5*np.sin(xs/6.0)
    ys = ys - ys.min() + 8
    ax.plot(xs, ys, color=MUT, lw=1.8, zorder=3)
    bx = 33.6
    byi = np.interp(bx, xs, ys)
    ax.add_patch(Circle((bx, byi+1.5), 1.5, facecolor=GOLD, edgecolor="none", zorder=5))
    ax.text(33, 24, "stuck in a local minimum", color=GOLD, fontsize=11, ha="center")
    ax.text(64, 3.5, "the right answer, never reached", color=MUT, fontsize=10.5, ha="center")
    arrow(ax, (52, 24), (62.5, 15.5), color=MUT, lw=1.2, ms=10, rad=-0.25)
    save(fig, "sfm-limitations.png")

# ----------------------------------------------------- fig 5: dust3r pointmap
def fig_dust3r():
    fig, ax = newfig(12.3, 5.8)
    ax.text(3, 93.5, "DUSt3R: geometry as regression", color=FG, fontsize=16, weight="bold")
    # LEFT: two photos -> pointmaps in one frame, color = correspondence
    ax.text(24, 84, "a pointmap: every pixel gets an (x, y, z)", color=MUT, fontsize=11.5,
            ha="center")
    gw, gh = 7, 5
    def grad_grid(x, y, s, gap, hue0, z=4):
        cs = []
        for r in range(gh):
            for c in range(gw):
                hue = (hue0 + 0.5*c/gw + 0.25*r/gh) % 1.0
                col = mcolors.hsv_to_rgb((hue, 0.65, 0.95))
                px, py = x + c*(s+gap), y - r*(s+gap)
                ax.add_patch(Rectangle((px, py), s, s, facecolor=col, edgecolor="none",
                             alpha=0.95, zorder=z))
                cs.append((px+s/2, py+s/2, hue))
        return cs
    g1 = grad_grid(5, 74, 1.7, 0.45, 0.52)
    g2 = grad_grid(5, 42, 1.7, 0.45, 0.60)
    ax.text(12.5, 77.5, "image 1", color=MUT, fontsize=10, ha="center")
    ax.text(12.5, 45.5, "image 2", color=MUT, fontsize=10, ha="center")
    arrow(ax, (22, 68), (29, 60), color=FG, lw=1.8, ms=13, rad=-0.15)
    arrow(ax, (22, 36), (29, 44), color=FG, lw=1.8, ms=13, rad=0.15)
    ax.text(25.0, 52, "ViT", color=FG, fontsize=11, ha="center",
            bbox=dict(boxstyle="round,pad=0.4", fc=CARD, ec=MUT, lw=1.2))
    # shared 3D frame: scatter the same colors inside the box, overlapping
    rng = np.random.default_rng(4)
    for cs, (ox, oy) in [(g1, (32.5, 64.0)), (g2, (35.5, 59.5))]:
        px0, py0 = cs[0][0], cs[0][1]
        for (px, py, hue) in cs:
            col = mcolors.hsv_to_rgb((hue, 0.65, 0.95))
            X = ox + (px-px0)*1.05 + rng.normal(0, 0.2)
            Y = oy - (py0-py)*2.0 + rng.normal(0, 0.2)
            ax.add_patch(Circle((X, Y), 0.42, facecolor=col, edgecolor="none",
                         alpha=0.9, zorder=5))
    box(ax, 30, 28, 21.5, 42, ec=MUT, fc="none", lw=1.1)
    ax.text(40.7, 25, "one shared 3D frame —\nsame color = same point, matching is free",
            color=FG, fontsize=10.5, ha="center", va="top")
    # RIGHT: pairwise explosion
    ax.text(76, 84, "but it only eats pairs", color=MUT, fontsize=11.5, ha="center")
    N = 8; cx, cy, R = 76, 50, 20
    angs = np.linspace(0, 2*np.pi, N, endpoint=False) + np.pi/2
    P = np.c_[cx + R*np.cos(angs), cy + R*np.sin(angs)]
    segs = [[P[i], P[j]] for i in range(N) for j in range(i+1, N)]
    ax.add_collection(LineCollection(segs, colors=RED, lw=1.0, alpha=0.45, zorder=3))
    for i, p in enumerate(P):
        photo(ax, p[0]-3.4, p[1]-2.4, 6.8, 4.8, seed=i+10, z=5)
    ax.text(76, 21.5, "N images → N·(N−1)/2 pairs to glue\n“global alignment” = an optimizer again",
            color=RED, fontsize=10.5, ha="center")
    save(fig, "dust3r-pointmap.png")

# --------------------------------------------------------- fig 6: vggt arch
def fig_vggt_arch():
    fig, ax = newfig(12.3, 5.6, ylim=(20, 100))
    ax.text(3, 93.5, "VGGT: every view at once, one pass", color=FG, fontsize=16, weight="bold")
    # input frames
    for i, dy in enumerate([0, -14, -28]):
        photo(ax, 3, 62+dy, 10, 11, seed=i+3)
    ax.text(8, 27, "N frames", color=MUT, fontsize=10, ha="center")
    arrow(ax, (14, 55), (18.5, 55), color=FG, lw=2, ms=14)
    # DINO encoder
    box(ax, 19, 40, 9, 30, ec=MUT)
    ax.text(23.5, 55, "DINOv2\nencoder", color=FG, fontsize=10.5, ha="center", va="center")
    arrow(ax, (29, 55), (33.5, 55), color=FG, lw=2, ms=14)
    # token columns: camera token + registers + patch grid
    for i, x in enumerate([35, 44, 53]):
        ax.add_patch(Rectangle((x, 68), 2.2, 2.2, facecolor=GOLD, edgecolor="none", zorder=5))
        for k in range(3):
            ax.add_patch(Rectangle((x+3.0+k*1.35, 68.35), 1.0, 1.5, facecolor=PURP,
                         edgecolor="none", zorder=5, alpha=0.95))
        token_col(ax, x, 64.5, 5, 8, 1.35, 0.28, color=CYAN, alpha=0.85)
    ax.text(36.1, 73.3, "camera token", color=GOLD, fontsize=9.5)
    ax.text(47.5, 73.3, "registers", color=PURP, fontsize=9.5)
    ax.text(46.5, 47.5, "tokens per frame", color=MUT, fontsize=10, ha="center")
    arrow(ax, (62, 55), (66, 55), color=FG, lw=2, ms=14)
    # alternating attention stack
    box(ax, 67, 28, 15, 52, ec=CYAN, lw=1.8)
    ax.text(74.5, 83, "alternating attention  × L", color=CYAN, fontsize=11, ha="center")
    # frame attention row
    ax.text(74.5, 72.5, "frame", color=FG, fontsize=9.5, ha="center")
    for x in (69.5, 73.5, 77.5):
        pts = token_col(ax, x, 69, 2, 3, 0.9, 0.25, color=CYAN, alpha=0.8)
        segs = [[pts[i], pts[j]] for i in range(len(pts)) for j in range(i+1, len(pts))]
        ax.add_collection(LineCollection(segs, colors=FG, lw=0.4, alpha=0.35, zorder=3))
    # global attention row (dense mesh)
    ax.text(74.5, 58, "global — all·to·all", color=RED, fontsize=9.5, ha="center")
    cols = [(70.2, 52), (74.5, 52), (78.8, 52)]
    allp = []
    for x, y in cols:
        allp += [(x+dx, y-dy) for dx in (0, 1.2) for dy in (0, 1.4, 2.8)]
    allp = np.array(allp)
    segs = [[allp[i], allp[j]] for i in range(len(allp)) for j in range(i+1, len(allp))]
    ax.add_collection(LineCollection(segs, colors=RED, lw=0.4, alpha=0.35, zorder=4))
    ax.scatter(allp[:, 0], allp[:, 1], s=6, c=CYAN, zorder=5)
    ax.text(74.5, 44, "the cost center:\n(F·T)² interactions", color=RED, fontsize=9.5,
            ha="center")
    ax.text(74.5, 33.5, "…alternate, repeat", color=MUT, fontsize=9, ha="center",
            style="italic")
    arrow(ax, (83, 55), (86.5, 55), color=FG, lw=2, ms=14)
    # heads
    box(ax, 87.5, 56, 10.5, 14, ec=GOLD)
    ax.text(92.7, 63, "camera\nhead", color=GOLD, fontsize=10, ha="center", va="center")
    box(ax, 87.5, 38, 10.5, 14, ec=MUT)
    ax.text(92.7, 45, "DPT dense\nheads", color=FG, fontsize=10, ha="center", va="center")
    ax.text(92.7, 74, "poses", color=MUT, fontsize=9.5, ha="center")
    arrow(ax, (92.7, 70.5), (92.7, 72.3), color=MUT, lw=1.4, ms=9)
    ax.text(92.7, 30.5, "depth · pointmaps · tracks", color=MUT, fontsize=9.5, ha="center")
    arrow(ax, (92.7, 37.5), (92.7, 34.2), color=MUT, lw=1.4, ms=9)
    save(fig, "vggt-arch.png")

# ------------------------------------------- fig 7: global attention wall
def fig_global_wall():
    fig, ax = newfig(12.3, 5.6)
    ax.text(3, 93.5, "the wall: quadratic attention, mostly unused", color=FG,
            fontsize=16, weight="bold")
    # LEFT: the thicket
    F, rows, cols = 4, 8, 2
    xs = [8, 20, 32, 44]
    allpts = []
    for x in xs:
        pts = token_col(ax, x, 76, cols, rows, 2.1, 0.8, color=CYAN, alpha=0.9)
        allpts.append(pts)
        ax.text(x+2.9, 80.5, "frame", color=MUT, fontsize=9, ha="center")
    P = np.vstack(allpts)
    segs, colors = [], []
    for i in range(len(P)):
        for j in range(i+1, len(P)):
            segs.append([P[i], P[j]])
            d = abs(P[i][0]-P[j][0])
            colors.append(RED if d > 20 else CYAN)
    ax.add_collection(LineCollection(segs, colors=colors, lw=0.35, alpha=0.16, zorder=2))
    ax.text(28, 22, "global attention: every token ↔ every token", color=FG,
            fontsize=12, ha="center")
    ax.text(28, 15.5, "cost ~ (F·T)²  —  double the frames, quadruple the bill",
            color=RED, fontsize=11, ha="center")
    # RIGHT: sparse attention heatmap
    n = 64
    rng = np.random.default_rng(7)
    M = rng.random((n, n))**14 * 0.5
    M += np.eye(n) * 0.95
    for k in range(6):
        r = rng.integers(0, n)
        M[r, :] += rng.random(n)**6 * 0.6
        M[:, r] += rng.random(n)**6 * 0.5
    M = np.clip(M, 0, 1)
    ext = [62, 92, 32, 82]
    cmap = mcolors.LinearSegmentedColormap.from_list("att", ["#000000", "#0c2f42", CYAN, "#dff4ff"])
    ax.imshow(M, extent=ext, origin="lower", cmap=cmap, zorder=3, aspect="auto")
    box(ax, 62, 32, 30, 50, ec=MUT, fc="none", lw=1.2)
    ax.text(77, 86, "…but the learned attention map", color=FG, fontsize=11.5, ha="center")
    ax.text(77, 22, "is mostly dark: nearly all pairs barely talk", color=FG,
            fontsize=12, ha="center")
    ax.text(77, 15.5, "paying quadratic for near-empty traffic", color=GOLD,
            fontsize=11, ha="center", style="italic")
    save(fig, "global-attention-wall.png")

# ------------------------------------------- fig 8: register attention relay
def fig_register_relay():
    fig, ax = newfig(12.3, 6.0, ylim=(21, 100))
    ax.text(3, 95, "register attention: a two-step relay", color=FG, fontsize=16,
            weight="bold")
    xs = [12, 36, 60, 84]
    reg_pts, tok_pts = [], []
    for fi, x in enumerate(xs):
        # registers strip (gold) — 4 squares standing in for the 16
        rp = []
        for k in range(4):
            px = x - 5.7 + k*3.2
            ax.add_patch(Rectangle((px, 60), 2.4, 2.4, facecolor=GOLD,
                         edgecolor="none", zorder=6))
            rp.append((px+1.2, 62.5))
        reg_pts.append(np.array(rp))
        tp = token_col(ax, x-6.5, 54, 6, 7, 1.75, 0.45, color=CYAN, alpha=0.75, z=4)
        tok_pts.append(tp)
        ax.text(x, 36.5, f"frame {fi+1}", color=MUT, fontsize=9.5, ha="center")
    # STEP 1: cross-frame arcs among registers only, bowing UP above the strips
    for i in range(len(xs)):
        for j in range(i+1, len(xs)):
            span = j - i
            for a in (0, 2, 3):
                p0 = reg_pts[i][a]; p1 = reg_pts[j][3-a]
                rad = -(0.42 - 0.09*span + 0.03*a)
                ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-",
                             connectionstyle=f"arc3,rad={rad}",
                             color=GOLD, lw=1.0, alpha=0.55, zorder=5))
    ax.text(48, 88.5, "① register attention — only the 16 registers per frame meet across frames",
            color=GOLD, fontsize=12.5, ha="center")
    # STEP 2: within-frame briefing (registers → their own tokens)
    for x, tp, rp in zip(xs, tok_pts, reg_pts):
        c = rp.mean(axis=0)
        for t in tp[::4]:
            ax.plot([c[0], t[0]], [c[1]-2.6, t[1]], color=CYAN, lw=0.7,
                    alpha=0.5, zorder=3)
    ax.text(48, 31, "② frame attention — each frame’s registers brief their own tokens, locally",
            color=CYAN, fontsize=12.5, ha="center")
    ax.text(48, 24.5, "cross-frame cost now scales with F·R (R = 16), not F·T (T ≈ thousands)   ·   "
            "VGGT-Ω swaps 25% of global layers for this — accuracy unchanged",
            color=MUT, fontsize=10, ha="center")
    save(fig, "register-attention.png")

# ---------------------------------------- fig 8b: attention cost (exact)
def fig_attention_cost():
    """Exact interaction counts per attention layer.
    T = 1024 image tokens (a 512x512 input at VGGT-Omega's 16px patches),
    R = 16 registers, +1 camera token -> N = 1041 tokens per frame."""
    T, R = 1024, 16
    N = T + R + 1
    F = np.geomspace(2, 1000, 200)
    fig = plt.figure(figsize=(12.3, 4.9)); fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0.09, 0.16, 0.60, 0.68]); ax.set_facecolor(BG)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.plot(F, (F*N)**2, color=RED, lw=2.4, zorder=4)
    ax.plot(F, (F*R)**2, color=GOLD, lw=2.4, zorder=4)
    ax.plot(F, F*(N**2), color=MUT, lw=1.6, ls="--", zorder=3)
    fig.text(0.09, 0.93, "swap a global layer for a register layer — exact counts",
             fontsize=16, weight="bold", color=FG)
    ax.set_xlabel("frames F  (log)", color=MUT, fontsize=11.5)
    ax.set_ylabel("token–token interactions\nper layer  (log)", color=MUT, fontsize=11.5)
    ax.tick_params(labelsize=10)
    for s in ["top", "right"]: ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]: ax.spines[s].set_color(MUT)
    ax.grid(True, which="major", color="#1a2029", lw=0.7, zorder=0)
    # constant vertical gap between the two quadratic curves: (N/R)^2
    gap = (N / R) ** 2
    fx = 30
    ax.annotate("", (fx, (fx*R)**2), (fx, (fx*N)**2),
                arrowprops=dict(arrowstyle="<->", color=FG, lw=1.4))
    ax.text(fx*1.3, np.sqrt((fx*N)**2 * (fx*R)**2),
            f"≈{gap:,.0f}× fewer,\nat any F", color=FG, fontsize=11.5, va="center")
    # right-side legend text
    fig.text(0.72, 0.72, "global attention layer", color=RED, fontsize=12.5, weight="bold")
    fig.text(0.72, 0.66, "(F·N)² — every token ↔ every token", color=MUT, fontsize=10)
    fig.text(0.72, 0.56, "register attention layer", color=GOLD, fontsize=12.5, weight="bold")
    fig.text(0.72, 0.50, "(F·R)² — only registers meet", color=MUT, fontsize=10)
    fig.text(0.72, 0.40, "frame attention layer", color=MUT, fontsize=12.5)
    fig.text(0.72, 0.34, "F·N² — unchanged in both models", color=MUT, fontsize=10)
    fig.text(0.09, 0.03, "exact arithmetic, N = 1041 tokens per frame "
             "(1024 image tokens at 512×512 / 16px patches + 16 registers + 1 camera token), R = 16",
             fontsize=9, color=MUT)
    save(fig, "attention-cost.png")

# --------------------------------------------------- fig 9: data engine
def fig_data_engine():
    fig, ax = newfig(12.3, 5.2)
    ax.text(3, 92.5, "the data engine: the old enemy as teacher", color=FG,
            fontsize=16, weight="bold")
    y, h = 52, 20
    def stage(x, w, label, sub=None, ec=MUT, tc=FG, lw=1.5):
        box(ax, x, y, w, h, ec=ec, lw=lw)
        ax.text(x+w/2, y+h/2 + (2.2 if sub else 0), label, color=tc, fontsize=10.5,
                ha="center", va="center", weight="bold" if ec == GOLD else "normal")
        if sub:
            ax.text(x+w/2, y+h/2-3.6, sub, color=MUT, fontsize=8.8, ha="center")
    stage(3, 13, "40M internet\nvideos")
    arrow(ax, (16.4, y+h/2), (18.6, y+h/2), color=FG, lw=1.8, ms=12)
    stage(19, 14, "VLM pre-filter", "drops ~half", ec=MUT)
    arrow(ax, (33.4, y+h/2), (35.6, y+h/2), color=FG, lw=1.8, ms=12)
    stage(36, 16, "matching ensemble", "+ dynamic-object masks")
    arrow(ax, (52.4, y+h/2), (54.6, y+h/2), color=FG, lw=1.8, ms=12)
    stage(55, 17, "COLMAP bundle\nadjustment", None, ec=GOLD, tc=GOLD, lw=2.0)
    ax.text(63.5, y-7, "pseudo-labels from the optimizer\nthis model replaces", color=GOLD,
            fontsize=9, ha="center", va="top", style="italic")
    arrow(ax, (72.4, y+h/2), (74.6, y+h/2), color=FG, lw=1.8, ms=12)
    stage(75, 14, "aggressive\nquality filter", None)
    arrow(ax, (89.4, y+h/2), (91.2, y+h/2), color=FG, lw=1.8, ms=12)
    # outputs
    box(ax, 3, 12, 34, 14, ec=MUT)
    ax.text(20, 19, "~3M curated dataset sequences", color=FG, fontsize=10.5, ha="center")
    box(ax, 60, 12, 25, 14, ec=MUT)
    ax.text(72.5, 21.5, "0.8M labeled sequences", color=FG, fontsize=10.5, ha="center")
    ax.text(72.5, 16.5, "~1/3 dynamic scenes", color=MUT, fontsize=9.5, ha="center")
    ax.plot([91.5, 91.5], [y+h/2, 19], color=FG, lw=1.8)
    ax.plot([91.5, 86.5], [19, 19], color=FG, lw=1.8)
    arrow(ax, (86.5, 19), (85.6, 19), color=FG, lw=1.8, ms=12)
    # merge
    arrow(ax, (37.5, 19), (43.3, 19), color=FG, lw=1.8, ms=12)
    box(ax, 44, 10, 12.5, 18, ec=GREEN, lw=2.0)
    ax.text(50.2, 21.5, "4M total", color=GREEN, fontsize=12.5, ha="center", weight="bold")
    ax.text(50.2, 15.5, "15× VGGT", color=GREEN, fontsize=10.5, ha="center")
    arrow(ax, (60, 19), (57.3, 19), color=FG, lw=1.8, ms=12)
    ax.text(50, 2.5, "videos that fail labeling still feed self-supervised teacher–student training (18M clips) — the supporting act",
            color=MUT, fontsize=9.5, ha="center")
    save(fig, "data-engine.png")

# ------------------------------------------------------- fig 10: scaling laws
def fig_scaling():
    fig = plt.figure(figsize=(12.3, 4.6)); fig.patch.set_facecolor(BG)
    fig.suptitle("scaling laws for reconstruction — published values", x=0.055, y=0.96,
                 ha="left", fontsize=16, weight="bold", color=FG)
    model_x = np.array([0.2, 1, 5, 10])
    model_y = np.array([0.107, 0.073, 0.057, 0.046])
    data_y = np.array([0.275, 0.210, 0.160, 0.129, 0.073])
    data_x = np.geomspace(2e3, 2e6, len(data_y))
    for k, (xv, yv, col, xl, tt) in enumerate([
            (model_x, model_y, CYAN, "model parameters", "grow the model 0.2B → 10B"),
            (data_x, data_y, GOLD, "training sequences", "grow the data 2K → 2M")]):
        ax = fig.add_subplot(1, 2, k+1)
        ax.set_facecolor(BG)
        ax.set_xscale("log")
        ax.plot(xv, yv, color=col, lw=2.2, zorder=3)
        ax.scatter(xv, yv, s=42, c=col, edgecolor=BG, lw=1.2, zorder=4)
        for xi, yi in zip(xv, yv):
            ax.annotate(f"{yi:.3f}", (xi, yi), textcoords="offset points",
                        xytext=(2, 9), fontsize=10, color=FG)
        ax.set_title(tt, color=col, fontsize=12.5, pad=10)
        ax.set_xlabel(xl + "  (log scale)", color=MUT, fontsize=11)
        if k == 0:
            ax.set_ylabel("3D point error  (lower is better)", color=MUT, fontsize=11)
            ax.set_xticks([0.2, 1, 5, 10])
            ax.set_xticklabels(["0.2B", "1B", "5B", "10B"])
            ax.set_ylim(0.035, 0.125)
        else:
            ax.set_xticks([1e4, 1e5, 1e6])
            ax.set_ylim(0.05, 0.31)
        ax.tick_params(labelsize=10)
        for s in ["top", "right"]:
            ax.spines[s].set_visible(False)
        for s in ["left", "bottom"]:
            ax.spines[s].set_color(MUT)
        ax.grid(True, which="major", color="#1a2029", lw=0.7, zorder=0)
    fig.text(0.055, 0.015, "point-error values as published (VGGT-Ω, Fig. 1); "
             "x-positions on the data curve interpolated between the reported 2K → 2M endpoints",
             fontsize=9, color=MUT)
    fig.subplots_adjust(left=0.075, right=0.97, top=0.78, bottom=0.21, wspace=0.22)
    save(fig, "scaling.png")

# ------------------------------------------- fig 11: vggt-omega limitations
def fig_limitations():
    fig, ax = newfig(12.3, 5.4)
    ax.text(3, 93, "what it still can’t do", color=FG, fontsize=16, weight="bold")
    y0, h, w = 24, 52, 28.5
    xs = [4, 35.75, 67.5]
    for x in xs:
        box(ax, x, y0, w, h, ec=MUT)
    # (a) scale ambiguity
    x = xs[0]
    for w_, ox, lab in [(4.5, 4.5, "dollhouse?"), (9, 14.5, "real house?")]:
        house_poly(ax, x+ox, y0+12, w_, CYAN, az=38, el=18, ar=12.3/5.4)
        ax.text(x+ox+w_/2, y0+8, lab, color=MUT, fontsize=9.5, ha="center")
    ax.text(x+w/2, y0+h-7, "same pixels, either answer", color=FG, fontsize=10.5, ha="center")
    ax.text(x+w/2, y0+h-13, "scale needs outside cues", color=GOLD, fontsize=10, ha="center")
    ax.text(x+w/2, y0-6, "a · metric scale", color=FG, fontsize=12, ha="center")
    # (b) hallucination
    x = xs[1]
    t = np.linspace(0, 1, 120)
    true_y = y0 + 18 + 14*np.exp(-((t-0.45)/0.3)**2)
    pred_y = y0 + 18 + 14*np.exp(-((t-0.62)/0.22)**2) + 6*np.exp(-((t-0.2)/0.1)**2)
    X = x + 3 + t*(w-6)
    ax.plot(X, true_y, color=RED, lw=1.6, ls="--", alpha=0.8, zorder=4)
    ax.plot(X, pred_y, color=CYAN, lw=2.2, zorder=5)
    ax.text(x+w-4, y0+35, "predicted", color=CYAN, fontsize=9.5, ha="right")
    ax.text(x+w-4, y0+13.5, "true surface", color=RED, fontsize=9.5, ha="right")
    ax.text(x+w/2, y0+h-7, "confident, plausible, wrong —", color=FG, fontsize=10.5, ha="center")
    ax.text(x+w/2, y0+h-13, "and no residual to warn you", color=GOLD, fontsize=10, ha="center")
    ax.text(x+w/2, y0-6, "b · off-distribution hallucination", color=FG, fontsize=12, ha="center")
    # (c) precision gap: bullseye
    x = xs[2]; cx, cyy = x+w/2, y0+24
    for r, a in [(11, 0.25), (7.5, 0.35), (4, 0.5)]:
        ax.add_patch(Circle((cx, cyy), r, facecolor="none", edgecolor=MUT,
                     lw=1.0, alpha=a, zorder=3))
    rng = np.random.default_rng(2)
    ba = rng.normal(0, 0.6, (14, 2)) + [cx, cyy]
    ff = rng.normal(0, 3.4, (14, 2)) + [cx, cyy]
    ax.scatter(ff[:, 0], ff[:, 1], s=14, c=CYAN, alpha=0.9, zorder=4)
    ax.scatter(ba[:, 0], ba[:, 1], s=14, c=GOLD, alpha=0.95, zorder=5)
    ax.text(x+w/2, y0+h-7, "bundle adjustment: hundredths of a degree", color=GOLD,
            fontsize=9.8, ha="center")
    ax.text(x+w/2, y0+h-13, "feed-forward: not there (yet)", color=CYAN, fontsize=10,
            ha="center")
    ax.text(x+w/2, y0-6, "c · peak precision", color=FG, fontsize=12, ha="center")
    ax.text(50, 6, "the paper’s own framing: feed-forward output makes an excellent initialization for optimization when you need the last decimal",
            color=MUT, fontsize=10, ha="center", style="italic")
    save(fig, "vggt-omega-limitations.png")

# ---------------------------------------- fig 12: future spatial foundation
def fig_future():
    fig, ax = newfig(12.3, 5.2)
    ax.text(3, 92.5, "reconstruction as a pretext task for spatial intelligence",
            color=FG, fontsize=16, weight="bold")
    # video stack
    for i, (dx, dy) in enumerate([(0, 0), (1.8, -2.5), (3.6, -5)]):
        photo(ax, 4+dx, 56+dy, 13, 14, seed=i+6, z=3+i)
    ax.text(12.5, 42, "oceans of video", color=MUT, fontsize=10.5, ha="center")
    arrow(ax, (22, 57), (27.5, 57), color=FG, lw=2.2, ms=16)
    box(ax, 28.5, 46, 17, 22, ec=CYAN, lw=1.8)
    ax.text(37, 59.5, "VGGT-Ω", color=CYAN, fontsize=13, ha="center", weight="bold")
    ax.text(37, 52.5, "predict the scene", color=MUT, fontsize=10, ha="center")
    arrow(ax, (46.5, 57), (52, 57), color=FG, lw=2.2, ms=16)
    # register block
    box(ax, 53, 44, 16, 26, ec=GOLD, lw=2.2)
    for r in range(2):
        for c in range(4):
            ax.add_patch(Rectangle((55.4+c*2.9, 58.5-r*3.6), 2.2, 2.4,
                         facecolor=GOLD, edgecolor="none", zorder=5))
    ax.text(61, 49.5, "registers:\na compact spatial\nrepresentation", color=FG,
            fontsize=9.8, ha="center", va="center")
    # fan out
    targets = [(84, 79, "language alignment", "97% top-3 scene retrieval", PURP),
               (84, 52, "robots / VLA", "LIBERO: 97.1 → 98.5% success", GREEN),
               (84, 25, "motion & mapping", "emergent motion segmentation", CYAN)]
    for ty, rad in zip(targets, (0.25, 0.0, -0.25)):
        arrow(ax, (69.5, 57), (75.5, ty[1]), color=ty[4], lw=1.8, ms=13, rad=rad)
    for (tx, ty, lab, sub, col) in targets:
        box(ax, 76.5, ty-8, 21, 16, ec=col, lw=1.6)
        ax.text(87, ty+3.2, lab, color=col, fontsize=11, ha="center", weight="bold")
        ax.text(87, ty-2.8, sub, color=MUT, fontsize=8.4, ha="center")
    ax.text(37, 22, "the 3D analogue of next-word prediction:\ntrain it to rebuild the world, get a sense of space for free",
            color=FG, fontsize=11.5, ha="center", style="italic")
    save(fig, "future-spatial-foundation.png")

# ------------------------------------------------------------ fig 1: social
def fig_social():
    fig, ax = newfig(12.0, 6.3)
    ax.text(6, 74, "VGGT-Ω", color=FG, fontsize=44, weight="bold")
    ax.text(6, 58, "3D reconstruction in a", color=MUT, fontsize=19)
    ax.text(6, 48, "single forward pass", color=CYAN, fontsize=19, weight="bold")
    ax.text(6, 22, "COLMAP → DUSt3R → VGGT → VGGT-Ω", color=MUT, fontsize=12)
    ax.text(6, 13, "itamar-weiss.com", color=MUT, fontsize=11)
    # register-attention motif on the right
    xs = [60, 74, 88]
    regs = []
    for x in xs:
        rp = []
        for k in range(3):
            px = x - 3.6 + k*3.0
            ax.add_patch(Rectangle((px, 62), 2.3, 3.6, facecolor=GOLD,
                         edgecolor="none", zorder=6))
            rp.append((px+1.15, 63.8))
        regs.append(rp)
        token_col(ax, x-5.5, 55, 5, 8, 2.0, 0.55, color=CYAN, alpha=0.75, z=4)
    for i in range(3):
        for j in range(i+1, 3):
            for a in range(3):
                p0 = regs[i][a]; p1 = regs[j][2-a]
                ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-",
                             connectionstyle=f"arc3,rad={0.22+0.06*a}",
                             color=GOLD, lw=1.3, alpha=0.6, zorder=5))
    save(fig, "social.png")

if __name__ == "__main__":
    fig_social(); fig_problem(); fig_sfm_pipeline(); fig_sfm_limitations()
    fig_dust3r(); fig_vggt_arch(); fig_global_wall(); fig_register_relay()
    fig_attention_cost(); fig_data_engine(); fig_scaling(); fig_limitations()
    fig_future()
