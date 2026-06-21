#!/usr/bin/env python3
"""Social-share card (1200x630) for the day/night/seasons solar-system post.

Pure-black background to match the site. Left: the post title. Right: a glowing
Sun and a tilted Earth showing the day/night terminator — the core idea the
simulation makes intuitive. This is an illustrative diagram, not a frame from
the actual Three.js simulation."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import os

BG   = "#000000"
FG   = "#ededed"
MUT  = "#8b95a5"
CYAN = "#3fc1ff"
GOLD = "#ffd166"
GREEN= "#7CFC8A"

# research/solar-system/sim/ -> repo root -> public/img/solar-system
OUT = os.path.normpath(os.path.join(os.path.dirname(__file__),
      "../../../public/img/solar-system"))
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial"],
    "text.color": FG,
})


def radial_glow(ax, cx, cy, r, color, extent, peak=1.0, n=400, falloff=2.2):
    """Soft radial glow centred at (cx, cy)."""
    x = np.linspace(extent[0], extent[1], n)
    y = np.linspace(extent[2], extent[3], n)
    X, Y = np.meshgrid(x, y)
    d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) / r
    a = np.clip(peak * np.exp(-falloff * d * d), 0, 1)
    rgb = matplotlib.colors.to_rgb(color)
    img = np.zeros((n, n, 4))
    img[..., 0], img[..., 1], img[..., 2] = rgb
    img[..., 3] = a
    ax.imshow(img, extent=extent, origin="lower", zorder=2,
              interpolation="bilinear")


def earth(ax, cx, cy, r, light_dir, tilt_deg=23.5, n=600):
    """A shaded Earth disk: lit hemisphere faces the light, dark hemisphere is
    night. Faint latitude bands hint at a globe; a tilted axis shows the 23.5°."""
    ext = [cx - r, cx + r, cy - r, cy + r]
    x = np.linspace(-1, 1, n)
    X, Y = np.meshgrid(x, x)
    R2 = X ** 2 + Y ** 2
    inside = R2 <= 1.0
    Z = np.sqrt(np.clip(1 - R2, 0, 1))           # toward viewer
    L = np.array(light_dir, dtype=float)
    L = L / np.linalg.norm(L)
    # surface normal on the visible hemisphere, lit by dot(normal, light)
    lam = np.clip(X * L[0] + Y * L[1] + Z * L[2], 0, 1)
    lam = lam ** 0.8

    # base ocean->land tint, darkened on the night side
    day_lo = np.array(matplotlib.colors.to_rgb("#0b2a4a"))   # deep ocean
    day_hi = np.array(matplotlib.colors.to_rgb("#54b8ff"))   # lit ocean/cyan
    land   = np.array(matplotlib.colors.to_rgb(GREEN))
    night  = np.array(matplotlib.colors.to_rgb("#05080d"))

    # a little fake landmass via low-freq noise so it reads as a globe
    rng = np.random.default_rng(7)
    fx, fy = rng.normal(size=(2, 6))
    fa = rng.uniform(0.5, 1.0, size=6)
    fk = rng.uniform(1.5, 3.5, size=6)
    land_mask = np.zeros_like(X)
    for i in range(6):
        land_mask += fa[i] * np.sin(fk[i] * (X * 3 + fx[i])) * \
            np.cos(fk[i] * (Y * 3 + fy[i]))
    land_mask = (land_mask > 0.6).astype(float)

    base = day_lo[None, None, :] + (day_hi - day_lo)[None, None, :] * \
        (0.4 + 0.6 * np.clip(Y * 0.5 + 0.5, 0, 1))[..., None]
    base = base * (1 - land_mask[..., None]) + land * land_mask[..., None]

    col = base * lam[..., None] + night[None, None, :] * (1 - lam[..., None])
    # terminator warm rim where lam is small but > 0
    rim = np.exp(-((lam - 0.12) ** 2) / 0.004) * (lam > 0)
    col += np.array(matplotlib.colors.to_rgb(GOLD))[None, None, :] * \
        (0.25 * rim[..., None])

    img = np.zeros((n, n, 4))
    img[..., :3] = np.clip(col, 0, 1)
    img[..., 3] = inside.astype(float)
    ax.imshow(img, extent=ext, origin="lower", zorder=4,
              interpolation="bilinear")

    # rotation axis, tilted by 23.5°
    th = np.radians(tilt_deg)
    ax_dir = np.array([np.sin(th), np.cos(th)])
    p0 = np.array([cx, cy]) - ax_dir * r * 1.28
    p1 = np.array([cx, cy]) + ax_dir * r * 1.28
    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=FG, lw=1.6,
            alpha=0.85, zorder=6)
    ax.add_patch(Circle((p1[0], p1[1]), r * 0.04, color=FG, zorder=6))


def fig_social():
    W, H = 12, 6.3
    fig = plt.figure(figsize=(W, H), dpi=100)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor(BG)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlim(0, W); ax.set_ylim(0, H)
    for s in ax.spines.values(): s.set_visible(False)
    ext = [0, W, 0, H]

    # starfield (kept clear of the title area on the left)
    rng = np.random.default_rng(42)
    for _ in range(140):
        sx = rng.uniform(0, W); sy = rng.uniform(0, H)
        if sx < 6.4 and sy > 2.4:        # leave headline room
            continue
        ax.add_patch(Circle((sx, sy), rng.uniform(0.005, 0.03),
                     color="#cdd6e0", alpha=rng.uniform(0.25, 0.9), zorder=1))

    # the Sun, glowing on the right edge
    sun = (12.6, 3.15)
    radial_glow(ax, sun[0], sun[1], 4.4, GOLD, ext, peak=0.9, falloff=1.7)
    radial_glow(ax, sun[0], sun[1], 2.0, "#fff3c4", ext, peak=1.0, falloff=2.6)

    # faint orbit arc sweeping past the Earth
    t = np.linspace(np.radians(118), np.radians(242), 200)
    ax.plot(sun[0] + 6.2 * np.cos(t), sun[1] + 3.0 * np.sin(t),
            color=CYAN, lw=1.0, alpha=0.30, zorder=1)

    # the Earth, lit from the Sun (terminator faces left = night side toward us)
    ecx, ecy, er = 8.35, 3.55, 1.5
    light = (sun[0] - ecx, sun[1] - ecy, 0.55)   # +z bias = mostly day toward us
    earth(ax, ecx, ecy, er, light, tilt_deg=23.5)

    # title block, left
    ax.text(0.62, 4.78, "Day, Night", color=FG, fontsize=58,
            fontweight="bold", va="center")
    ax.text(0.62, 3.70, "& Seasons", color=CYAN, fontsize=58,
            fontweight="bold", va="center")
    ax.text(0.66, 2.62, "a 3D simulation to explain the sky to my kids",
            color=MUT, fontsize=20, va="center")

    fig.savefig(f"{OUT}/social.png", facecolor=BG)
    plt.close(fig)
    print("social.png ->", OUT)


if __name__ == "__main__":
    fig_social()
