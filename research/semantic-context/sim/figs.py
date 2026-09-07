"""
Figures for the post "Semantic Context That Builds Itself"
(content/posts/2026-09-04-semantic-context-that-builds-itself.md).

Dark 3blue1brown-style schematics on a pure-black background. None of these is a
data plot: they are labelled concept diagrams. The only numbers drawn are the
directional-containment ratios from the customers/transfers example described in
the post (about 89% one way, 11% the other, Jaccard 0.11); the join-specification
card is explicitly marked as an illustrative example.

Run:
    python research/semantic-context/sim/figs.py
Writes to public/img/semantic-context/:
    social.png       1200x630 lead / social card: the three-layer pedestal
    history.png      the same schema bare vs. annotated with its history
    containment.png  directional containment vs. Jaccard on the wallet example
    evidence.png     one join spec with its evidence panels + the authority ladder
    loop.png         the learn-from-mistakes loop with its asymmetry
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import (FancyBboxPatch, FancyArrowPatch, Circle,
                                Polygon, Rectangle)

BG, LIGHT, MUTED, DIM = "#000000", "#ededed", "#8b95a5", "#2a3140"
CYAN, GOLD, GREEN, RED, PURPLE = "#3fc1ff", "#ffd166", "#7CFC8A", "#ff5a5a", "#b48cff"
PANEL = "#0b0f15"

plt.rcParams.update({
    "figure.facecolor": BG, "savefig.facecolor": BG, "text.color": LIGHT,
    "font.family": "DejaVu Sans", "font.size": 11,
})

OUT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                    "public", "img", "semantic-context"))
os.makedirs(OUT, exist_ok=True)


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis("off")
    ax.set_aspect("equal")
    return fig, ax


def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p, facecolor=BG, dpi=100)
    plt.close(fig)
    print("wrote", p)


def rbox(ax, x, y, w, h, ec, fc=PANEL, lw=1.6, r=10, z=2, alpha=1.0, ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                linewidth=lw, edgecolor=ec, facecolor=fc, zorder=z,
                                alpha=alpha, linestyle=ls))


def arrow(ax, p, q, color, lw=1.6, style="-|>", ms=14, z=4, ls="-", rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=ms, color=color,
                                 lw=lw, zorder=z, linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}"))


def text(ax, x, y, s, size=11, color=LIGHT, ha="center", va="center", w="normal",
         z=6, family=None, alpha=1.0):
    ax.text(x, y, s, fontsize=size, color=color, ha=ha, va=va, fontweight=w,
            zorder=z, family=family, alpha=alpha)


# ----------------------------------------------------------------------------
# 1. Social card: the pedestal
# ----------------------------------------------------------------------------
def pedestal(ax, cx, base_y, widths, heights, colors, labels, subs, size=16,
             subsize=10.5, gap=6):
    """Three stacked tiers, narrowing upward. Returns the tier centres."""
    y = base_y
    centres = []
    for w, h, c, lab, sub in zip(widths, heights, colors, labels, subs):
        rbox(ax, cx - w / 2, y, w, h, c, fc=PANEL, lw=2, r=8)
        # a faint tinted fill so the tiers read as solid
        ax.add_patch(Rectangle((cx - w / 2 + 2, y + 2), w - 4, h - 4, color=c,
                               alpha=0.10, zorder=2.5))
        text(ax, cx, y + h * 0.62, lab, size=size, color=c, w="bold")
        text(ax, cx, y + h * 0.28, sub, size=subsize, color=MUTED)
        centres.append((cx, y + h / 2, w, h))
        y += h + gap
    return centres


fig, ax = canvas(1200, 630)
text(ax, 60, 560, "Semantic Context That Builds Itself", size=34, color=LIGHT,
     ha="left", w="bold")
text(ax, 60, 512, "Your data has a history. Your agent needs to know it.", size=17,
     color=MUTED, ha="left")

cx = 640
tiers = pedestal(ax, cx, 70,
                 widths=[760, 560, 360], heights=[118, 118, 118],
                 colors=[CYAN, GOLD, PURPLE],
                 labels=["Physical structure", "Usage", "Curation"],
                 subs=["tables · columns · sketches · containment · lineage · freshness",
                       "query logs · join keys · filters · dashboards · query families",
                       "caveats · exceptions · approvals · rejections"])

# cost arrow on the left
arrow(ax, (245, 90), (245, 415), MUTED, lw=1.8, ms=16)
text(ax, 232, 252, "cost of obtaining", size=11, color=MUTED, ha="right")
text(ax, 232, 232, "human attention", size=11, color=MUTED, ha="right")
text(ax, 232, 100, "cheap · continuous · derived", size=10.5, color=CYAN, ha="right")
text(ax, 232, 405, "expensive · scarce · asked", size=10.5, color=PURPLE, ha="right")

# reinforcement arrows on the right
arrow(ax, (1040, 130), (1040, 190), CYAN, lw=1.4, ms=12, rad=0.0)
text(ax, 1052, 158, "proposes", size=10.5, color=CYAN, ha="left")
arrow(ax, (1040, 255), (1040, 315), GOLD, lw=1.4, ms=12)
text(ax, 1052, 283, "strengthens", size=10.5, color=GOLD, ha="left")
arrow(ax, (1175, 400), (1175, 100), PURPLE, lw=1.4, ms=12, ls=(0, (4, 3)))
text(ax, 1163, 215, "explains the\nexceptions", size=10.5, color=PURPLE, ha="right")
save(fig, "social.png")


# ----------------------------------------------------------------------------
# 2. History: the schema, bare and annotated
# ----------------------------------------------------------------------------
def schema(ax, ox, oy, annotate):
    """A 5-table ER sketch at origin (ox, oy). Optionally overlay the history."""
    tables = {
        "customers": (ox + 40, oy + 300, ["id", "wallet", "type"]),
        "orders": (ox + 300, oy + 300, ["id", "customer_id", "amount"]),
        "events_v1": (ox + 40, oy + 90, ["ts", "customer_id", "kind"]),
        "events_v2": (ox + 300, oy + 90, ["ts", "customer_id", "kind"]),
        "transfers": (ox + 560, oy + 195, ["id", "to_address", "value"]),
    }
    W, H = 180, 96
    for name, (x, y, cols) in tables.items():
        rbox(ax, x, y, W, H, DIM, fc=PANEL, lw=1.4, r=6)
        ax.add_patch(Rectangle((x, y + H - 26), W, 26, color=DIM, alpha=0.55, zorder=2.5))
        text(ax, x + 10, y + H - 13, name, size=11, color=LIGHT, ha="left", w="bold",
             family="DejaVu Sans Mono")
        for i, c in enumerate(cols):
            text(ax, x + 12, y + H - 44 - i * 20, c, size=9.5, color=MUTED, ha="left",
                 family="DejaVu Sans Mono")
    # relationships
    e = [("customers", "orders"), ("customers", "events_v1"), ("orders", "events_v2"),
         ("customers", "transfers"), ("orders", "transfers")]
    ctr = {n: (x + W / 2, y + H / 2) for n, (x, y, _) in tables.items()}
    for a, b in e:
        ax.plot([ctr[a][0], ctr[b][0]], [ctr[a][1], ctr[b][1]], color=DIM, lw=1.4,
                zorder=1)
    if not annotate:
        return
    notes = [  # (x, y, text, color, anchor point)
        (ox + 150, oy + 440, "ingestion failed Mar 3–6,\nhandle that window separately",
         GOLD, (ox + 390, oy + 396)),
        (ox + 470, oy + 470, "customer_id is lowercase here,\nmixed-case in customers",
         GOLD, (ox + 390, oy + 340)),
        (ox + 170, oy + 10, "reliable until Jan 2026 …", GOLD, (ox + 130, oy + 90)),
        (ox + 440, oy + 10, "… then use v2 instead", GOLD, (ox + 390, oy + 90)),
        (ox + 630, oy + 150, "joins on customer wallet,\nbut not for revenue reporting",
         RED, (ox + 400, oy + 290)),
        (ox + 650, oy + 555, "looks like the right table\nfor volume. It isn't.",
         RED, (ox + 650, oy + 291)),
    ]
    for x, y, s, c, anchor in notes:
        text(ax, x, y, s, size=10, color=c, ha="center", z=8)
        ax.plot([x, anchor[0]], [y, anchor[1]], color=c, lw=0.9, alpha=0.7, zorder=7,
                linestyle=(0, (2, 2)))


fig, ax = canvas(1600, 640)
text(ax, 400, 600, "what the schema says", size=17, color=MUTED)
text(ax, 1200, 600, "what the analysts know", size=17, color=GOLD)
schema(ax, 20, 40, annotate=False)
ax.plot([800, 800], [30, 570], color=DIM, lw=1, zorder=1)
schema(ax, 820, 40, annotate=True)
save(fig, "history.png")


# ----------------------------------------------------------------------------
# 3. Directional containment
# ----------------------------------------------------------------------------
fig, ax = canvas(1600, 700)
# transfers.to_address ~ 4.0M distinct, customers.wallet ~ 0.5M, 89% of the
# small set inside the big one. Areas proportional to set sizes (ratio 8).
R_big = 250
R_small = R_big / np.sqrt(8)
cb = (620, 350)
# place the small circle so ~89% of its area overlaps the big one
d = R_big - R_small * 0.72
cs = (cb[0] + d, cb[1])
ax.add_patch(Circle(cb, R_big, facecolor=GOLD, alpha=0.10, edgecolor=GOLD, lw=2, zorder=2))
ax.add_patch(Circle(cs, R_small, facecolor=CYAN, alpha=0.18, edgecolor=CYAN, lw=2, zorder=3))
text(ax, cb[0] - 60, cb[1] + 40, "transfers.to_address", size=15, color=GOLD, w="bold",
     family="DejaVu Sans Mono")
text(ax, cb[0] - 60, cb[1] + 10, "~4,000,000 distinct", size=11.5, color=MUTED)
text(ax, cs[0] + 8, cs[1] - R_small - 28, "customers.wallet", size=15, color=CYAN,
     w="bold", family="DejaVu Sans Mono")
text(ax, cs[0] + 8, cs[1] - R_small - 54, "~500,000 distinct", size=11.5, color=MUTED)

# right-hand explanations
x0 = 1010
text(ax, x0, 560, "wallet ⊂ to_address", size=18, color=CYAN, ha="left", w="bold")
text(ax, x0, 522, "89% of customer wallets appear as a transfer destination",
     size=12.5, color=LIGHT, ha="left")
text(ax, x0, 496, "→ a strong subset relationship, this join is real", size=12.5,
     color=CYAN, ha="left")

text(ax, x0, 410, "to_address ⊂ wallet", size=18, color=GOLD, ha="left", w="bold")
text(ax, x0, 372, "11% of transfer destinations are customer wallets", size=12.5,
     color=LIGHT, ha="left")
text(ax, x0, 346, "→ most transfers go elsewhere, and that's fine", size=12.5,
     color=GOLD, ha="left")

text(ax, x0, 258, "Jaccard = overlap / union ≈ 0.11", size=18, color=RED, ha="left",
     w="bold")
text(ax, x0, 220, "the symmetric metric averages the two views away", size=12.5,
     color=LIGHT, ha="left")
text(ax, x0, 194, "→ looks like noise, the relationship is missed", size=12.5,
     color=RED, ha="left")

text(ax, x0, 110, "Containment is directional. Jaccard isn't.", size=14, color=MUTED,
     ha="left")
text(ax, x0, 82, "Ask “how much of A is in B?” separately from “how much of B is in A?”",
     size=11.5, color=MUTED, ha="left")
save(fig, "containment.png")


# ----------------------------------------------------------------------------
# 4. Evidence over verdicts + the authority ladder
# ----------------------------------------------------------------------------
fig, ax = canvas(1600, 760)
# the join card
cx0, cy0, cw, ch = 30, 60, 1040, 640
rbox(ax, cx0, cy0, cw, ch, DIM, fc=PANEL, lw=1.6, r=12)
text(ax, cx0 + 28, cy0 + ch - 40, "join specification", size=12, color=MUTED, ha="left")
text(ax, cx0 + cw - 28, cy0 + ch - 40, "illustrative example", size=10.5, color=DIM,
     ha="right")
text(ax, cx0 + 28, cy0 + ch - 78, "transfers.to_address  ↔  customers.wallet", size=17,
     color=LIGHT, ha="left", w="bold", family="DejaVu Sans Mono")

panels = [
    (CYAN, "physical", [
        "wallet → to_address    0.89",
        "to_address → wallet    0.11",
        "types    varchar ↔ varchar",
        "distinct ratio  0.98 · 0.71",
        "fanout   1 wallet → many rows",
    ]),
    (GOLD, "usage", [
        "explicit joins  many, this key",
        "success rate    high",
        "query families  3 exemplars",
        "filtered by     ts, chain",
        "feeds           settlement_daily",
    ]),
    (PURPLE, "curation", [
        "status       candidate",
        "approved by  nobody yet",
        "req. filter  none declared",
        "caveat       —",
        "conflicts    none",
    ]),
]
pw, ph = 315, 330
px0, py0 = cx0 + 28, cy0 + 150
for i, (c, title, lines) in enumerate(panels):
    x = px0 + i * (pw + 18)
    rbox(ax, x, py0, pw, ph, c, fc=BG, lw=1.6, r=8)
    text(ax, x + 16, py0 + ph - 28, title, size=13.5, color=c, ha="left", w="bold")
    for j, ln in enumerate(lines):
        text(ax, x + 16, py0 + ph - 72 - j * 44, ln, size=10, color=LIGHT, ha="left",
             family="DejaVu Sans Mono")

# score bar underneath
bx, by, bw = px0, cy0 + 70, pw * 3 + 36
ax.add_patch(Rectangle((bx, by), bw, 18, color=DIM, zorder=3))
ax.add_patch(Rectangle((bx, by), bw * 0.72, 18, color=GREEN, alpha=0.75, zorder=4))
text(ax, bx, by + 42, "score", size=12, color=GREEN, ha="left", w="bold")
text(ax, bx + 62, by + 42, "ranks candidates. Never replaces the evidence above.",
     size=11.5, color=MUTED, ha="left")

# the ladder
lx, lw_ = 1200, 360
text(ax, lx + lw_ / 2, cy0 + ch - 40, "authority ladder", size=12, color=MUTED)
ladder = [(PURPLE, "curated", "what people told us"),
          (GOLD, "usage", "what people do"),
          (CYAN, "physical", "what the data shows")]
ly = cy0 + ch - 110
for c, name, sub in ladder:
    rbox(ax, lx, ly - 110, lw_, 110, c, fc=PANEL, lw=2, r=8)
    ax.add_patch(Rectangle((lx + 2, ly - 108), lw_ - 4, 106, color=c, alpha=0.10, zorder=2.5))
    text(ax, lx + lw_ / 2, ly - 42, name, size=17, color=c, w="bold")
    text(ax, lx + lw_ / 2, ly - 78, sub, size=11, color=MUTED)
    ly -= 130
arrow(ax, (lx - 28, cy0 + 150), (lx - 28, cy0 + ch - 120), MUTED, lw=1.6)
text(ax, lx - 42, cy0 + 380, "wins on\nconflict", size=11, color=MUTED, ha="right")
text(ax, lx + lw_ / 2, cy0 + 118, "nothing is averaged.", size=12, color=LIGHT)
text(ax, lx + lw_ / 2, cy0 + 92, "a disagreement is kept, and shown.", size=12, color=LIGHT)
save(fig, "evidence.png")


# ----------------------------------------------------------------------------
# 5. The loop, with its asymmetry
# ----------------------------------------------------------------------------
fig, ax = canvas(1600, 760)
C = (470, 390)
R = 250
steps = [("Observe", CYAN), ("Infer", CYAN), ("Use", GOLD), ("Discover", GOLD),
         ("Curate", PURPLE), ("Improve", GREEN)]
pts = []
for i, (name, col) in enumerate(steps):
    a = np.pi / 2 - i * 2 * np.pi / len(steps)
    p = (C[0] + R * np.cos(a), C[1] + R * np.sin(a))
    pts.append(p)
    ax.add_patch(Circle(p, 46, facecolor=PANEL, edgecolor=col, lw=2, zorder=4))
    text(ax, p[0], p[1], name, size=12.5, color=col, w="bold", z=6)
for i in range(len(pts)):
    p, q = pts[i], pts[(i + 1) % len(pts)]
    v = np.array(q) - np.array(p); v /= np.linalg.norm(v)
    arrow(ax, (p[0] + v[0] * 52, p[1] + v[1] * 52), (q[0] - v[0] * 52, q[1] - v[1] * 52),
          MUTED, lw=1.6, ms=14, rad=-0.18)
text(ax, C[0], C[1] + 22, "context", size=15, color=LIGHT, w="bold")
text(ax, C[0], C[1] - 8, "graph", size=15, color=LIGHT, w="bold")
text(ax, C[0], C[1] - 42, "revisioned · append-only", size=10, color=MUTED)

# labels on the ring
ring_notes = [(0, "profile · sketch · read the logs"), (1, "containment · families · lineage"),
              (2, "agent gets a bounded working set"), (3, "a join that almost didn't match"),
              (4, "a human promotes or rejects"), (5, "next agent starts from it")]
for i, s in ring_notes:
    a = np.pi / 2 - i * 2 * np.pi / len(steps)
    x, y = C[0] + (R + 92) * np.cos(a), C[1] + (R + 92) * np.sin(a)
    ha = "left" if np.cos(a) > 0.2 else ("right" if np.cos(a) < -0.2 else "center")
    text(ax, x, y, s, size=10, color=MUTED, ha=ha)

# the asymmetry: two branches out of Discover
dx, dy = pts[3]
x1 = 1060
text(ax, x1, 640, "the learning is asymmetric", size=16, color=LIGHT, ha="left", w="bold")

# positive branch
rbox(ax, x1, 470, 500, 110, GREEN, fc=PANEL, lw=1.8, r=8)
text(ax, x1 + 18, 552, "positive signal", size=13, color=GREEN, ha="left", w="bold")
text(ax, x1 + 18, 522, "validated answer · “useful” · corroborated execution", size=10.5,
     color=LIGHT, ha="left")
text(ax, x1 + 18, 494, "→ a small, capped boost, shown as its own component", size=10.5,
     color=GREEN, ha="left")
arrow(ax, (dx + 40, dy + 20), (x1 - 8, 525), GREEN, lw=1.4, ms=12, rad=-0.25)

# negative branch
rbox(ax, x1, 300, 500, 110, RED, fc=PANEL, lw=1.8, r=8)
text(ax, x1 + 18, 382, "negative signal", size=13, color=RED, ha="left", w="bold")
text(ax, x1 + 18, 352, "“incorrect” · rejected recommendation · failed join", size=10.5,
     color=LIGHT, ha="left")
text(ax, x1 + 18, 324, "→ never lowers a score. Opens a review item for a human.",
     size=10.5, color=RED, ha="left")
arrow(ax, (dx + 40, dy - 20), (x1 - 8, 355), RED, lw=1.4, ms=12, rad=0.25)

# review queue → curate
rbox(ax, x1, 140, 500, 100, PURPLE, fc=PANEL, lw=1.8, r=8, ls=(0, (5, 3)))
text(ax, x1 + 18, 212, "review queue", size=13, color=PURPLE, ha="left", w="bold")
text(ax, x1 + 18, 184, "flagged joins · proposed caveats · stale approvals", size=10.5,
     color=LIGHT, ha="left")
text(ax, x1 + 18, 158, "each with a paste-ready curation snippet", size=10.5, color=MUTED,
     ha="left")
arrow(ax, (x1 + 250, 300), (x1 + 250, 242), RED, lw=1.4, ms=12)
cxp, cyp = pts[4]
arrow(ax, (x1 - 8, 190), (cxp + 48, cyp - 10), PURPLE, lw=1.4, ms=12, rad=0.25,
      ls=(0, (5, 3)))
text(ax, x1, 70, "a successful query is not proof the join was correct.", size=11.5,
     color=MUTED, ha="left")
text(ax, x1, 44, "only humans move a join from candidate to approved.", size=11.5,
     color=MUTED, ha="left")
save(fig, "loop.png")
