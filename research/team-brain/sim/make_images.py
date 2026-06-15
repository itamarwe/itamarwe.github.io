"""
Team-brain post imagery (dark 3blue1brown style).

Two coherent figures for the post
[*Building a Team Brain That Updates Itself*](../../content/posts/2026-06-09-building-a-self-updating-team-brain.md):

    header.png   1200x560   in-page lead banner (diagram-focused, no title text)
    social.png   1200x630   OpenGraph / Twitter card (title baked in)

Both render the same motif — a central "team brain" (a small cross-linked wiki
graph living in a Git repo) that every builder keeps current via a pull/push
cron loop, with autonomous agents reading from it.

Illustrative diagram (node labels and counts are hand-picked for clarity), not a
capture of a live system.

Run:
    python research/team-brain/sim/make_images.py
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

# ---- palette (matches the house dark style) --------------------------------
BG     = "#0E1116"
LIGHT  = "#EDEDED"
GREY   = "#8b95a5"
DIM    = "#39414f"
CYAN   = "#3fc1ff"
GREEN  = "#7CFC8A"
GOLD   = "#ffd166"
RED    = "#ff5a5a"
PURPLE = "#b48cff"

plt.rcParams.update({
    "figure.facecolor": BG, "savefig.facecolor": BG,
    "text.color": LIGHT, "font.family": "DejaVu Sans",
})

OUT = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "public", "img", "team-brain"))
os.makedirs(OUT, exist_ok=True)


def new_fig(w_px, h_px):
    asp = w_px / h_px
    fig, ax = plt.subplots(figsize=(w_px / 100, h_px / 100), dpi=100)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set_xlim(0, asp)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0, 0), asp, 1, boxstyle="square,pad=0",
                 linewidth=0, facecolor=BG, zorder=0))
    return fig, ax, asp


def curved(ax, p0, p1, color, rad, lw=1.6, ms=11, z=4, alpha=1.0, ls="-"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms,
                 color=color, lw=lw, zorder=z, alpha=alpha, linestyle=ls,
                 connectionstyle=f"arc3,rad={rad}", shrinkA=6, shrinkB=8))


# Concept / entity / decision / meeting palette for the wiki nodes.
NODE_KINDS = [CYAN, GREEN, GOLD, PURPLE, GREEN, CYAN, GOLD, RED]


def brain_cluster(ax, cx, cy, scale=1.0, seed=3, alpha=1.0, label=True):
    """A small cross-linked wiki graph — the 'brain'."""
    rng = np.random.default_rng(seed)
    n = 9
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False) + rng.uniform(0, 1, n) * 0.4
    rad = (0.05 + rng.uniform(0, 0.05, n)) * scale
    pts = np.column_stack([cx + rad * np.cos(ang), cy + rad * np.sin(ang)])
    pts[0] = [cx, cy]
    # edges: connect each node to 1-2 near neighbours + hub
    order = np.argsort(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy))
    for i in range(1, n):
        a = order[i]
        b = order[rng.integers(0, i)]
        ax.plot([pts[a, 0], pts[b, 0]], [pts[a, 1], pts[b, 1]],
                color=DIM, lw=1.0 * scale, alpha=0.8 * alpha, zorder=3)
    sizes = (rng.uniform(40, 120, n)) * scale ** 2
    sizes[0] *= 1.6
    cols = [NODE_KINDS[i % len(NODE_KINDS)] for i in range(n)]
    ax.scatter(pts[:, 0], pts[:, 1], s=sizes, c=cols, zorder=4,
               edgecolors=BG, linewidths=1.0 * scale, alpha=alpha)
    if label:
        ax.add_patch(Circle((cx, cy), 0.135 * scale, edgecolor=DIM,
                     facecolor="none", lw=1.3, linestyle=(0, (5, 5)),
                     zorder=2, alpha=alpha))
    return pts


# ============================================================================
#  HEADER — the self-updating loop
# ============================================================================
def make_header():
    W, H = 1200, 560
    fig, ax, asp = new_fig(W, H)          # asp ≈ 2.143
    cx, cy = 1.07, 0.50                   # brain center
    L_EDGE, R_EDGE = cx - 0.17, cx + 0.17

    # ---- central brain ----
    brain_cluster(ax, cx, cy, scale=1.25, seed=7)
    ax.text(cx, cy - 0.245, "the team brain", ha="center", color=LIGHT,
            fontsize=13, weight="bold")
    ax.text(cx, cy - 0.295, "a living wiki in a Git repo", ha="center",
            color=GREY, fontsize=9.5, style="italic")

    # ---- left: builders sync with the brain (push in / pull out) ----
    bx = 0.46
    builders = [("Note Taker", 0.82), ("Slack", 0.61), ("WhatsApp", 0.39),
                ("Docs", 0.18)]
    ax.text(bx, 0.95, "every builder is a node", ha="center", color=CYAN,
            fontsize=10, weight="bold")
    for src, by in builders:
        ax.scatter([bx], [by], s=300, color="#10161e", edgecolors=CYAN,
                   linewidths=1.8, zorder=5)
        ax.scatter([bx], [by], s=60, color=CYAN, zorder=6, alpha=0.9)
        ax.text(bx - 0.075, by, src, ha="right", va="center", color=GREY,
                fontsize=8.6, zorder=6)
        # push (gold, in) and pull (cyan, out), curved opposite ways
        curved(ax, (bx + 0.02, by), (L_EDGE, cy), GOLD, rad=0.16, lw=1.6, ms=10)
        curved(ax, (L_EDGE, cy), (bx + 0.02, by), CYAN, rad=0.16, lw=1.4, ms=9)
    ax.text(0.46, 0.045, "a cron job every 30 min  ·  pull + push", ha="center",
            color=GREY, fontsize=8.8, style="italic")
    ax.text(L_EDGE - 0.10, cy + 0.075, "push", ha="center", color=GOLD,
            fontsize=8.8, weight="bold")
    ax.text(L_EDGE - 0.10, cy - 0.075, "pull", ha="center", color=CYAN,
            fontsize=8.8, weight="bold")

    # ---- right: autonomous agents read from the brain ----
    axx = asp - 0.42
    for src, ay in (("design", 0.78), ("go-to-market", 0.50), ("Siena · WhatsApp", 0.22)):
        ax.scatter([axx], [ay], s=240, color="#15101e", edgecolors=PURPLE,
                   linewidths=1.7, zorder=5)
        ax.scatter([axx], [ay], s=55, color=PURPLE, zorder=6)
        ax.text(axx + 0.06, ay, src, ha="left", va="center", color=GREY,
                fontsize=8.6, zorder=6)
        curved(ax, (R_EDGE, cy), (axx - 0.03, ay), PURPLE, rad=-0.16, lw=1.4,
               ms=9, z=3, alpha=0.85)
    ax.text(axx, 0.95, "agents on top", ha="center", color=PURPLE,
            fontsize=10, weight="bold")

    fig.savefig(os.path.join(OUT, "header.png"), dpi=100, facecolor=BG)
    plt.close(fig)


# ============================================================================
#  SOCIAL — title card
# ============================================================================
def make_social():
    W, H = 1200, 630
    fig, ax, asp = new_fig(W, H)

    # faint full-bleed knowledge graph backdrop
    rng = np.random.default_rng(21)
    N = 60
    P = np.column_stack([rng.uniform(0, asp, N), rng.uniform(0, 1, N)])
    for i in range(N):
        for j in range(i + 1, N):
            if np.hypot(*(P[i] - P[j])) < 0.26:
                ax.plot([P[i, 0], P[j, 0]], [P[i, 1], P[j, 1]],
                        color=DIM, lw=0.6, alpha=0.5, zorder=1)
    cols = [NODE_KINDS[i % len(NODE_KINDS)] for i in range(N)]
    ax.scatter(P[:, 0], P[:, 1], s=rng.uniform(8, 70, N), c=cols,
               alpha=0.45, zorder=2, edgecolors=BG, linewidths=0.5)

    # the self-updating loop motif, glowing, upper-right
    lx, ly = asp - 0.62, 0.66
    brain_cluster(ax, lx, ly, scale=1.0, seed=7, label=True)
    R = 0.28
    for deg in np.linspace(90, 450, 5, endpoint=False):
        a = np.deg2rad(deg)
        bx, by = lx + R * np.cos(a), ly + R * np.sin(a)
        ax.scatter([bx], [by], s=120, color="#10161e", edgecolors=CYAN,
                   linewidths=1.4, zorder=5)
        ax.scatter([bx], [by], s=30, color=CYAN, zorder=6)
        edge_in = (lx + 0.12 * np.cos(a), ly + 0.12 * np.sin(a))
        curved(ax, (bx, by), edge_in, GOLD, rad=0.28, lw=1.3, ms=8)
        curved(ax, edge_in, (bx, by), CYAN, rad=0.28, lw=1.2, ms=7)

    # left-side scrim so the title stays legible
    ax.add_patch(FancyBboxPatch((-0.05, -0.05), 1.15, 1.1,
                 boxstyle="square,pad=0", linewidth=0, facecolor=BG,
                 alpha=0.55, zorder=7))

    # title block
    ax.text(0.075, 0.80, "THE TEAM BRAIN", color=CYAN, fontsize=20,
            weight="bold", zorder=8, family="DejaVu Sans")
    # letter-spacing emulation
    ax.text(0.075, 0.555, "Building a Team Brain", color=LIGHT, fontsize=46,
            weight="bold", zorder=8, va="center")
    ax.text(0.075, 0.45, "That Updates Itself", color=LIGHT, fontsize=46,
            weight="bold", zorder=8, va="center")
    ax.text(0.078, 0.315, "A living wiki that every meeting rewrites",
            color=GREEN, fontsize=20, weight="bold", zorder=8, va="center")

    fig.savefig(os.path.join(OUT, "social.png"), dpi=100, facecolor=BG)
    plt.close(fig)


if __name__ == "__main__":
    make_header()
    make_social()
    for n in ("header", "social"):
        print("wrote", os.path.join(OUT, n + ".png"))
