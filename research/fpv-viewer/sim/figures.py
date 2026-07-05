"""
Figures for the FPV *viewer* post (the interactive explorer at /fpv), distinct
from the dataset post's figures.

  - tool_flow.png        : qualitative schematic of the three views the tool gives
                           you (gallery -> annotated player -> 3-D scene). Concept
                           diagram, no numeric axes.
  - annotated_clip.png   : REAL flight-annotation timeline of one clip
                           (2026-06-06 Merkava tank, Blat), straight from the
                           dataset's segment markers. Shows how much of a
                           clip is banner / replay / pause vs. flight.
  - footage_breakdown.png: REAL — of all annotated footage across the dataset,
                           how the seconds split by segment type. Durations are
                           summed from consecutive segment boundaries (the final,
                           open-ended segment of each clip is excluded because the
                           clip end time isn't in the manifest).
  - social.png           : 1200x630 OpenGraph card for the post.

All counts/durations are REAL, computed from ../2026-07-05_videos_snapshot.json
(a frozen copy of public/fpv/data/videos.json; the live one keeps growing).
Inside the tool_flow schematic, the gallery cards and the small timeline are
illustrative stand-ins (the timeline uses real segment boundaries); the 3-D
scene panel is a REAL screenshot of the viewer
(../assets/biranit_scene_capture.png).
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

# segment type -> (display label, colour). "flight" is the signal (the one
# saturated colour); the rest is editing on top of the footage and stays in a
# muted family. All colours were checked against the black surface with the
# dataviz palette validator (>=3:1 contrast, CVD-separable with labels+gaps).
SEG = {
    "flight_start":     ("Flight",     CYAN),
    "new_flight_start": ("Flight",     CYAN),
    "banner_start":     ("Banner",     MUTED),
    "replay_start":     ("Replay",     PURPLE),
    "pause_start":      ("Pause/freeze", "#5b6675"),
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


def draw_scene_capture(ax, x0, y0, w, h):
    """A REAL screenshot of the scene viewer (the Biranit / Iron Dome strike),
    cropped and fitted inside the panel with rounded corners."""
    from PIL import Image
    cap = Image.open(os.path.join(HERE, "..", "assets",
                                  "biranit_scene_capture.png")).convert("RGB")
    cap = cap.crop((240, 55, 1040, 400))   # drop dead space & the UI button
    ar = cap.width / cap.height
    dw, dh = (w, w / ar) if ar > w / h else (h * ar, h)
    ex0, ey0 = x0 + (w - dw) / 2, y0 + (h - dh) / 2
    im = ax.imshow(np.asarray(cap) / 255.0,
                   extent=[ex0, ex0 + dw, ey0, ey0 + dh],
                   aspect="auto", zorder=2, interpolation="lanczos")
    clip = FancyBboxPatch((ex0, ey0), dw, dh,
                          boxstyle="round,pad=0,rounding_size=0.05",
                          transform=ax.transData,
                          facecolor="none", edgecolor="none")
    ax.add_patch(clip)
    im.set_clip_path(clip)


# --------------------------------------------------------------------------
def fig_tool_flow(videos):
    ex = next(v for v in videos if v["slug"] == "2026-06-06_merkava_tank_blat_position")
    fig, ax = plt.subplots(figsize=(11, 4.4))
    ax.set_xlim(0, 11); ax.set_ylim(0, 4.6); ax.axis("off")

    panels = [
        ("Browse", "Gallery of every clip —\nsearch, sort, filter to the\nones with a 3-D scene", CYAN),
        ("Read the edit", "Auto-annotated timeline:\njump past banners &\nreplays to real flight", GOLD),
        ("Debrief the strike", "Replay the reconstructed\n3-D scene, measure it, and\nlearn how it unfolded", GREEN),
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
            draw_scene_capture(ax, x + 0.18, y0 + 0.22, pw - 0.36, ph - 0.85)
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


# ---- shared helpers for the two "breakdown" charts ------------------------
# Both charts use an axes that maps 1 data unit = 1 inch in x AND y, so the
# rounded corners of FancyBboxPatch come out circular instead of squashed.

def inch_axes(fig_w, fig_h):
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w); ax.set_ylim(0, fig_h); ax.axis("off")
    return fig, ax


def text_w(fig, ax, s, fontsize, fontweight="normal"):
    """Measured width of a string, in inches (== data units here)."""
    t = ax.text(0, -5, s, fontsize=fontsize, fontweight=fontweight)
    fig.canvas.draw()
    w = t.get_window_extent().width / fig.dpi
    t.remove()
    return w


def seg_patch(ax, x, y, w, h, color, gap=0.028, rs=0.045):
    """One rounded timeline/bar segment with a small breathing gap around it."""
    x, w = x + gap / 2, max(w - gap, 0.02)
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={min(rs, 0.49 * w)}",
        linewidth=0, facecolor=color))


def legend_swatch(fig, ax, x, y, label, color, fontsize=9.5, color_txt="#c3cad3"):
    """Rounded swatch + label; returns the x where the next item can start."""
    sw, sh = 0.17, 0.11
    ax.add_patch(FancyBboxPatch((x, y - sh / 2), sw, sh,
                 boxstyle="round,pad=0,rounding_size=0.03",
                 linewidth=0, facecolor=color))
    ax.text(x + sw + 0.07, y, label, va="center", color=color_txt,
            fontsize=fontsize)
    return x + sw + 0.07 + text_w(fig, ax, label, fontsize) + 0.32


def fig_annotated_clip(videos):
    ex = next(v for v in videos if v["slug"] == "2026-06-06_merkava_tank_blat_position")
    segs = ex["segments"]
    times = [s["time"] for s in segs]
    T = times[-1] + 3.0

    W, H = 10.0, 3.3
    M = 0.55                       # side margin, inches
    BW = W - 2 * M                 # ribbon width
    fig, ax = inch_axes(W, H)

    def X(t):                      # seconds -> inches
        return M + BW * t / T

    # title
    ax.text(M, H - 0.42, "One clip, annotated", color=TXT, fontsize=13.5,
            fontweight="bold")
    ax.text(M + text_w(fig, ax, "One clip, annotated", 13.5, "bold") + 0.14,
            H - 0.42, "—  Merkava tank, Blat · 2026-06-06", color=MUTED,
            fontsize=11)

    # ribbon — merge consecutive same-label markers (the data sometimes has
    # e.g. two banner_start boundaries in a row) so each visual segment is one
    # patch and the callouts measure the real span
    seg_spans = []                 # (t0, t1, label)
    for i, s in enumerate(segs):
        t0 = times[i]
        t1 = times[i + 1] if i + 1 < len(segs) else T
        label = SEG.get(s["type"], ("Other", MUTED))[0]
        if seg_spans and seg_spans[-1][2] == label:
            seg_spans[-1] = (seg_spans[-1][0], t1, label)
        else:
            seg_spans.append((t0, t1, label))
    ry, rh = 1.18, 0.62
    seen = {}
    for t0, t1, label in seg_spans:
        col = SEG_COLOR(label)
        seg_patch(ax, X(t0), ry, BW * (t1 - t0) / T, rh, col)
        seen[label] = col

    # story callouts above the ribbon (thin leaders, staggered heights)
    def callout(t0, t1, text, y_text, ha):
        cx = X((t0 + t1) / 2)
        ax.plot([cx, cx], [ry + rh + 0.05, y_text - 0.10], color="#39404b",
                lw=0.9)
        tx = {"left": max(cx - 0.05, M), "center": cx,
              "right": min(cx + 0.05, M + BW)}[ha]
        ax.text(tx, y_text, text, ha=ha, va="bottom", color=MUTED,
                fontsize=9, style="italic")
    banners = [s for s in seg_spans if s[2] == "Banner"]
    pauses = [s for s in seg_spans if s[2] == "Pause/freeze"]
    replays = [s for s in seg_spans if s[2] == "Replay"]
    if banners:
        b = banners[0]
        callout(b[0], b[1], f"{b[1] - b[0]:.0f}-second banner", ry + rh + 0.22,
                "left")
    if pauses:
        p = max(pauses, key=lambda s: s[1] - s[0])
        callout(p[0], p[1], "freeze at impact", ry + rh + 0.48, "center")
    if replays:
        r = replays[-1]
        callout(r[0], r[1], "slow-mo replay", ry + rh + 0.22, "right")

    # time axis: hairline baseline + ticks every 15 s
    ax.plot([M, M + BW], [ry - 0.09, ry - 0.09], color="#262c35", lw=1.0)
    for tt in range(0, int(T) + 1, 15):
        ax.plot([X(tt), X(tt)], [ry - 0.09, ry - 0.16], color="#3a424e", lw=1.0)
        ax.text(X(tt), ry - 0.24, f"{tt}s", ha="center", va="top",
                color=MUTED, fontsize=8.5)

    # legend row (bottom, under the axis)
    order = ["Flight", "Pause/freeze", "Replay", "Banner", "Other"]
    lx = M
    for lab in order:
        if lab in seen:
            lx = legend_swatch(fig, ax, lx, 0.36, lab, seen[lab])

    fig.savefig(os.path.join(OUT, "annotated_clip.png"), dpi=150, facecolor=BG)
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

    W, H = 10.0, 3.3
    M = 0.55
    BW = W - 2 * M
    fig, ax = inch_axes(W, H)

    # title + total
    ax.text(M, H - 0.42, "Where the seconds go", color=TXT, fontsize=13.5,
            fontweight="bold")
    ax.text(M + text_w(fig, ax, "Where the seconds go", 13.5, "bold") + 0.14,
            H - 0.42,
            f"—  all annotated footage, {total/3600:.1f} hours",
            color=MUTED, fontsize=11)

    # one proportional bar with rounded segments and gaps
    by, bh = 1.22, 0.60
    x = M
    for k, v, c in zip(order, vals, cols):
        w = BW * v / total
        seg_patch(ax, x, by, w, bh, c)
        pct = 100 * v / total
        if pct > 10:   # big segments carry their share directly
            ax.text(x + w / 2, by + bh / 2, f"{pct:.0f}%", ha="center",
                    va="center", fontsize=11.5, fontweight="bold",
                    color="#04141d" if c == CYAN else "#0b0e13")
        x += w

    # the story, as two brackets over the bar: flight vs. everything else
    fw = BW * dur["Flight"] / total
    def bracket(x0, x1, label, col, y=by + bh + 0.17):
        ax.plot([x0 + 0.02, x1 - 0.02], [y, y], color=col, lw=1.1)
        for xe in (x0 + 0.02, x1 - 0.02):
            ax.plot([xe, xe], [y, y - 0.07], color=col, lw=1.1)
        ax.text((x0 + x1) / 2, y + 0.09, label, ha="center", va="bottom",
                color=col, fontsize=9.8)
    bracket(M, M + fw, f"actual flight — {100*dur['Flight']/total:.0f}%", CYAN)
    bracket(M + fw, M + BW,
            f"added in the edit — {100*(total-dur['Flight'])/total:.0f}%",
            MUTED)

    # value row: every type, even the slivers too small to label in the bar
    lx = M
    for k, v, c in zip(order, vals, cols):
        lab = f"{k} {100*v/total:.0f}% · {v/60:.0f} min"
        lx = legend_swatch(fig, ax, lx, 0.62, lab, c)

    fig.savefig(os.path.join(OUT, "footage_breakdown.png"), dpi=150,
                facecolor=BG)
    plt.close(fig)
    print("footage_breakdown.png  flight=%.0f%% total=%.0fs" %
          (100 * dur["Flight"] / total, total))


def SEG_COLOR(label):
    for _, (lab, col) in SEG.items():
        if lab == label:
            return col
    return MUTED


def fig_social(videos):
    """1200x630 OG card built around a REAL capture of the viewer's 3-D scene
    for the Biranit / Iron Dome strike (../assets/biranit_scene_capture.png,
    a screenshot of the live scene viewer). Text sits over a left scrim."""
    from PIL import Image
    W, H = 1200, 630
    cap = os.path.join(HERE, "..", "assets", "biranit_scene_capture.png")
    img = Image.open(cap).convert("RGB")
    # cover-crop the capture to fill the whole card
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    l = (img.width - W) // 2
    t = (img.height - H) // 2
    arr = np.asarray(img.crop((l, t, l + W, t + H))) / 255.0

    fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor="#050607")
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.imshow(arr, extent=[0, 1, 0, 1], aspect="auto", zorder=0)

    # left-to-right black scrim so the title stays legible over the render
    ramp = np.clip(np.linspace(0.92, -0.35, W), 0, 1)
    scrim = np.zeros((2, W, 4)); scrim[:, :, 3] = ramp
    ax.imshow(scrim, extent=[0, 1, 0, 1], aspect="auto", zorder=1)
    # slim bottom scrim for the footer line (alpha strongest at the bottom row)
    bot = np.zeros((H, 2, 4))
    bot[:, :, 3] = np.clip(np.linspace(-0.2, 0.55, H), 0, 1)[:, None]
    ax.imshow(bot, extent=[0, 1, 0, 1], aspect="auto", zorder=1)

    T = dict(transform=ax.transAxes, zorder=3)
    ax.text(0.045, 0.83, "Explore the FPV", color="#ffffff", fontsize=35,
            fontweight="bold", **T)
    ax.text(0.045, 0.70, "strike dataset", color=CYAN, fontsize=35,
            fontweight="bold", **T)
    ax.text(0.045, 0.55,
            "Browse the gallery, read each clip's\n"
            "flight edit, and orbit the reconstructed\n"
            "3-D attack path — in the browser.",
            color="#e2e7ec", fontsize=15.5, va="top", linespacing=1.55, **T)
    ax.text(0.045, 0.075, "itamar-weiss.com/fpv", color=GOLD, fontsize=14, **T)
    ax.text(0.972, 0.055,
            "Reconstructed 3-D scene · Iron Dome platform, “Biranit”",
            color="#cfd5dd", fontsize=10.5, ha="right", **T)

    fig.savefig(os.path.join(OUT, "social.png"), dpi=100, facecolor="#050607")
    plt.close(fig)
    print("social.png (real Biranit scene capture)")


if __name__ == "__main__":
    videos = load()
    fig_tool_flow(videos)
    fig_annotated_clip(videos)
    fig_footage_breakdown(videos)
    fig_social(videos)
