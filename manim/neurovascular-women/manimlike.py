"""
Shared 3Blue1Brown / manim-style helpers for a static slide deck rendered
to a multi-page vector PDF with matplotlib.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle, PathPatch, Rectangle
from matplotlib.path import Path

# ----------------------------------------------------------------------------
# Manim (ManimCE) colour palette
# ----------------------------------------------------------------------------
BG        = "#0b0d12"   # deep near-black background
WHITE     = "#ECECEC"
GREY      = "#8A8A8A"
GREY_D    = "#4a4d55"
BLUE_B    = "#9CDCEB"
BLUE      = "#58C4DD"
BLUE_D    = "#29ABCA"
BLUE_E    = "#236B8E"
TEAL      = "#5CD0B3"
GREEN     = "#83C167"
YELLOW    = "#F4D35E"
GOLD      = "#F0AC5F"
RED       = "#FC6255"
MAROON    = "#C55F73"
PURPLE    = "#9A72AC"
PINK      = "#D689C4"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "text.color": WHITE,
    "axes.edgecolor": WHITE,
    "savefig.facecolor": BG,
    "figure.facecolor": BG,
    "pdf.fonttype": 42,
})

W, H = 16.0, 9.0  # slide coordinate system (16:9)


def new_slide():
    fig = plt.figure(figsize=(12.8, 7.2))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_facecolor(BG)
    ax.axis("off")
    return fig, ax


def glow_line(ax, xs, ys, color, lw=2.2, glow=True, alpha=1.0, zorder=2, ls="-"):
    """Draw a line with a soft outer glow, 3b1b style."""
    if glow:
        for g, a in [(7.0, 0.05), (4.5, 0.08), (3.0, 0.12)]:
            ax.plot(xs, ys, color=color, lw=lw * g, alpha=a,
                    solid_capstyle="round", zorder=zorder, ls=ls)
    ax.plot(xs, ys, color=color, lw=lw, alpha=alpha,
            solid_capstyle="round", zorder=zorder + 1, ls=ls)


def glow_dot(ax, x, y, color, r=0.09, zorder=5):
    for g, a in [(3.2, 0.10), (2.0, 0.18)]:
        ax.add_patch(Circle((x, y), r * g, color=color, alpha=a, zorder=zorder))
    ax.add_patch(Circle((x, y), r, color=color, zorder=zorder + 1))


def arrow(ax, p0, p1, color=WHITE, lw=2.0, mut=16, alpha=1.0, zorder=4,
          ls="-", connectionstyle=None):
    kw = dict(arrowstyle="-|>", mutation_scale=mut, lw=lw, color=color,
              alpha=alpha, zorder=zorder, capstyle="round", linestyle=ls)
    if connectionstyle:
        kw["connectionstyle"] = connectionstyle
    ax.add_patch(FancyArrowPatch(p0, p1, **kw))


def rbox(ax, cx, cy, w, h, color, lw=2.0, fill=0.06, zorder=3, round_pad=0.12):
    box = matplotlib.patches.FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle=f"round,pad={round_pad},rounding_size=0.18",
        linewidth=lw, edgecolor=color, facecolor=color, alpha=1.0, zorder=zorder)
    # draw fill separately for control
    box.set_facecolor(color)
    box.set_alpha(1.0)
    # use two patches: faint fill + crisp edge
    fillbox = matplotlib.patches.FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle=f"round,pad={round_pad},rounding_size=0.18",
        linewidth=0, facecolor=color, alpha=fill, zorder=zorder)
    edgebox = matplotlib.patches.FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle=f"round,pad={round_pad},rounding_size=0.18",
        linewidth=lw, edgecolor=color, facecolor="none", alpha=0.95, zorder=zorder + 1)
    ax.add_patch(fillbox)
    ax.add_patch(edgebox)


def title(ax, text, sub=None, accent=BLUE, y=8.05):
    ax.text(1.0, y, text, fontsize=30, color=WHITE, weight="bold",
            ha="left", va="center")
    # accent underline
    glow_line(ax, [1.02, 1.02 + min(0.42 * len(text) ** 0.5, 6.5)],
              [y - 0.62, y - 0.62], accent, lw=3.0)
    if sub:
        ax.text(1.02, y - 1.12, sub, fontsize=15, color=GREY, ha="left", va="center",
                style="italic")


def page_tag(ax, n, total, section="NEUROVASCULAR DISEASE IN WOMEN"):
    ax.text(W - 0.5, 0.42, f"{n:02d} / {total:02d}", fontsize=10.5, color=GREY_D,
            ha="right", va="center")
    ax.text(0.5, 0.42, section, fontsize=9.5, color=GREY_D, ha="left", va="center",
            family="serif")
    glow_line(ax, [0.5, W - 0.5], [0.72, 0.72], GREY_D, lw=0.8, glow=False, alpha=0.5)


def bullet(ax, x, y, text, color=BLUE, fs=15.5, dot=True, tcolor=None, dx=0.42):
    if dot:
        glow_dot(ax, x, y, color, r=0.07)
    ax.text(x + dx, y, text, fontsize=fs, color=tcolor or WHITE, ha="left",
            va="center")


# ----------------------------------------------------------------------------
# Reusable neurovascular shapes
# ----------------------------------------------------------------------------
def brain_outline(cx, cy, s):
    """Return (xs, ys) of a stylised side-view brain silhouette."""
    t = np.linspace(0, 2 * np.pi, 400)
    # base ellipse modulated with a few lobes for a cortical look
    r = (1.0
         + 0.13 * np.sin(3 * t + 0.6)
         + 0.06 * np.sin(7 * t)
         + 0.04 * np.sin(11 * t + 1.0))
    x = 1.35 * r * np.cos(t)
    y = 1.0 * r * np.sin(t)
    # flatten the bottom a touch
    y = np.where(y < -0.55, -0.55 + (y + 0.55) * 0.5, y)
    return cx + s * x, cy + s * y


def draw_brain(ax, cx, cy, s, color=BLUE_B, sulci=True, zorder=2, lw=2.0):
    xs, ys = brain_outline(cx, cy, s)
    glow_line(ax, xs, ys, color, lw=lw, zorder=zorder)
    if sulci:
        for k in range(4):
            tt = np.linspace(0.15 + k, 2.4 + k, 60)
            rr = 0.55 - 0.08 * k
            xx = cx + s * (rr * 1.3 * np.cos(tt) + 0.05 * np.sin(4 * tt) - 0.1)
            yy = cy + s * (rr * np.sin(tt) + 0.05 * np.cos(3 * tt) + 0.15)
            ax.plot(xx, yy, color=color, lw=1.0, alpha=0.35, zorder=zorder)


def draw_circle_of_willis(ax, cx, cy, s, color=RED, label=False):
    """Stylised Circle of Willis vascular schematic (vertical oval ring
    + ACA / MCA / PCA / basilar branches)."""
    # ring (vertical oval)
    t = np.linspace(0, 2 * np.pi, 240)
    rx, ry = 0.95, 1.5
    x = cx + s * rx * np.cos(t)
    y = cy + s * ry * np.sin(t)
    glow_line(ax, x, y, color, lw=2.4)

    def seg(p0, p1, **kw):
        glow_line(ax, [cx + s * p0[0], cx + s * p1[0]],
                  [cy + s * p0[1], cy + s * p1[1]], color, lw=2.2, **kw)

    top = (0, ry); bot = (0, -ry)
    # ACA - up from top, splayed
    seg((-0.18, ry - 0.05), (-0.55, ry + 1.05))
    seg((0.18, ry - 0.05), (0.55, ry + 1.05))
    # MCA - lateral from mid-sides
    seg((-rx + 0.05, 0.2), (-rx - 1.25, 0.55))
    seg((rx - 0.05, 0.2), (rx + 1.25, 0.55))
    seg((-rx - 1.25, 0.55), (-rx - 1.7, 1.1))
    seg((rx + 1.25, 0.55), (rx + 1.7, 1.1))
    # PCA - down-lateral from lower sides
    seg((-rx + 0.25, -0.85), (-rx - 0.9, -1.25))
    seg((rx - 0.25, -0.85), (rx + 0.9, -1.25))
    # basilar + vertebrals down from bottom
    seg((0, -ry + 0.05), (0, -ry - 0.7))
    seg((0, -ry - 0.7), (-0.5, -ry - 1.35))
    seg((0, -ry - 0.7), (0.5, -ry - 1.35))
    # junction nodes
    for p in [(-0.18, ry - 0.05), (0.18, ry - 0.05), (-rx + 0.05, 0.2),
              (rx - 0.05, 0.2), (0, -ry + 0.05), (0, -ry - 0.7)]:
        glow_dot(ax, cx + s * p[0], cy + s * p[1], color, r=0.06)
    if label:
        ax.text(cx, cy + s * (ry + 1.5), "Circle of Willis", fontsize=12,
                color=GREY, ha="center")


def lightning(ax, x, y, s, color=YELLOW):
    pts = np.array([(0, 1), (-0.25, 0.15), (0.08, 0.15), (-0.18, -1),
                    (0.32, 0.05), (-0.02, 0.05), (0, 1)])
    xs = x + s * pts[:, 0]
    ys = y + s * pts[:, 1]
    glow_line(ax, xs, ys, color, lw=2.2)
    ax.fill(xs, ys, color=color, alpha=0.18)
