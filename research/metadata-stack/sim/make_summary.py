"""
Five-layer data stack summary card (dark 3blue1brown style).

A single 1200x630 figure used both as the post's lead image and its OpenGraph /
Twitter social card. The five interdependent layers Sanjeev Mohan describes,
stacked bottom-to-top, each with the capability it adds and the failure it
prevents.

Illustrative diagram (the running Customer / MacBook / Order example is
hand-picked for clarity), a visual restatement of the FAQ, not output from any
live system.

Run:
    python research/metadata-stack/sim/make_summary.py
Writes:
    public/img/metadata-stack/five-layers.png   (1200x630)
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, RegularPolygon

# ---- Manim-matched palette -------------------------------------------------
BG     = "#000000"   # pure black, to match the website background
PANEL  = "#151b24"
LIGHT  = "#E8E8E8"
GREY   = "#7A8090"
DIM    = "#3C4250"
BLUE   = "#58C4DD"
TEAL   = "#5CD0B3"
GREEN  = "#83C167"
YELLOW = "#FFD866"
ORANGE = "#FF8E3C"
PURPLE = "#9A72AC"

plt.rcParams.update({
    "figure.facecolor": BG, "savefig.facecolor": BG,
    "text.color": LIGHT, "font.family": "DejaVu Sans", "font.size": 11,
})

OUT = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "public", "img", "metadata-stack"))
os.makedirs(OUT, exist_ok=True)


def box(ax, x, y, w, h, ec, fc=PANEL, lw=1.6, r=0.012, z=2, alpha=1.0):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad=0.004,rounding_size={r}",
        linewidth=lw, edgecolor=ec, facecolor=fc, zorder=z, alpha=alpha))


# ----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 6.3), dpi=100)
fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="square,pad=0",
             linewidth=0, facecolor=BG, zorder=0))

# Title band
ax.text(0.5, 0.945, "Making your data stack AI-ready", ha="center",
        color=LIGHT, fontsize=26, weight="bold")
ax.text(0.5, 0.893, "the five layers: metadata · ontology · knowledge graph · semantic · context",
        ha="center", color=GREY, fontsize=12.5)

# ---- the stack -------------------------------------------------------------
# Five bands, bottom-to-top. Left third = name + one-liner; right glyph column.
layers = [
    ("01", "Metadata",        BLUE,   "data about data",
     "describes each asset: its type, owner, lineage & meaning"),
    ("02", "Ontology",        TEAL,   "the model of meaning",
     "your entities and which relationships between them are valid"),
    ("03", "Knowledge graph", GREEN,  "the model, populated",
     "that model filled with real, interconnected entities"),
    ("04", "Semantic layer",  YELLOW, "one truth per metric",
     "each metric defined once, served identically to every tool"),
    ("05", "Context layer",   ORANGE, "the right info, right now",
     "the needed signals assembled at runtime, for one decision"),
]

x0, x1 = 0.045, 0.60         # stack column (names)
gx0, gx1 = 0.625, 0.965      # glyph column
band_h = 0.118
gap = 0.018
y_bottom = 0.085

ys = []
for i, (num, name, col, tag, desc) in enumerate(layers):
    y = y_bottom + i * (band_h + gap)
    ys.append(y)
    box(ax, x0, y, x1 - x0, band_h, col, fc=PANEL, lw=1.6, r=0.02, z=2)
    # accent edge on the left
    ax.add_patch(FancyBboxPatch((x0, y), 0.012, band_h,
                 boxstyle="round,pad=0,rounding_size=0.004",
                 linewidth=0, facecolor=col, zorder=3))
    ax.text(x0 + 0.03, y + band_h - 0.038, num, color=col, fontsize=13,
            weight="bold", family="monospace", va="center")
    ax.text(x0 + 0.075, y + band_h - 0.038, name, color=LIGHT, fontsize=16.5,
            weight="bold", va="center")
    ax.text(x0 + 0.075, y + band_h - 0.038, "",)
    ax.text(x0 + 0.30, y + band_h - 0.038, "— " + tag, color=col, fontsize=11.5,
            style="italic", va="center")
    ax.text(x0 + 0.03, y + 0.032, desc, color=GREY, fontsize=10.2, va="center")

# "builds on" arrow up the left margin
ax.annotate("", xy=(0.028, ys[-1] + band_h - 0.02), xytext=(0.028, ys[0] + 0.02),
            arrowprops=dict(arrowstyle="-|>", color=DIM, lw=2.0))
ax.text(0.020, (ys[0] + ys[-1] + band_h) / 2, "each layer builds on the one below",
        rotation=90, ha="center", va="center", color=GREY, fontsize=9.5,
        style="italic")

# ---- glyph column: one tiny picture per layer ------------------------------
gcx = (gx0 + gx1) / 2
gw = gx1 - gx0
box(ax, gx0 - 0.005, y_bottom - 0.005, gw + 0.01,
    5 * (band_h + gap) - gap + 0.01, DIM, fc="#10141b", lw=1.2, r=0.02, z=1)


def gy(i):
    return ys[i] + band_h / 2


# 01 metadata — a raw cell wrapped by descriptor tags
y = gy(0)
box(ax, gcx - 0.035, y - 0.022, 0.07, 0.044, BLUE, fc="#10161e", z=4)
ax.text(gcx, y, "cust_st", ha="center", va="center", color=GREY,
        fontsize=7.6, family="monospace", zorder=5)
for dx, lbl in [(-0.13, "type"), (-0.13, ""), (0.13, "owner")]:
    pass
for dx, dy, lbl, col in [(-0.135, 0.018, "type", GREY), (-0.135, -0.018, "owner", GREY),
                         (0.135, 0.018, "lineage", GREY), (0.135, -0.018, "= US state", BLUE)]:
    ax.text(gcx + dx, y + dy, lbl, ha="center", va="center", color=col, fontsize=7.0)
    ax.plot([gcx + (0.04 if dx > 0 else -0.04), gcx + dx * 0.62],
            [y, y + dy], color=DIM, lw=0.8, zorder=3)

# 02 ontology — class schema with a typed edge
y = gy(1)
for dx, lbl, col in [(-0.10, "Customer", TEAL), (0.10, "Order", TEAL)]:
    box(ax, gcx + dx - 0.05, y - 0.018, 0.10, 0.036, col, fc="#10211c", z=4)
    ax.text(gcx + dx, y, lbl, ha="center", va="center", color=col, fontsize=7.8,
            weight="bold", zorder=5)
ax.annotate("", xy=(gcx + 0.05, y), xytext=(gcx - 0.05, y),
            arrowprops=dict(arrowstyle="-|>", color=YELLOW, lw=1.4))
ax.text(gcx, y + 0.026, "places", ha="center", color=YELLOW, fontsize=7.0,
        style="italic")

# 03 knowledge graph — instances connected, one multi-hop path
y = gy(2)
rng = np.random.default_rng(3)
pts = np.array([[gcx - 0.12, y + 0.02], [gcx - 0.04, y - 0.025],
                [gcx + 0.04, y + 0.028], [gcx + 0.12, y - 0.01],
                [gcx + 0.0, y + 0.005]])
path = [0, 1, 4, 3]
for a in range(len(path) - 1):
    ax.plot([pts[path[a], 0], pts[path[a + 1], 0]],
            [pts[path[a], 1], pts[path[a + 1], 1]], color=GREEN, lw=2.0, zorder=3)
cols = [BLUE, GREEN, ORANGE, PURPLE, YELLOW]
ax.scatter(pts[:, 0], pts[:, 1], s=70, color=cols, zorder=4,
           edgecolors=BG, linewidths=0.8)
ax.text(gcx, y - 0.05, "multi-hop, real entities", ha="center", color=GREEN,
        fontsize=7.4, style="italic")

# 04 semantic layer — one hub feeding three consumers
y = gy(3)
ax.add_patch(Circle((gcx, y), 0.026, edgecolor=YELLOW, facecolor="#1a180e",
             lw=1.6, zorder=4))
ax.text(gcx, y, "=", ha="center", va="center", color=YELLOW, fontsize=11,
        weight="bold", zorder=5)
for dx, lbl in [(-0.13, "BI"), (0.0, "SQL"), (0.13, "agent")]:
    ax.scatter([gcx + dx], [y - 0.04], s=42, color=DIM, edgecolors=YELLOW,
               linewidths=1.0, zorder=4)
    ax.plot([gcx, gcx + dx], [y, y - 0.04], color=YELLOW, lw=1.0, alpha=0.7, zorder=3)
ax.text(gcx, y + 0.045, "one definition", ha="center", color=YELLOW, fontsize=7.4,
        style="italic")

# 05 context layer — many sources converge on the moment
y = gy(4)
ax.add_patch(RegularPolygon((gcx, y), numVertices=6, radius=0.026,
             orientation=0, edgecolor=ORANGE, facecolor="#1d150c", lw=1.6, zorder=5))
ax.text(gcx, y, "now", ha="center", va="center", color=ORANGE, fontsize=7.4,
        weight="bold", zorder=6)
srcs = [(-0.15, 0.02, BLUE), (-0.15, -0.02, GREEN), (0.15, 0.02, YELLOW),
        (0.15, -0.02, PURPLE), (0.0, 0.045, TEAL), (0.0, -0.045, GREY)]
for dx, dy, col in srcs:
    ax.scatter([gcx + dx], [y + dy], s=34, color=col, zorder=4,
               edgecolors=BG, linewidths=0.6)
    ax.annotate("", xy=(gcx + np.sign(dx) * 0.03 if dx else gcx,
                        y + np.sign(dy) * 0.02 if dy else y),
                xytext=(gcx + dx, y + dy),
                arrowprops=dict(arrowstyle="-|>", color=col, lw=1.0, alpha=0.7))

path_out = os.path.join(OUT, "five-layers.png")
fig.savefig(path_out, dpi=100, facecolor=BG)
print("wrote", path_out)
