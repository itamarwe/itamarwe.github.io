"""
Eon per-section figures (dark 3blue1brown style).

One focused landscape figure for each of the four layers, placed above its
section in the post. Same Manim-matched palette as `make_summary.py` and the
embedded video.

Illustrative diagrams (table names, the 0.94 / 0.12 scores, min-hash sketches
and cluster layouts are hand-picked for clarity), not output from a live Eon
system.

Run:
    python research/eon-layers/sim/make_sections.py
Writes (1100x560 each) to public/img/eon-layers/:
    joinability.png  semantic.png  rag.png  nl2sql.png
"""
import os
import numpy as np
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
RED    = "#FC6255"

plt.rcParams.update({
    "figure.facecolor": BG, "savefig.facecolor": BG,
    "text.color": LIGHT, "font.family": "DejaVu Sans", "font.size": 11,
})

OUT = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "public", "img", "eon-layers"))
os.makedirs(OUT, exist_ok=True)


# ---- shared helpers --------------------------------------------------------
def new_fig():
    fig, ax = plt.subplots(figsize=(11, 5.6), dpi=100)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="square,pad=0",
                 linewidth=0, facecolor=BG, zorder=0))
    return fig, ax


def title(ax, num, name, color, subtitle):
    ax.text(0.045, 0.91, num, color=color, fontsize=18, weight="bold",
            family="monospace", va="center")
    ax.text(0.092, 0.91, name, color=LIGHT, fontsize=20, weight="bold", va="center")
    ax.text(0.045, 0.83, subtitle, color=GREY, fontsize=12.5, va="center")


def box(ax, x, y, w, h, ec, fc=PANEL, lw=1.6, r=0.012, z=2, alpha=1.0):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad=0.004,rounding_size={r}",
        linewidth=lw, edgecolor=ec, facecolor=fc, zorder=z, alpha=alpha))


def table(ax, x, y, w, h, ec, ttl, rows, hi=None, fs=8.6):
    box(ax, x, y, w, h, ec, fc="#10161e", z=3)
    ax.add_patch(FancyBboxPatch((x, y + h - 0.05), w, 0.05,
                 boxstyle="round,pad=0.001,rounding_size=0.006",
                 linewidth=0, facecolor=ec, alpha=0.20, zorder=4))
    ax.text(x + w / 2, y + h - 0.025, ttl, ha="center", va="center",
            color=ec, fontsize=fs + 0.6, weight="bold", zorder=5)
    n = len(rows)
    gap = (h - 0.07) / n
    ys = []
    for i, r in enumerate(rows):
        ry = y + h - 0.07 - gap * (i + 0.5)
        ys.append(ry)
        c = YELLOW if hi == i else GREY
        wt = "bold" if hi == i else "normal"
        ax.text(x + 0.015, ry, r, ha="left", va="center", color=c,
                fontsize=fs, family="monospace", weight=wt, zorder=5)
    return ys


def arrow(ax, x1, y1, x2, y2, color, lw=1.7, ms=13, style="-|>", z=4, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                 mutation_scale=ms, color=color, lw=lw, zorder=z,
                 linestyle=ls, shrinkA=0, shrinkB=0,
                 connectionstyle="arc3,rad=0"))


def curve(ax, x1, y1, x2, y2, color, rad=0.3, lw=1.7, ms=13, z=4):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                 mutation_scale=ms, color=color, lw=lw, zorder=z,
                 connectionstyle=f"arc3,rad={rad}"))


def sketch(ax, cx, cy, w, ec, vals, label):
    """A min-hash sketch glyph: a row of small hash values in a rounded box."""
    h = 0.075
    box(ax, cx - w / 2, cy - h / 2, w, h, ec, fc="#0c1118", lw=1.3, z=3)
    ax.text(cx, cy + h / 2 + 0.03, label, ha="center", color=ec, fontsize=8.4)
    s = "  ".join(vals)
    ax.text(cx, cy, s, ha="center", va="center", color=GREY,
            fontsize=8.0, family="monospace", zorder=5)


