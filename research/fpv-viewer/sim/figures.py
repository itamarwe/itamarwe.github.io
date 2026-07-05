"""
Figures for the FPV *viewer* post (the interactive explorer at /fpv), distinct
from the dataset post's figures.

  - tool_flow.png        : qualitative schematic of the three views the tool gives
                           you (gallery -> annotated player -> 3-D scene). Concept
                           diagram, no numeric axes.
  - annotated_clip.png   : REAL flight-annotation timeline of one clip
                           (2026-06-06 Merkava tank, Blat), straight from the
                           dataset's segment markers. Shows how much of a
                           propaganda clip is banner / replay / pause vs. flight.
  - footage_breakdown.png: REAL — of all annotated footage across the dataset,
                           how the seconds split by segment type. Durations are
                           summed from consecutive segment boundaries (the final,
                           open-ended segment of each clip is excluded because the
                           clip end time isn't in the manifest).
  - social.png           : 1200x630 OpenGraph card for the post.

All counts/durations are REAL, computed from ../2026-07-05_videos_snapshot.json
(a frozen copy of public/fpv/data/videos.json; the live one keeps growing).
The little gallery cards and point clouds drawn inside the schematics are
illustrative stand-ins, not screenshots — they're there to say "this is what the
view looks like," not to plot data.
"""
import os, json
from collections import Counter
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "2026-07-05_videos_snapshot.json")
OUT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "public", "img", "fpv-viewer"))
os.makedirs(OUT, exist_ok=True)

BG = "#000000"; PANEL = "#0c0f14"; TXT = "#ededed"; MUTED = "#8b95a5"
CYAN, GOLD, GREEN, RED, PURPLE = "#3fc1ff", "#ffd166", "#7CFC8A", "#ff5a5a", "#b48cff"

plt.rcParams.update({
    "figure.facecolor": BG, "savefig.facecolor": BG, "axes.facecolor": BG,
    "text.color": TXT, "axes.labelcolor": TXT, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.edgecolor": "#333a45", "font.size": 12,
    "font.family": "sans-serif",
})

# segment type -> (display label, colour). "flight" is the signal; the rest is
# editing added on top of the footage.
SEG = {
    "flight_start":     ("Flight",     CYAN),
    "new_flight_start": ("Flight",     CYAN),
    "banner_start":     ("Banner",     MUTED),
    "replay_start":     ("Replay",     PURPLE),
    "pause_start":      ("Pause/freeze", "#4a5260"),
    "other":            ("Other",      "#6b7480"),
}


def load():
    return json.load(open(DATA))["videos"]


# --------------------------------------------------------------------------
# small reusable "what the view looks like" glyphs (illustrative, not data)
# --------------------------------------------------------------------------
def draw_gallery(ax, x0, y0, w, h):
    """A grid of thumbnail cards, a couple with a 3D badge."""
    cols, rows = 3, 2
    gx, gy = 0.06 * w, 0.10 * h
    cw = (w - (cols + 1) * gx) / cols
    ch = (h - (rows + 1) * gy) / rows
    badge = {(0, 0), (2, 1), (1, 0)}
    rng = np.random.default_rng(7)
    for r in range(rows):
        for c in range(cols):
            cx = x0 + gx + c * (cw + gx)
            cy = y0 + h - (r + 1) * (ch + gy) + gy
            ax.add_patch(FancyBboxPatch((cx, cy), cw, ch,
                         boxstyle="round,pad=0,rounding_size=0.02",
                         linewidth=1.0, edgecolor="#2b323c",
                         facecolor="#161b22"))
            # faint "terrain" streaks so it reads as a frame, not an empty box
            for _ in range(3):
                yy = cy + rng.uniform(0.15, 0.85) * ch
                ax.plot([cx + 0.08 * cw, cx + 0.92 * cw], [yy, yy],
                        color="#232a33", lw=1.0)
            if (c, r) in badge:
                bw, bh = 0.34 * cw, 0.20 * ch
                ax.add_patch(FancyBboxPatch((cx + cw - bw - 0.05 * cw,
                             cy + ch - bh - 0.08 * ch), bw, bh,
                             boxstyle="round,pad=0,rounding_size=0.015",
                             linewidth=0, facecolor=GOLD, alpha=0.9))
                ax.text(cx + cw - bw / 2 - 0.05 * cw,
                        cy + ch - bh / 2 - 0.08 * ch, "3D",
                        ha="center", va="center", color="#000", fontsize=6.5,
                        fontweight="bold")


