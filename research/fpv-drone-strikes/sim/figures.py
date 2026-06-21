"""
Dataset-overview figures for the FPV-drone-strikes post.

  - target_mix.png : what the enemy strikes — REAL counts parsed from the dataset
                     manifest snapshot (../2026-06-21_manifest_snapshot.tsv).
  - timeline.png   : cumulative documented strikes over time (REAL dates).
  - pipeline.png   : qualitative schematic of the video -> 3-D flight-path pipeline
                     (no numeric axes — it's a concept diagram).
  - social.png     : 1200x630 OpenGraph card.

Counts are real; the target buckets are a coarse hand-grouping of the manifest's
free-text slugs (see categorize()). Re-run after pulling a fresh manifest.
"""
import os, csv, datetime as dt, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "..", "2026-06-21_manifest_snapshot.tsv")
OUT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "public", "img", "fpv-drone-strikes"))
os.makedirs(OUT, exist_ok=True)

BG = "#000000"; TXT = "#ededed"; MUTED = "#8b95a5"
CYAN, GOLD, GREEN, RED, PURPLE = "#3fc1ff", "#ffd166", "#7CFC8A", "#ff5a5a", "#b48cff"

plt.rcParams.update({
    "figure.facecolor": BG, "savefig.facecolor": BG, "axes.facecolor": BG,
    "text.color": TXT, "axes.labelcolor": TXT, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.edgecolor": "#333a45", "font.size": 12,
})

def categorize(slug):
    s = slug.lower()
    if "merkava" in s or ("tank" in s and "anti" not in s):
        return "Merkava tanks"
    if "namer" in s:
        return "Namer APCs"
    if "humvee" in s or "hummer" in s:
        return "Humvees"
    if any(k in s for k in ["d9", "bulldozer", "excavator", "engineering", "digger"]):
        return "Engineering vehicles"
    if any(k in s for k in ["soldier", "troop", "personnel", "commander", "forces", "company"]):
        return "Personnel"
    if any(k in s for k in ["iron_dome", "launcher", "radar", "camera", "drone_control",
                            "anti_drone", "howitzer", "sholef", "communications",
                            "surveillance", "platform", "position", "command", "hq"]):
        return "Sensors, air-defense & positions"
    return "Other vehicles"

ORDER = ["Merkava tanks", "Personnel", "Namer APCs", "Engineering vehicles",
         "Humvees", "Sensors, air-defense & positions", "Other vehicles"]

def load():
    rows = []
    with open(MANIFEST) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            rows.append(r)
    return rows

def parse_dates(rows):
    ds = []
    for r in rows:
        try:
            ds.append(dt.date.fromisoformat(r["date"]))
        except Exception:
            pass
    return sorted(ds)

# --------------------------------------------------------------------------
def fig_target_mix(rows):
    from collections import Counter
    c = Counter(categorize(r["slug"]) for r in rows)
    cats = [k for k in ORDER if k in c]
    vals = [c[k] for k in cats]
    total = sum(c.values())
    colors = [RED, GOLD, "#ff8a5a", PURPLE, CYAN, GREEN, MUTED][:len(cats)]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    y = np.arange(len(cats))[::-1]
    ax.barh(y, vals, color=colors, height=0.66)
    for yi, v in zip(y, vals):
        ax.text(v + 0.4, yi, str(v), va="center", color=TXT, fontsize=12, fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels(cats, fontsize=12, color=TXT)
    ax.set_xlim(0, max(vals) + 4)
    ax.set_xlabel("documented strike videos")
    ax.set_title(f"What the FPV strikes target   ·   {total} videos, Apr–Jun 2026",
                 color=TXT, fontsize=13, loc="left")
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    ax.tick_params(length=0)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "target_mix.png"), dpi=150, facecolor=BG)
    plt.close(fig)
    print("target_mix.png", dict(zip(cats, vals)))