# ============================================================================
# 01 — Joinability detection
# ============================================================================
def fig_joinability():
    fig, ax = new_fig()
    title(ax, "01", "Joinability detection", BLUE,
          "which columns actually join — physical overlap, not look-alike names")

    # two tables, top-left
    tw, th = 0.13, 0.30
    tx = 0.06
    yU = table(ax, tx, 0.40, tw, th, BLUE, "users", ["id", "email", "plan"], hi=0)
    yE = table(ax, tx + 0.17, 0.40, tw, th, PURPLE, "events", ["uid", "ts", "kind"], hi=0)

    # min-hash sketches under each highlighted column
    lcx, rcx = tx + tw / 2, tx + 0.17 + tw / 2
    sketch(ax, lcx, 0.27, 0.15, BLUE, ["a1", "9c", "27", "e0"], "MinHash(users.id)")
    sketch(ax, rcx, 0.27, 0.15, PURPLE, ["a1", "9c", "27", "b4"], "MinHash(events.uid)")
    arrow(ax, lcx, yU[0] - 0.012, lcx, 0.31, BLUE, lw=1.4, ms=10)
    arrow(ax, rcx, yE[0] - 0.012, rcx, 0.31, PURPLE, lw=1.4, ms=10)
    # both sketches feed a single Jaccard readout below
    mid = (lcx + rcx) / 2
    arrow(ax, lcx, 0.233, mid - 0.02, 0.20, YELLOW, lw=1.4, ms=9)
    arrow(ax, rcx, 0.233, mid + 0.02, 0.20, YELLOW, lw=1.4, ms=9)
    box(ax, mid - 0.16, 0.115, 0.32, 0.075, YELLOW, fc="#1a180e", z=4)
    ax.text(mid, 0.166, "users.id  ⟷  events.uid", ha="center", va="center",
            color=LIGHT, fontsize=9.2, family="monospace", zorder=5)
    ax.text(mid, 0.135, "Jaccard ≈ 0.94  —  no scan of 2B rows", ha="center",
            va="center", color=YELLOW, fontsize=8.6, weight="bold", zorder=5)

    # right side: the two verdicts
    rx = 0.55
    arrow(ax, 0.40, 0.40, rx - 0.01, 0.40, DIM, lw=1.5, ms=12)
    box(ax, rx, 0.58, 0.40, 0.16, RED, fc="#1d1113", z=3)
    ax.text(rx + 0.018, 0.685, "✗  name match only", color=RED, fontsize=11,
            weight="bold", va="center")
    ax.text(rx + 0.018, 0.625, "look-alike UUIDs → hallucinated joins",
            color=GREY, fontsize=9.5, va="center")
    box(ax, rx, 0.34, 0.40, 0.20, GREEN, fc="#0f1a11", z=3)
    ax.text(rx + 0.018, 0.485, "✓  physical overlap + semantic check",
            color=GREEN, fontsize=11, weight="bold", va="center")
    ax.text(rx + 0.018, 0.425, "min-hash proves the values overlap;",
            color=GREY, fontsize=9.5, va="center")
    ax.text(rx + 0.018, 0.385, "the LLM confirms they mean the same thing",
            color=GREY, fontsize=9.5, va="center")

    # output edge of the joinability graph
    ox = rx + 0.085
    ey = 0.18
    ax.scatter([ox, ox + 0.23], [ey, ey], s=120, color=[BLUE, PURPLE],
               zorder=5, edgecolors=BG, linewidths=1.0)
    ax.plot([ox, ox + 0.23], [ey, ey], color=YELLOW, lw=2.2, zorder=4)
    ax.text(ox + 0.115, ey + 0.035, "0.94", ha="center", color=YELLOW,
            fontsize=9, weight="bold")
    ax.text(ox, ey - 0.05, "users.id", ha="center", color=GREY, fontsize=8.4,
            family="monospace")
    ax.text(ox + 0.23, ey - 0.05, "events.uid", ha="center", color=GREY,
            fontsize=8.4, family="monospace")
    ax.text(rx + 0.20, 0.10, "→ an edge in the joinability graph", ha="center",
            color=BLUE, fontsize=9.5, style="italic")

    fig.savefig(os.path.join(OUT, "joinability.png"), dpi=100, facecolor=BG)
    plt.close(fig)