def draw_timeline(ax, x0, y0, w, h, segs):
    """A horizontal annotation ribbon from real (time, type) boundaries."""
    times = [s["time"] for s in segs]
    T = times[-1] + 4.0  # pad the open final segment for drawing
    bh = 0.42 * h
    by = y0 + 0.30 * h
    for i, s in enumerate(segs):
        t0 = times[i]
        t1 = times[i + 1] if i + 1 < len(segs) else T
        col = SEG.get(s["type"], ("", MUTED))[1]
        ax.add_patch(Rectangle((x0 + w * t0 / T, by), w * (t1 - t0) / T, bh,
                     facecolor=col, edgecolor=BG, linewidth=0.8))
    # playhead
    px = x0 + w * 0.36
    ax.plot([px, px], [by - 0.10 * h, by + bh + 0.10 * h], color=GOLD, lw=1.6)
    ax.add_patch(plt.Circle((px, by + bh + 0.10 * h), 0.012 * w, color=GOLD))
    return T


def draw_scene(ax, cx, cy, s):
    """A little point cloud with a cyan->gold flight path arcing onto a target."""
    rng = np.random.default_rng(3)
    pts = rng.normal(0, 1, (260, 2)) * np.array([1.5, 0.7]) * s
    ax.scatter(cx + pts[:, 0], cy + pts[:, 1] - 0.5 * s, s=2.2,
               c="#3a444f", alpha=0.7, linewidths=0)
    t = np.linspace(0, 1, 60)
    px = cx + (-2.2 + 2.4 * t) * s
    py = cy + (1.5 * s) * (1 - t) ** 1.6 - 0.15 * s
    cols = plt.cm.ScalarMappable().to_rgba(t)  # unused; explicit gradient below
    for i in range(len(t) - 1):
        f = i / (len(t) - 1)
        col = (CYAN if f < 0.5 else GOLD)
        ax.plot(px[i:i + 2], py[i:i + 2], color=col, lw=2.0, alpha=0.9)
    ax.scatter([px[0]], [py[0]], s=26, color=GREEN, zorder=5)   # launch
    ax.scatter([px[-1]], [py[-1]], s=30, color=RED, marker="X", zorder=5)  # target