def fig_timeline(rows):
    ds = parse_dates(rows)
    d0, d1 = ds[0], ds[-1]
    days = [(d - d0).days for d in ds]
    span = (d1 - d0).days
    cum = np.arange(1, len(ds) + 1)
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.fill_between(days, cum, color=CYAN, alpha=0.18, step="post")
    ax.step(days, cum, where="post", color=CYAN, lw=2.2)
    ax.scatter(days, cum, s=10, color=CYAN, zorder=3)
    # month ticks
    ticks, labels = [], []
    cur = dt.date(d0.year, d0.month, 1)
    while cur <= d1:
        ticks.append((cur - d0).days)
        labels.append(cur.strftime("%b %-d"))
        cur = (cur.replace(day=28) + dt.timedelta(days=7)).replace(day=1)
    ax.set_xticks(ticks); ax.set_xticklabels(labels)
    ax.set_xlim(-1, span + 1); ax.set_ylim(0, len(ds) + 14)
    ax.set_ylabel("cumulative videos")
    ax.set_title("A constantly-growing log of documented strikes", color=TXT,
                 fontsize=13, loc="left")
    # label sits in the empty upper-left region, clear of the climbing curve
    ax.text(span * 0.03, len(ds) + 6,
            f"{d0.strftime('%b %-d')} → {d1.strftime('%b %-d')}, {d1.year}\nand still climbing",
            color=GOLD, fontsize=11, va="top", linespacing=1.4)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "timeline.png"), dpi=150, facecolor=BG)
    plt.close(fig)
    print("timeline.png", len(ds), "videos over", span, "days")

def fig_pipeline():
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 3); ax.axis("off")
    steps = [
        ("Strike video", "raw MP4:\ntitle cards +\nFPV footage", MUTED),
        ("Isolate FPV", "drop intros /\nlogos, sample\nclean frames", CYAN),
        ("VGGT", "feed-forward\n3-D transformer\n(one pass)", GOLD),
        ("Poses + cloud", "camera pose\nper frame +\ndense points", GREEN),
        ("Flight path", "camera centers\n= drone's 3-D\ntrajectory", RED),
    ]
    w, h, gap = 1.66, 1.7, 0.24
    x = 0.18
    for i, (title, body, col) in enumerate(steps):
        box = FancyBboxPatch((x, 0.7), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                             linewidth=1.6, edgecolor=col, facecolor="#0c0f14")
        ax.add_patch(box)
        ax.text(x + w / 2, 0.7 + h - 0.3, title, ha="center", va="center",
                color=col, fontsize=12, fontweight="bold")
        ax.text(x + w / 2, 0.7 + h / 2 - 0.28, body, ha="center", va="center",
                color=TXT, fontsize=9.2)
        if i < len(steps) - 1:
            ax.add_patch(FancyArrowPatch((x + w + 0.01, 0.7 + h / 2),
                                         (x + w + gap - 0.01, 0.7 + h / 2),
                                         arrowstyle="-|>", mutation_scale=16,
                                         color=MUTED, linewidth=1.6))
        x += w + gap
    ax.text(0.18, 2.72, "From a strike clip to a 3-D flight path",
            color=TXT, fontsize=13, fontweight="bold")
    fig.savefig(os.path.join(OUT, "pipeline.png"), dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print("pipeline.png")

def fig_social():
    """1200x630 card built around the real reconstruction hero, if present."""
    from matplotlib.image import imread
    fig = plt.figure(figsize=(12, 6.3), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_facecolor(BG)
    hero = os.path.join(OUT, "reconstruction_hero.png")
    if os.path.exists(hero):
        img = imread(hero)
        iax = fig.add_axes([0.44, 0.05, 0.55, 0.9]); iax.axis("off")
        iax.imshow(img)
    ax.text(0.05, 0.82, "FPV drone strikes,", color=TXT, fontsize=27,
            fontweight="bold", transform=ax.transAxes)
    ax.text(0.05, 0.71, "as an open dataset", color=CYAN, fontsize=27,
            fontweight="bold", transform=ax.transAxes)
    ax.text(0.05, 0.57, "95+ documented Hezbollah\nstrike videos — and what\nyou can pull from one:\n"
            "a real 3-D flight path,\nstraight from the footage.",
            color=MUTED, fontsize=14, transform=ax.transAxes, va="top", linespacing=1.55)
    ax.text(0.05, 0.08, "itamar-weiss.com", color=GOLD, fontsize=13,
            transform=ax.transAxes)
    fig.savefig(os.path.join(OUT, "social.png"), dpi=100, facecolor=BG)
    plt.close(fig)
    print("social.png")

if __name__ == "__main__":
    rows = load()
    fig_target_mix(rows)
    fig_timeline(rows)
    fig_pipeline()
    fig_social()