# ============================================================================
# 02 — Semantic analysis
# ============================================================================
def fig_semantic():
    fig, ax = new_fig()
    title(ax, "02", "Semantic analysis", TEAL,
          "an LLM describes every table — fed the physical evidence, not just names")

    # five inputs on the left
    inx, inw, inh = 0.05, 0.235, 0.085
    inputs = [
        ("column names", "id, uid, amount, ts", GREY, 0.66),
        ("sampled rows", "bounded sample (not random)", GREY, 0.555),
        ("source DB · env", "postgres · production", GREY, 0.45),
        ("foreign keys", "orders.uid → users.id", BLUE, 0.345),
        ("joinability hints", "uid ⟷ users.id  ≈ 0.94", YELLOW, 0.24),
    ]
    hxc = (0.555, 0.45)
    for lbl, val, col, y in inputs:
        box(ax, inx, y, inw, inh, col if col != GREY else DIM, fc="#10161e", z=3)
        ax.text(inx + 0.014, y + inh - 0.026, lbl, color=col, fontsize=9.4,
                weight="bold", va="center")
        ax.text(inx + 0.014, y + 0.026, val, color=GREY, fontsize=8.6,
                family="monospace", va="center")
        arrow(ax, inx + inw, y + inh / 2, hxc[0] - 0.066, hxc[1],
              col if col in (BLUE, YELLOW) else DIM,
              lw=1.5 if col in (BLUE, YELLOW) else 1.2, ms=10)
    ax.text(inx, 0.775, "what the LLM is given", ha="left",
            color=GREY, fontsize=9.5, style="italic")

    # LLM hexagon
    ax.add_patch(RegularPolygon(hxc, numVertices=6, radius=0.085,
                 orientation=0, edgecolor=TEAL, facecolor="#10211c",
                 linewidth=2.2, zorder=5))
    ax.text(hxc[0], hxc[1], "LLM", ha="center", va="center", color=TEAL,
            fontsize=15, weight="bold", zorder=6)

    # output description card
    ox, ow = 0.66, 0.30
    box(ax, ox, 0.26, ow, 0.40, TEAL, fc="#0e1a17", z=3)
    ax.text(ox + ow / 2, 0.61, "orders — structured description", ha="center",
            color=TEAL, fontsize=11, weight="bold")
    lines = [
        ("“one row per purchase; amount in USD.”", LIGHT, False),
        ("", LIGHT, False),
        ("uid     → users.id   (FK · 94% overlap)", YELLOW, True),
        ("amount  → revenue metric", GREY, True),
        ("ts      → event time (Iceberg snapshot)", GREY, True),
    ]
    for i, (ln, col, mono) in enumerate(lines):
        ax.text(ox + 0.018, 0.555 - i * 0.052, ln, color=col, fontsize=8.8,
                family="monospace" if mono else "DejaVu Sans",
                style="italic" if not mono and ln else "normal",
                weight="bold" if col == YELLOW else "normal", va="center")
    arrow(ax, hxc[0] + 0.09, hxc[1], ox - 0.008, 0.46, TEAL, lw=1.8, ms=13)
    ax.text(ox + ow / 2, 0.20, "relationships are encoded as fact, not guess",
            ha="center", color=TEAL, fontsize=9.5, style="italic")

    fig.savefig(os.path.join(OUT, "semantic.png"), dpi=100, facecolor=BG)
    plt.close(fig)