# --------------------------------------------------------------------------
def fig_tool_flow(videos):
    ex = next(v for v in videos if v["slug"] == "2026-06-06_merkava_tank_blat_position")
    fig, ax = plt.subplots(figsize=(11, 4.4))
    ax.set_xlim(0, 11); ax.set_ylim(0, 4.6); ax.axis("off")

    panels = [
        ("Browse", "Gallery of every clip —\nsearch, sort, filter to the\nones with a 3-D scene", CYAN),
        ("Read the edit", "Auto-annotated timeline:\njump past banners &\nreplays to real flight", GOLD),
        ("Fly the strike", "Orbit the reconstructed\n3-D scene & measure\nright in the browser", GREEN),
    ]
    pw, ph, gap = 3.1, 2.4, 0.55
    y0 = 1.35
    x = 0.35
    for i, (title, body, col) in enumerate(panels):
        ax.add_patch(FancyBboxPatch((x, y0), pw, ph,
                     boxstyle="round,pad=0.02,rounding_size=0.08",
                     linewidth=1.6, edgecolor=col, facecolor=PANEL))
        # inner glyph (leave room for the title band at the top of the panel)
        if i == 0:
            draw_gallery(ax, x + 0.18, y0 + 0.22, pw - 0.36, ph - 0.85)
        elif i == 1:
            draw_timeline(ax, x + 0.22, y0 + 0.35, pw - 0.44, 1.2, ex["segments"])
        else:
            draw_scene(ax, x + pw / 2, y0 + ph / 2 - 0.25, 0.46)
        ax.text(x + pw / 2, y0 + ph - 0.06, title, ha="center", va="top",
                color=col, fontsize=12.5, fontweight="bold")
        ax.text(x + pw / 2, 0.98, body, ha="center", va="top",
                color="#c3cad3", fontsize=8.8, linespacing=1.35)
        if i < 2:
            ax.add_patch(FancyArrowPatch((x + pw + 0.06, y0 + ph / 2),
                         (x + pw + gap - 0.06, y0 + ph / 2), arrowstyle="-|>",
                         mutation_scale=15, color=MUTED, linewidth=1.6))
        x += pw + gap
    ax.text(0.35, 4.4, "One dataset, three ways to look at it",
            color=TXT, fontsize=13.5, fontweight="bold")
    fig.savefig(os.path.join(OUT, "tool_flow.png"), dpi=150, facecolor=BG,
                bbox_inches="tight")
    plt.close(fig)
    print("tool_flow.png")


def fig_annotated_clip(videos):
    ex = next(v for v in videos if v["slug"] == "2026-06-06_merkava_tank_blat_position")
    segs = ex["segments"]
    times = [s["time"] for s in segs]
    T = times[-1] + 3.0
    fig, ax = plt.subplots(figsize=(10, 3.1))
    ax.set_xlim(0, T); ax.set_ylim(0, 1); ax.axis("off")

    # title (top) ; legend (just under it) ; ribbon (middle) ; ticks (bottom)
    ax.text(0, 0.95,
            "One clip, annotated:  Merkava tank, Blat  (2026-06-06)",
            color=TXT, fontsize=12.5, fontweight="bold")

    y, h = 0.30, 0.30
    seen = {}
    for i, s in enumerate(segs):
        t0 = times[i]
        t1 = times[i + 1] if i + 1 < len(segs) else T
        label, col = SEG.get(s["type"], ("Other", MUTED))
        ax.add_patch(Rectangle((t0, y), t1 - t0, h, facecolor=col,
                     edgecolor=BG, linewidth=1.2))
        seen[label] = col
    # time axis ticks every 15s
    for tt in range(0, int(T) + 1, 15):
        ax.plot([tt, tt], [y - 0.05, y], color=MUTED, lw=1)
        ax.text(tt, y - 0.11, f"{tt}s", ha="center", va="top",
                color=MUTED, fontsize=9)
    # legend row
    order = ["Flight", "Pause/freeze", "Replay", "Banner", "Other"]
    lx = 0
    for lab in order:
        if lab not in seen:
            continue
        ax.add_patch(Rectangle((lx, 0.71), T * 0.022, 0.07,
                     facecolor=seen[lab], edgecolor="none"))
        ax.text(lx + T * 0.03, 0.745, lab, va="center", color="#c3cad3",
                fontsize=9.5)
        lx += T * (0.03 + 0.0085 * len(lab) + 0.045)
    fig.savefig(os.path.join(OUT, "annotated_clip.png"), dpi=150, facecolor=BG,
                bbox_inches="tight")
    plt.close(fig)
    print("annotated_clip.png  span %.0fs" % T)


