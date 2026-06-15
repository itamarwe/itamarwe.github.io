"""
Eon four-layer summary card (dark 3blue1brown style).

A single 1200x630 figure used both as the post's lead image and its OpenGraph /
Twitter social card. Four panels — joinability detection, semantic analysis,
RAG over tables, NL->SQL — matching the palette of the embedded Manim video.

Illustrative diagram (the table names and the 0.94 score are hand-picked for
clarity), not output from a live Eon system.

Run:
    python research/eon-layers/sim/make_summary.py
Writes:
    public/img/eon-layers/four-layers.png   (1200x630)
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, RegularPolygon, Circle

# ---- Manim-matched palette -------------------------------------------------
BG     = "#0E1116"
PANEL  = "#151b24"
LIGHT  = "#E8E8E8"
GREY   = "#7A8090"
DIM    = "#3C4250"
BLUE   = "#58C4DD"
TEAL   = "#5CD0B3"
YELLOW = "#FFD866"
GREEN  = "#83C167"
ORANGE = "#FF8E3C"
PURPLE = "#9A72AC"

plt.rcParams.update({
    "figure.facecolor": BG, "savefig.facecolor": BG,
    "text.color": LIGHT, "font.family": "DejaVu Sans", "font.size": 11,
})

OUT = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "public", "img", "eon-layers"))
os.makedirs(OUT, exist_ok=True)


def box(ax, x, y, w, h, ec, fc=PANEL, lw=1.6, r=0.012, z=2):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad=0.004,rounding_size={r}",
        linewidth=lw, edgecolor=ec, facecolor=fc, zorder=z))


def table(ax, x, y, w, h, ec, title, rows, hi=None):
    """A tiny table glyph: header band + a few column-name rows."""
    box(ax, x, y, w, h, ec, fc="#10161e", z=3)
    ax.add_patch(FancyBboxPatch((x, y + h - 0.034), w, 0.034,
                 boxstyle="round,pad=0.001,rounding_size=0.004",
                 linewidth=0, facecolor=ec, alpha=0.20, zorder=4))
    ax.text(x + w / 2, y + h - 0.017, title, ha="center", va="center",
            color=ec, fontsize=8.5, weight="bold", zorder=5)
    n = len(rows)
    gap = (h - 0.05) / n
    for i, r in enumerate(rows):
        ry = y + h - 0.05 - gap * (i + 0.5)
        c = YELLOW if hi == i else GREY
        wt = "bold" if hi == i else "normal"
        ax.text(x + 0.012, ry, r, ha="left", va="center",
                color=c, fontsize=7.6, family="monospace", weight=wt, zorder=5)


def arrow(ax, x1, y1, x2, y2, color, lw=1.7, ms=12, style="-|>", z=4, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                 mutation_scale=ms, color=color, lw=lw, zorder=z,
                 linestyle=ls, shrinkA=0, shrinkB=0))


def header(ax, cx, top, num, title, color):
    ax.text(cx, top, num, ha="center", va="center", color=color,
            fontsize=15, weight="bold", family="monospace")
    ax.text(cx, top - 0.052, title, ha="center", va="center",
            color=LIGHT, fontsize=12.5, weight="bold")


def caption(ax, cx, y, text, color):
    ax.text(cx, y, text, ha="center", va="center", color=color,
            fontsize=8.6, style="italic")


# ----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 6.3), dpi=100)
fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="square,pad=0",
             linewidth=0, facecolor=BG, zorder=0))

# Title band
ax.text(0.5, 0.945, "Making backups AI-queryable", ha="center",
        color=LIGHT, fontsize=26, weight="bold")
ax.text(0.5, 0.892, "the four layers Eon builds on its backup-derived data lake",
        ha="center", color=GREY, fontsize=12.5)

# Four panels
PX = [0.035, 0.285, 0.535, 0.785]
PW = 0.18
PANEL_Y, PANEL_H = 0.085, 0.70
CX = [x + PW / 2 for x in PX]
COLORS = [BLUE, TEAL, YELLOW, GREEN]

for x, c in zip(PX, COLORS):
    box(ax, x, PANEL_Y, PW, PANEL_H, DIM, fc=PANEL, lw=1.3, r=0.02, z=1)
    # thin accent bar at the panel top
    ax.add_patch(FancyBboxPatch((x, PANEL_Y + PANEL_H - 0.012), PW, 0.012,
                 boxstyle="round,pad=0,rounding_size=0.004",
                 linewidth=0, facecolor=c, zorder=2))

HEAD_Y = PANEL_Y + PANEL_H - 0.07

# soft connecting arrows between panels (the layers compose)
for i in range(3):
    arrow(ax, PX[i] + PW + 0.004, PANEL_Y + PANEL_H / 2,
          PX[i + 1] - 0.004, PANEL_Y + PANEL_H / 2,
          DIM, lw=1.4, ms=11)

# ---- Panel 1: Joinability detection ---------------------------------------
c0 = CX[0]
header(ax, c0, HEAD_Y, "01", "Joinability", BLUE)
ax.text(c0, HEAD_Y - 0.092, "what actually joins what", ha="center",
        color=GREY, fontsize=8.6)
tw, th = 0.064, 0.155
ty = 0.40
xl = PX[0] + 0.012
xr = PX[0] + PW - tw - 0.012
table(ax, xl, ty, tw, th, BLUE, "users", ["id", "email", "plan"], hi=0)
table(ax, xr, ty, tw, th, PURPLE, "events", ["uid", "ts", "kind"], hi=0)
# the two highlighted id/uid rows drop down to a shared "match" node below
lyr = ty + th - 0.05 - (th - 0.05) / 3 * 0.5   # y of the (id / uid) rows
node_y = 0.275
arrow(ax, xl + tw, lyr, c0 - 0.012, node_y + 0.012, YELLOW, lw=1.6, ms=10)
arrow(ax, xr, lyr, c0 + 0.012, node_y + 0.012, YELLOW, lw=1.6, ms=10)
box(ax, c0 - 0.075, node_y - 0.052, 0.15, 0.062, YELLOW, fc="#1c1a10", z=4)
ax.text(c0, node_y - 0.0, "id  ⟷  uid", ha="center", va="center",
        color=LIGHT, fontsize=8.4, family="monospace", weight="bold", zorder=5)
ax.text(c0, node_y - 0.032, "min-hash  ≈ 0.94", ha="center", va="center",
        color=YELLOW, fontsize=8.0, zorder=5)
ax.text(c0, node_y - 0.10, "physical overlap", ha="center", color=BLUE, fontsize=8.4)
caption(ax, c0, node_y - 0.138, "real, not a guess", GREY)

# ---- Panel 2: Semantic analysis -------------------------------------------
c1 = CX[1]
header(ax, c1, HEAD_Y, "02", "Semantic", TEAL)
ax.text(c1, HEAD_Y - 0.092, "describe every table", ha="center",
        color=GREY, fontsize=8.6)
table(ax, c1 - 0.036, 0.46, 0.072, 0.12, TEAL, "orders", ["uid", "amount"])
hexy = 0.345
ax.add_patch(RegularPolygon((c1, hexy), numVertices=6, radius=0.052,
             orientation=0, edgecolor=TEAL, facecolor="#10211c",
             linewidth=1.8, zorder=4))
ax.text(c1, hexy, "LLM", ha="center", va="center", color=TEAL,
        fontsize=10, weight="bold", zorder=5)
arrow(ax, c1, 0.46, c1, hexy + 0.058, TEAL, lw=1.6, ms=11)
arrow(ax, c1, hexy - 0.058, c1, 0.205, TEAL, lw=1.6, ms=11)
box(ax, c1 - 0.072, 0.13, 0.144, 0.07, TEAL, fc="#10211c", z=3)
ax.text(c1, 0.182, "uid → users.id", ha="center", va="center",
        color=YELLOW, fontsize=8.0, family="monospace", weight="bold", zorder=5)
ax.text(c1, 0.155, "FK · 94% overlap", ha="center", va="center",
        color=GREY, fontsize=7.4, zorder=5)
caption(ax, c1, 0.105, "fed the layer-1 evidence", GREY)

# ---- Panel 3: RAG over tables ---------------------------------------------
c2 = CX[2]
header(ax, c2, HEAD_Y, "03", "RAG over tables", YELLOW)
ax.text(c2, HEAD_Y - 0.092, "an index of tables", ha="center",
        color=GREY, fontsize=8.6)
ring_y = 0.295
ax.add_patch(Circle((c2, ring_y), 0.115, edgecolor=DIM, facecolor="none",
             linewidth=1.3, linestyle=(0, (4, 4)), zorder=2))
ax.text(c2, ring_y + 0.138, "table index", ha="center", color=GREY, fontsize=7.8)
# four clusters of dots
clusters = [
    (c2 - 0.05, ring_y + 0.045, BLUE),
    (c2 + 0.055, ring_y + 0.04, PURPLE),
    (c2 - 0.045, ring_y - 0.05, GREEN),
    (c2 + 0.05, ring_y - 0.055, ORANGE),
]
import numpy as np
rng = np.random.default_rng(7)
for (ccx, ccy, col) in clusters:
    pts = np.array([[ccx, ccy]]) + rng.normal(0, 0.016, (3, 2))
    for j in range(len(pts) - 1):
        ax.plot([pts[j, 0], pts[j + 1, 0]], [pts[j, 1], pts[j + 1, 1]],
                color=DIM, lw=1.0, zorder=3)
    ax.scatter(pts[:, 0], pts[:, 1], s=34, color=col, zorder=4,
               edgecolors=BG, linewidths=0.6)
# incoming query arrow curving toward the green (orders) cluster
arrow(ax, PX[2] + 0.012, ring_y + 0.0, clusters[2][0] - 0.022, clusters[2][1],
      YELLOW, lw=1.6, ms=11)
caption(ax, c2, ring_y - 0.165, "by meaning + joinability", GREY)

# ---- Panel 4: NL -> SQL ----------------------------------------------------
c3 = CX[3]
header(ax, c3, HEAD_Y, "04", "NL → SQL", GREEN)
ax.text(c3, HEAD_Y - 0.092, "scales to 1M tables", ha="center",
        color=GREY, fontsize=8.6)
box(ax, c3 - 0.078, 0.475, 0.156, 0.062, GREEN, fc="#10211a", z=3)
ax.text(c3, 0.506, "“revenue per user?”", ha="center", va="center",
        color=LIGHT, fontsize=8.6, style="italic", zorder=5)
arrow(ax, c3, 0.475, c3, 0.405, GREEN, lw=1.6, ms=11)
box(ax, c3 - 0.082, 0.205, 0.164, 0.195, GREEN, fc="#0c130f", z=3)
sql = [("SELECT", BLUE), ("  u.id, SUM(o.amount)", GREY),
       ("FROM users u", GREY), ("JOIN orders o", GREY),
       ("  ON o.uid = u.id", YELLOW), ("GROUP BY u.id", GREY)]
for i, (line, col) in enumerate(sql):
    ax.text(c3 - 0.072, 0.372 - i * 0.029, line, ha="left", va="center",
            color=col, fontsize=7.4, family="monospace",
            weight="bold" if col == YELLOW else "normal", zorder=5)
ax.text(c3, 0.16, "join on real overlap ✓", ha="center", color=GREEN, fontsize=8.2)
caption(ax, c3, 0.115, "+ interactive confirm", GREY)

path = os.path.join(OUT, "four-layers.png")
fig.savefig(path, dpi=100, facecolor=BG)
print("wrote", path)
