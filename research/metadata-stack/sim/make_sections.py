"""
Per-section figures for the five-layer data stack post (dark 3blue1brown style).

One focused landscape figure for each of the five layers, placed above its
section in the post. Same Manim-matched palette as `make_summary.py`. A single
running example — a customer who bought a MacBook Air — threads through all five.

Illustrative diagrams (entity names, the "12,847 active customers" figure, serial
numbers, and the per-consumer mismatch are hand-picked for clarity): a visual
restatement of Sanjeev Mohan's FAQ, not output from any live system.

Run:
    python research/metadata-stack/sim/make_sections.py
Writes (1100x560 each) to public/img/metadata-stack/:
    metadata.png  ontology.png  knowledge-graph.png  semantic-layer.png  context-layer.png
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
GREEN  = "#83C167"
YELLOW = "#FFD866"
ORANGE = "#FF8E3C"
PURPLE = "#9A72AC"
RED    = "#FC6255"

plt.rcParams.update({
    "figure.facecolor": BG, "savefig.facecolor": BG,
    "text.color": LIGHT, "font.family": "DejaVu Sans", "font.size": 11,
})

OUT = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "public", "img", "metadata-stack"))
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
    ax.text(0.045, 0.915, num, color=color, fontsize=18, weight="bold",
            family="monospace", va="center")
    ax.text(0.093, 0.915, name, color=LIGHT, fontsize=20, weight="bold", va="center")
    ax.text(0.045, 0.835, subtitle, color=GREY, fontsize=12.5, va="center")


def box(ax, x, y, w, h, ec, fc=PANEL, lw=1.6, r=0.012, z=2, alpha=1.0):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad=0.004,rounding_size={r}",
        linewidth=lw, edgecolor=ec, facecolor=fc, zorder=z, alpha=alpha))


def arrow(ax, x1, y1, x2, y2, color, lw=1.7, ms=13, style="-|>", z=4, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                 mutation_scale=ms, color=color, lw=lw, zorder=z,
                 linestyle=ls, shrinkA=0, shrinkB=0,
                 connectionstyle="arc3,rad=0"))


def curve(ax, x1, y1, x2, y2, color, rad=0.3, lw=1.7, ms=13, z=4, style="-|>"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                 mutation_scale=ms, color=color, lw=lw, zorder=z,
                 connectionstyle=f"arc3,rad={rad}"))


def pill(ax, x, y, label, color, sub=None, fs=9.0, fc="#10161e"):
    """A rounded entity node sized to its word label; edges hide under it."""
    w = 0.034 + 0.0135 * len(label)
    h = 0.066
    box(ax, x - w / 2, y - h / 2, w, h, color, fc=fc, lw=1.9, r=0.03, z=5)
    ax.text(x, y, label, ha="center", va="center", color=color, fontsize=fs,
            weight="bold", zorder=6)
    if sub:
        ax.text(x, y - h / 2 - 0.028, sub, ha="center", va="center", color=GREY,
                fontsize=7.6, family="monospace", zorder=6)


def chip(ax, x, y, text, color, fs=8.4):
    box(ax, x, y - 0.026, 0.012 + 0.0125 * len(text), 0.052, color,
        fc="#10161e", lw=1.2, z=4)
    ax.text(x + 0.006 + 0.0062 * len(text), y, text, ha="center", va="center",
            color=color, fontsize=fs, family="monospace", zorder=5)


# ============================================================================
# 01 — Metadata
# ============================================================================
def fig_metadata():
    fig, ax = new_fig()
    title(ax, "01", "Metadata", BLUE,
          "data about data — the four descriptions that make a cryptic asset usable")

    # center: a raw, meaningless column
    cx, cy = 0.5, 0.42
    box(ax, cx - 0.07, cy - 0.16, 0.14, 0.32, GREY, fc="#10161e", lw=1.6, z=4)
    ax.add_patch(FancyBboxPatch((cx - 0.07, cy + 0.12), 0.14, 0.04,
                 boxstyle="round,pad=0.001,rounding_size=0.006",
                 linewidth=0, facecolor=GREY, alpha=0.22, zorder=5))
    ax.text(cx, cy + 0.14, "cust_addr_st", ha="center", va="center", color=LIGHT,
            fontsize=9.2, family="monospace", weight="bold", zorder=6)
    for i, v in enumerate(["CA", "NY", "TX", "WA", "FL"]):
        ax.text(cx, cy + 0.085 - i * 0.05, v, ha="center", va="center",
                color=GREY, fontsize=9.0, family="monospace", zorder=6)
    ax.text(cx, cy - 0.205, "a raw column — meaningless on its own",
            ha="center", color=GREY, fontsize=9.0, style="italic")

    # four descriptor cards, one per metadata dimension
    cards = [
        (0.045, 0.545, BLUE,   "TECHNICAL",   ["type: varchar(2)", "2-char code, not null"]),
        (0.045, 0.135, TEAL,   "OPERATIONAL", ["lineage: crm.customers", "refreshed 4h ago"]),
        (0.70,  0.545, GREEN,  "SOCIAL",      ["owner: data-platform", "used by 38 dashboards"]),
        (0.70,  0.135, YELLOW, "BUSINESS",    ["= customer's state", "ISO 3166-2:US"]),
    ]
    cw, ch = 0.255, 0.215
    for x, y, col, head, lines in cards:
        box(ax, x, y, cw, ch, col, fc="#10161e", lw=1.6, z=3)
        ax.text(x + 0.015, y + ch - 0.045, head, color=col, fontsize=11,
                weight="bold", va="center")
        for j, ln in enumerate(lines):
            ax.text(x + 0.015, y + ch - 0.105 - j * 0.052, ln, color=GREY,
                    fontsize=8.8, family="monospace", va="center")
        # connector toward the column
        sx = x + cw if x < 0.5 else x
        sy = y + ch / 2
        tx = cx - 0.072 if x < 0.5 else cx + 0.072
        arrow(ax, sx, sy, tx, cy + (0.07 if y > 0.4 else -0.07), col, lw=1.4, ms=10)

    box(ax, 0.30, 0.025, 0.40, 0.065, BLUE, fc="#0c141b", z=3)
    ax.text(0.5, 0.058, "findable · governable · trustworthy", ha="center",
            va="center", color=BLUE, fontsize=10.5, weight="bold")

    fig.savefig(os.path.join(OUT, "metadata.png"), dpi=100, facecolor=BG)
    plt.close(fig)


# ============================================================================
# 02 — Ontology
# ============================================================================
def fig_ontology():
    fig, ax = new_fig()
    title(ax, "02", "Ontology", TEAL,
          "the rules of meaning — beyond “is a kind of” to attributes and legal links")

    # divider
    ax.plot([0.5, 0.5], [0.06, 0.74], color=DIM, lw=1.0, ls=(0, (4, 4)), zorder=1)

    # ---- left: taxonomy (is-a tree) ----
    ax.text(0.05, 0.72, "TAXONOMY", color=GREY, fontsize=12, weight="bold")
    ax.text(0.05, 0.675, "only “is a kind of”", color=GREY, fontsize=9.5, style="italic")
    tx = 0.23
    levels = [("Device", 0.58), ("Laptop", 0.42), ("MacBook Air", 0.26)]
    for i, (lbl, y) in enumerate(levels):
        box(ax, tx - 0.10, y - 0.035, 0.20, 0.07, GREY, fc="#10161e", lw=1.4, z=3)
        ax.text(tx, y, lbl, ha="center", va="center", color=LIGHT, fontsize=9.6,
                weight="bold", zorder=4)
        if i > 0:
            arrow(ax, tx, levels[i - 1][1] - 0.035, tx, y + 0.035, GREY, lw=1.3, ms=10)
            ax.text(tx + 0.015, (levels[i - 1][1] + y) / 2, "is-a", color=GREY,
                    fontsize=7.6, style="italic", va="center")
    ax.text(tx, 0.16, "a clean hierarchy —", ha="center", color=GREY, fontsize=8.8,
            style="italic")
    ax.text(tx, 0.125, "but it can't say what a MacBook *has* or *belongs to*",
            ha="center", color=GREY, fontsize=8.8, style="italic")

    # ---- right: ontology (typed relationship schema) ----
    ax.text(0.555, 0.72, "ONTOLOGY", color=TEAL, fontsize=12, weight="bold")
    ax.text(0.555, 0.675, "entities + attributes + legal relationships",
            color=TEAL, fontsize=9.5, style="italic")

    C = (0.63, 0.55)   # Customer
    O = (0.88, 0.55)   # Order
    P = (0.71, 0.31)   # Product
    K = (0.90, 0.31)   # Chip

    def typed(a, b, label, rad=0.0, col=YELLOW):
        curve(ax, a[0], a[1], b[0], b[1], col, rad=rad, lw=1.6, ms=11)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        ax.text(mx, my + 0.03, label, ha="center", color=col, fontsize=8.2,
                style="italic", zorder=7)

    typed(C, O, "places", rad=0.0)
    typed(O, P, "contains", rad=0.18)
    typed(P, K, "has", rad=0.0, col=PURPLE)
    pill(ax, *C, "Customer", TEAL)
    pill(ax, *O, "Order", TEAL)
    pill(ax, *P, "Product", TEAL)
    pill(ax, *K, "Chip", PURPLE, fs=8.6)
    # attribute note on Product
    ax.text(P[0], P[1] - 0.075, "attrs: name · price", ha="center", color=GREY,
            fontsize=7.6, family="monospace")
    ax.text(0.74, 0.12, "“MacBook Air has an M5 chip, is owned by a Customer”",
            ha="center", color=TEAL, fontsize=8.8, style="italic")
    ax.text(0.74, 0.085, "machine-readable (RDFS / OWL) — the model, not the data",
            ha="center", color=GREY, fontsize=8.4, style="italic")

    fig.savefig(os.path.join(OUT, "ontology.png"), dpi=100, facecolor=BG)
    plt.close(fig)


# ============================================================================
# 03 — Knowledge graph
# ============================================================================
def fig_knowledge_graph():
    fig, ax = new_fig()
    title(ax, "03", "Knowledge graph", GREEN,
          "the ontology populated with real instances — and traversable in multi-hop")

    # left: the empty schema (from layer 2)
    ax.text(0.14, 0.70, "the schema", color=GREY, fontsize=10, style="italic",
            ha="center")
    sc = {"C": (0.07, 0.55), "O": (0.21, 0.55), "P": (0.14, 0.33)}
    for k, (x, y) in sc.items():
        ax.add_patch(Circle((x, y), 0.028, edgecolor=DIM, facecolor="#10161e",
                     lw=1.6, ls=(0, (2, 2)), zorder=4))
        ax.text(x, y, k, ha="center", va="center", color=GREY, fontsize=9,
                weight="bold", zorder=5)
    for a, b in [("C", "O"), ("O", "P")]:
        ax.plot([sc[a][0], sc[b][0]], [sc[a][1], sc[b][1]], color=DIM, lw=1.2,
                ls=(0, (3, 3)), zorder=3)
    ax.text(0.14, 0.24, "classes & rules", ha="center", color=GREY, fontsize=8.4,
            style="italic")

    arrow(ax, 0.27, 0.45, 0.36, 0.45, GREEN, lw=1.8, ms=13)
    ax.text(0.315, 0.50, "populate", ha="center", color=GREEN, fontsize=8.8,
            style="italic")

    # right: the populated graph with a highlighted multi-hop path
    nodes = {
        "jane":  (0.48, 0.63, BLUE,   "Jane",        "customer #4471"),
        "order": (0.68, 0.63, GREEN,  "Order",       "#1184"),
        "mac":   (0.68, 0.35, TEAL,   "MacBook Air", "C02XYZ123"),
        "chip":  (0.89, 0.35, PURPLE, "M5",          "chip gen"),
        "recall":(0.89, 0.63, ORANGE, "Recall",      "battery"),
    }

    # the multi-hop path Jane -> Order -> MacBook -> M5 chip -> Recall
    path = [("jane", "order", "placed", 0.0), ("order", "mac", "contains", 0.04),
            ("mac", "chip", "has", 0.0), ("chip", "recall", "affected by", 0.05)]
    for a, b, lbl, lx in path:
        xa, ya = nodes[a][0], nodes[a][1]
        xb, yb = nodes[b][0], nodes[b][1]
        arrow(ax, xa, ya, xb, yb, GREEN, lw=2.2, ms=12)
        ax.text((xa + xb) / 2 + lx, (ya + yb) / 2 + 0.022, lbl, ha="center",
                color=GREEN, fontsize=7.8, style="italic", zorder=7)
    for k, (x, y, c, lbl, sub) in nodes.items():
        pill(ax, x, y, lbl, c, sub=sub, fs=8.6)

    box(ax, 0.46, 0.075, 0.46, 0.10, GREEN, fc="#0c130f", z=3)
    ax.text(0.69, 0.138, "“Is Jane's laptop affected by the battery recall?”",
            ha="center", va="center", color=LIGHT, fontsize=9.4, style="italic")
    ax.text(0.69, 0.103, "four hops — a question plain SQL can't answer in one query",
            ha="center", va="center", color=GREEN, fontsize=8.8, weight="bold")

    fig.savefig(os.path.join(OUT, "knowledge-graph.png"), dpi=100, facecolor=BG)
    plt.close(fig)


# ============================================================================
# 04 — Semantic layer
# ============================================================================
def fig_semantic_layer():
    fig, ax = new_fig()
    title(ax, "04", "Semantic layer", YELLOW,
          "the governed contract — one definition of a metric, served to everyone")

    ax.plot([0.46, 0.46], [0.06, 0.74], color=DIM, lw=1.0, ls=(0, (4, 4)), zorder=1)

    consumers = [("BI dashboard", BLUE), ("analyst's SQL", TEAL), ("AI agent", ORANGE)]

    # ---- left: WITHOUT — everyone counts it their own way ----
    ax.text(0.04, 0.71, "WITHOUT", color=RED, fontsize=12, weight="bold")
    ax.text(0.04, 0.665, "each consumer reinvents the metric", color=GREY,
            fontsize=9.2, style="italic")
    nums = ["12,847", "11,200", "13,991"]
    for i, ((lbl, col), n) in enumerate(zip(consumers, nums)):
        y = 0.50 - i * 0.135
        box(ax, 0.04, y - 0.05, 0.20, 0.10, col, fc="#10161e", lw=1.5, z=3)
        ax.text(0.14, y + 0.012, lbl, ha="center", color=col, fontsize=9.2,
                weight="bold")
        ax.text(0.14, y - 0.025, '"active customers"', ha="center", color=GREY,
                fontsize=7.8, style="italic")
        box(ax, 0.28, y - 0.038, 0.13, 0.076, RED, fc="#1d1113", z=3)
        ax.text(0.345, y, n, ha="center", va="center", color=RED, fontsize=12,
                weight="bold", family="monospace")
    ax.text(0.225, 0.075, "three dashboards, three numbers → nobody trusts any",
            ha="center", color=RED, fontsize=8.8, style="italic")

    # ---- right: WITH — one hub, one number ----
    ax.text(0.55, 0.71, "WITH", color=YELLOW, fontsize=12, weight="bold")
    ax.text(0.55, 0.665, "one canonical definition, served as an API", color=YELLOW,
            fontsize=9.2, style="italic")

    hub = (0.66, 0.42)
    box(ax, hub[0] - 0.085, hub[1] - 0.085, 0.17, 0.17, YELLOW, fc="#1a180e", lw=2.0, z=4)
    ax.text(hub[0], hub[1] + 0.05, "semantic layer", ha="center", color=YELLOW,
            fontsize=9.4, weight="bold", zorder=5)
    ax.text(hub[0], hub[1] + 0.01, "Active Customer =", ha="center", color=LIGHT,
            fontsize=8.4, family="monospace", zorder=5)
    ax.text(hub[0], hub[1] - 0.022, "txn in last 90 days", ha="center", color=GREY,
            fontsize=8.0, family="monospace", zorder=5)
    ax.text(hub[0], hub[1] - 0.058, "= 12,847", ha="center", color=YELLOW,
            fontsize=9.6, weight="bold", family="monospace", zorder=5)

    cy_positions = [0.62, 0.42, 0.22]
    for (lbl, col), y in zip(consumers, cy_positions):
        x = 0.895
        box(ax, x - 0.075, y - 0.03, 0.15, 0.06, col, fc="#10161e", lw=1.4, z=3)
        ax.text(x, y, lbl, ha="center", va="center", color=col, fontsize=8.4,
                weight="bold", zorder=4)
        arrow(ax, hub[0] + 0.085, hub[1] + (y - hub[1]) * 0.35, x - 0.078, y,
              YELLOW, lw=1.5, ms=11)
        ax.text(x, y - 0.05, "12,847", ha="center", color=YELLOW, fontsize=8.0,
                family="monospace")
    ax.text(0.72, 0.075, "same number everywhere — “and here's exactly how we count it”",
            ha="center", color=YELLOW, fontsize=8.8, style="italic")

    fig.savefig(os.path.join(OUT, "semantic-layer.png"), dpi=100, facecolor=BG)
    plt.close(fig)


# ============================================================================
# 05 — Context layer
# ============================================================================
def fig_context_layer():
    fig, ax = new_fig()
    title(ax, "05", "Context layer", ORANGE,
          "the moment — assembling the right signals at runtime, for one decision")

    # center: the live agent turn
    hub = (0.5, 0.44)
    ax.add_patch(RegularPolygon(hub, numVertices=6, radius=0.085, orientation=0,
                 edgecolor=ORANGE, facecolor="#1d150c", lw=2.4, zorder=6))
    ax.text(hub[0], hub[1] + 0.018, "agent", ha="center", va="center", color=ORANGE,
            fontsize=11, weight="bold", zorder=7)
    ax.text(hub[0], hub[1] - 0.022, "this turn", ha="center", va="center", color=GREY,
            fontsize=8.0, style="italic", zorder=7)

    # the live question
    box(ax, hub[0] - 0.17, 0.725, 0.34, 0.075, ORANGE, fc="#1d150c", z=4)
    ax.text(hub[0], 0.7625, "“Jane's on the line — what should I offer her?”",
            ha="center", va="center", color=LIGHT, fontsize=9.0, style="italic", zorder=5)
    arrow(ax, hub[0], 0.725, hub[0], hub[1] + 0.088, ORANGE, lw=1.6, ms=11)

    # sources streaming in at runtime
    sources = [
        (0.085, 0.66, GREEN,  "knowledge graph", "Jane → MacBook → recall"),
        (0.085, 0.44, BLUE,   "warranty system", "expires in 11 days"),
        (0.085, 0.22, TEAL,   "support PDFs",    "defect pattern: battery"),
        (0.915, 0.66, YELLOW, "semantic metrics","LTV, churn risk"),
        (0.915, 0.44, PURPLE, "web + Slack logs","viewed refund page 3×"),
        (0.915, 0.22, GREY,   "her last tweet",  "“2nd time this happens…”"),
    ]
    for x, y, col, lbl, val in sources:
        left = x < 0.5
        w = 0.235
        bx = x if left else x - w
        box(ax, bx, y - 0.045, w, 0.09, col, fc="#10161e", lw=1.4, z=3)
        ax.text(bx + 0.014, y + 0.018, lbl, color=col, fontsize=8.8, weight="bold",
                va="center")
        ax.text(bx + 0.014, y - 0.018, val, color=GREY, fontsize=7.8,
                family="monospace", va="center")
        sx = bx + w if left else bx
        rad = -0.18 if (y > hub[1]) == left else 0.18
        curve(ax, sx, y, hub[0] + (-0.082 if left else 0.082),
              hub[1] + (0.03 if y > hub[1] else -0.03), col, rad=rad, lw=1.4, ms=10)

    ax.text(0.5, 0.075, "ephemeral, assembled per turn — semantics gives the vocabulary,",
            ha="center", color=ORANGE, fontsize=9.0, style="italic")
    ax.text(0.5, 0.04, "the graph gives the facts, the context layer gives the moment",
            ha="center", color=ORANGE, fontsize=9.0, style="italic")

    fig.savefig(os.path.join(OUT, "context-layer.png"), dpi=100, facecolor=BG)
    plt.close(fig)


if __name__ == "__main__":
    fig_metadata()
    fig_ontology()
    fig_knowledge_graph()
    fig_semantic_layer()
    fig_context_layer()
    for n in ("metadata", "ontology", "knowledge-graph", "semantic-layer", "context-layer"):
        print("wrote", os.path.join(OUT, n + ".png"))