def fig_footage_breakdown(videos):
    dur = Counter()
    for v in videos:
        segs = v.get("segments") or []
        for i in range(len(segs) - 1):
            length = segs[i + 1]["time"] - segs[i]["time"]
            if length > 0:
                dur[SEG.get(segs[i]["type"], ("Other", MUTED))[0]] += length
    total = sum(dur.values())
    order = ["Flight", "Pause/freeze", "Replay", "Banner", "Other"]
    order = [k for k in order if k in dur]
    vals = [dur[k] for k in order]
    cols = [SEG_COLOR(k) for k in order]

    fig, ax = plt.subplots(figsize=(10, 2.5))
    ax.set_xlim(0, total); ax.set_ylim(0, 1); ax.axis("off")
    x = 0
    for k, v, c in zip(order, vals, cols):
        ax.add_patch(Rectangle((x, 0.42), v, 0.34, facecolor=c,
                     edgecolor=BG, linewidth=1.4))
        pct = 100 * v / total
        if pct > 4:
            ax.text(x + v / 2, 0.59, f"{k}\n{pct:.0f}%", ha="center",
                    va="center", color="#04070c" if c in (CYAN, GOLD) else TXT,
                    fontsize=10, fontweight="bold", linespacing=1.15)
        x += v
    ax.text(0, 0.90,
            "Where the seconds go across all annotated footage",
            color=TXT, fontsize=12.5, fontweight="bold")
    ax.text(0, 0.14,
            f"{total/3600:.1f} hours of annotated footage · barely half is actual flight — "
            "the rest is banners, freezes and replays the editor added",
            color=MUTED, fontsize=9.5)
    fig.savefig(os.path.join(OUT, "footage_breakdown.png"), dpi=150,
                facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print("footage_breakdown.png  flight=%.0f%% total=%.0fs" %
          (100 * dur["Flight"] / total, total))


def SEG_COLOR(label):
    for _, (lab, col) in SEG.items():
        if lab == label:
            return col
    return MUTED


def fig_social(videos):
    n = len(videos)
    n3d = sum(1 for v in videos if v.get("scenePath"))
    towns = len({v.get("town") for v in videos if v.get("town")})
    ex = next(v for v in videos if v["slug"] == "2026-06-06_merkava_tank_blat_position")

    fig = plt.figure(figsize=(12, 6.3), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.set_xlim(0, 12); ax.set_ylim(0, 6.3)

    # right side: a scene glyph + a small annotation ribbon under it
    draw_scene(ax, 9.05, 3.9, 0.62)
    draw_timeline(ax, 7.4, 1.15, 3.3, 0.8, ex["segments"])

    ax.text(0.62, 5.35, "Explore the FPV", color=TXT, fontsize=33,
            fontweight="bold")
    ax.text(0.62, 4.55, "strike dataset", color=CYAN, fontsize=33,
            fontweight="bold")
    ax.text(0.62, 3.55,
            "Browse every clip, read the propaganda\n"
            "edit, and orbit the real 3-D attack path —\n"
            "right in the browser.",
            color="#cdd3dc", fontsize=15, va="top", linespacing=1.5)

    # real stat chips
    chips = [(f"{n}", "clips"), (f"{n3d}", "3-D scenes"), (f"{towns}", "towns")]
    cx = 0.62
    for big, small in chips:
        w = 0.55 + 0.36 * len(big)
        ax.add_patch(FancyBboxPatch((cx, 1.05), w, 1.05,
                     boxstyle="round,pad=0.04,rounding_size=0.12",
                     linewidth=1.4, edgecolor="#2b323c", facecolor=PANEL))
        ax.text(cx + w / 2, 1.72, big, ha="center", va="center", color=GOLD,
                fontsize=22, fontweight="bold")
        ax.text(cx + w / 2, 1.32, small, ha="center", va="center",
                color=MUTED, fontsize=11)
        cx += w + 0.35

    ax.text(0.62, 0.42, "itamar-weiss.com/fpv", color=GOLD, fontsize=13)
    fig.savefig(os.path.join(OUT, "social.png"), dpi=100, facecolor=BG)
    plt.close(fig)
    print(f"social.png  ({n} clips, {n3d} 3D, {towns} towns)")


if __name__ == "__main__":
    videos = load()
    fig_tool_flow(videos)
    fig_annotated_clip(videos)
    fig_footage_breakdown(videos)
    fig_social(videos)