# ============================================================================
# 03 — RAG over tables
# ============================================================================
def fig_rag():
    fig, ax = new_fig()
    title(ax, "03", "RAG over tables", YELLOW,
          "an index of tables — by meaning + joinability, not an index of rows")

    # left: a wall of generic table icons (the million-table problem)
    gx0, gy0 = 0.05, 0.18
    for r in range(5):
        for c in range(4):
            x = gx0 + c * 0.045
            y = gy0 + r * 0.085
            box(ax, x, y, 0.034, 0.06, DIM, fc="#10161e", lw=1.0, z=2)
    ax.text(gx0 + 0.075, 0.74, "hundreds of thousands", ha="center",
            color=GREY, fontsize=10, style="italic")
    ax.text(gx0 + 0.075, 0.70, "of tables", ha="center", color=GREY, fontsize=10,
            style="italic")
    arrow(ax, gx0 + 0.20, 0.40, 0.40, 0.40, YELLOW, lw=1.8, ms=13)
    ax.text(0.345, 0.45, "index", ha="center", color=YELLOW, fontsize=9.5,
            style="italic")

    # right: the table index ring with four clusters
    cx, cy, R = 0.66, 0.42, 0.255
    ax.add_patch(Circle((cx, cy), R, edgecolor=DIM, facecolor="none",
                 linewidth=1.4, linestyle=(0, (5, 5)), zorder=2))
    ax.text(cx, cy + R + 0.05, "table index", ha="center", color=GREY,
            fontsize=10.5, style="italic")

    clusters = {
        "users":   (cx - 0.13, cy + 0.12, BLUE),
        "events":  (cx + 0.13, cy + 0.12, PURPLE),
        "orders":  (cx - 0.12, cy - 0.12, GREEN),
        "billing": (cx + 0.13, cy - 0.12, ORANGE),
    }
    rng = np.random.default_rng(11)
    for name, (ccx, ccy, col) in clusters.items():
        pts = np.array([[ccx, ccy]]) + rng.normal(0, 0.028, (4, 2))
        # joinability edges inside the cluster (faint yellow)
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                ax.plot([pts[i, 0], pts[j, 0]], [pts[i, 1], pts[j, 1]],
                        color=YELLOW, lw=0.8, alpha=0.35, zorder=3)
        ax.scatter(pts[:, 0], pts[:, 1], s=55, color=col, zorder=4,
                   edgecolors=BG, linewidths=0.7)
        lbly = ccy + 0.075 if ccy > cy else ccy - 0.075
        ax.text(ccx, lbly, name, ha="center", color=col, fontsize=9.4,
                weight="bold", zorder=5)

    # a natural-language query routes into the orders cluster
    qx, qy = cx - 0.30, cy + 0.20
    ax.scatter([qx], [qy], s=130, color=YELLOW, zorder=6, edgecolors=BG,
               linewidths=1.0)
    ax.text(qx, qy + 0.05, "“users & their orders”", ha="center", color=YELLOW,
            fontsize=9.2, style="italic")
    oc = clusters["orders"]
    curve(ax, qx, qy, oc[0] - 0.02, oc[1] + 0.03, YELLOW, rad=-0.35, lw=1.8, ms=12)
    ax.text(cx - 0.02, cy - 0.235, "→ a small connected subgraph, not a flat list",
            ha="center", color=YELLOW, fontsize=9.5, style="italic")

    fig.savefig(os.path.join(OUT, "rag.png"), dpi=100, facecolor=BG)
    plt.close(fig)


# ============================================================================
# 04 — NL -> SQL
# ============================================================================
def fig_nl2sql():
    fig, ax = new_fig()
    title(ax, "04", "NL → SQL", GREEN,
          "the layers compose: retrieve → confirm → join on real overlap → time-travel")

    # NL question at top-left
    box(ax, 0.04, 0.62, 0.22, 0.10, GREEN, fc="#0f1a11", z=3)
    ax.text(0.15, 0.67, "“revenue per active user,\nlast quarter?”", ha="center",
            va="center", color=LIGHT, fontsize=9.6, style="italic")

    # Step 1: retrieve cluster (RAG)
    s1x = 0.04
    box(ax, s1x, 0.16, 0.20, 0.36, YELLOW, fc="#16140c", z=2)
    ax.text(s1x + 0.10, 0.475, "1 · retrieve cluster", ha="center", color=YELLOW,
            fontsize=10, weight="bold")
    ax.text(s1x + 0.10, 0.44, "1M tables → 3", ha="center", color=GREY,
            fontsize=8.6, style="italic")
    for i, (nm, col) in enumerate([("users", BLUE), ("orders", GREEN),
                                   ("events", PURPLE)]):
        box(ax, s1x + 0.03, 0.335 - i * 0.075, 0.14, 0.058, col, fc="#10161e", z=4)
        ax.text(s1x + 0.10, 0.364 - i * 0.075, nm, ha="center", va="center",
                color=col, fontsize=8.8, weight="bold", family="monospace", zorder=6)
    arrow(ax, 0.15, 0.62, 0.15, 0.525, YELLOW, lw=1.6, ms=11)

    # Step 2: joinability graph with weighted edges
    s2x = 0.30
    box(ax, s2x, 0.16, 0.27, 0.50, BLUE, fc="#0c141b", z=2)
    ax.text(s2x + 0.135, 0.625, "2 · join on real overlap", ha="center",
            color=BLUE, fontsize=10, weight="bold")
    nodes = {
        "users":  (s2x + 0.06, 0.46, BLUE),
        "orders": (s2x + 0.21, 0.46, GREEN),
        "events": (s2x + 0.135, 0.27, PURPLE),
    }
    edges = [("users", "orders", "0.94", YELLOW, 2.6, 1.0),
             ("orders", "events", "0.12", GREY, 1.1, 0.45),
             ("users", "events", "0.08", GREY, 1.0, 0.4)]
    for a, b, w, col, lw, al in edges:
        xa, ya, _ = nodes[a]
        xb, yb, _ = nodes[b]
        ax.plot([xa, xb], [ya, yb], color=col, lw=lw, alpha=al, zorder=3)
        ax.text((xa + xb) / 2, (ya + yb) / 2 + 0.02, w, ha="center",
                color=col, fontsize=8.6, weight="bold" if col == YELLOW else "normal",
                zorder=5)
    for nm, (nx, ny, col) in nodes.items():
        ax.scatter([nx], [ny], s=150, color=col, zorder=4, edgecolors=BG,
                   linewidths=1.0)
        ax.text(nx, ny - 0.05, nm, ha="center", color=col, fontsize=8.6,
                weight="bold", zorder=5)
    ax.text(s2x + 0.135, 0.20, "bright = real join · dim = coincidence",
            ha="center", color=GREY, fontsize=8.4, style="italic")
    arrow(ax, s1x + 0.20, 0.34, s2x - 0.005, 0.40, DIM, lw=1.5, ms=11)

    # Step 3: generated SQL
    s3x = 0.62
    box(ax, s3x, 0.16, 0.34, 0.50, GREEN, fc="#0c130f", z=2)
    ax.text(s3x + 0.17, 0.625, "3 · generated SQL", ha="center", color=GREEN,
            fontsize=10, weight="bold")
    sql = [("SELECT", BLUE), ("  u.id, SUM(o.amount)", GREY),
           ("FROM users u", GREY), ("JOIN orders o", GREY),
           ("  ON o.uid = u.id", YELLOW),
           ("WHERE o.ts >= '2026-01-01'", GREY),
           ("GROUP BY u.id", GREY)]
    for i, (ln, col) in enumerate(sql):
        ax.text(s3x + 0.02, 0.55 - i * 0.044, ln, ha="left", va="center",
                color=col, fontsize=9.2, family="monospace",
                weight="bold" if col == YELLOW else "normal", zorder=5)
    ax.text(s3x + 0.17, 0.205, "+ Iceberg time-travel for “last quarter”",
            ha="center", color=GREY, fontsize=8.4, style="italic")
    arrow(ax, s2x + 0.27, 0.40, s3x - 0.005, 0.40, DIM, lw=1.5, ms=11)

    # confirmation footer
    box(ax, 0.30, 0.045, 0.40, 0.07, GREEN, fc="#0f1a11", z=3)
    ax.text(0.50, 0.08, "user confirms the cluster  ✓   (interactive, not fire-and-forget)",
            ha="center", va="center", color=GREEN, fontsize=9.4)

    fig.savefig(os.path.join(OUT, "nl2sql.png"), dpi=100, facecolor=BG)
    plt.close(fig)


if __name__ == "__main__":
    fig_joinability()
    fig_semantic()
    fig_rag()
    fig_nl2sql()
    for n in ("joinability", "semantic", "rag", "nl2sql"):
        print("wrote", os.path.join(OUT, n + ".png"))
