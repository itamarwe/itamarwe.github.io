"""Generate the catalog charts and schematic figures for the FPV-drone-strikes post."""

import argparse
from collections import Counter
from datetime import date, timedelta
import json
import os
from pathlib import Path
import re
from urllib.request import urlopen

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.ticker import MaxNLocator

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG_REVISION = "20b7f30e44648dcd703628eadb4ce733e0a3465b"
CATALOG_URL = (
    "https://raw.githubusercontent.com/itamarwe/fpv-drone-strikes-lebanon-dataset/"
    f"{CATALOG_REVISION}/data/catalog.json"
)
OUT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "public", "img", "fpv-drone-strikes"))
os.makedirs(OUT, exist_ok=True)

BG = "#000000"; TXT = "#ededed"; MUTED = "#8b95a5"
CYAN, GOLD, GREEN, RED, PURPLE = "#3fc1ff", "#ffd166", "#7CFC8A", "#ff5a5a", "#b48cff"

plt.rcParams.update({
    "figure.facecolor": BG, "savefig.facecolor": BG, "axes.facecolor": BG,
    "text.color": TXT, "axes.labelcolor": TXT, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.edgecolor": "#333a45", "font.size": 12,
})

# Match the target phrase before the first comma, which usually introduces
# the location. The specific target and mixed-target rules precede broader ones.
TARGET_GROUPS = (
    ("Mixed targets", r"^israeli army vehicles and soldiers|^soldier gathering \+|"
                      r"^soldiers' position and"),
    ("Tanks", r"\btanks?\b"),
    ("Namer APCs", r"\bnamers?\b|\bnamera\b"),
    ("Humvees", r"\b(?:humvees?|hummers?)\b"),
    ("Engineering vehicles", r"\b(?:d9|bulldozers?|excavators?|engineering vehicles?)\b"),
    ("Air defense, sensors & equipment",
     r"\b(?:iron dome|radar|camera|drone control system|counter-drone system|"
     r"communications (?:system|equipment)|technical equipment)\b"),
    ("Other vehicles", r"\b(?:vehicles?|tankers?|troop carriers?|apcs?)\b"),
    ("Positions & facilities",
     r"\b(?:positions?|positioning|logistics point|tent|house|command center|command room|hq)\b"),
    ("Personnel", r"\b(?:soldiers?|personnel|forces?)\b"),
)


def categorize(description):
    target = description.split(",", 1)[0].lower()
    for category, pattern in TARGET_GROUPS:
        if re.search(pattern, target):
            return category
    return "Unclassified"


def load_catalog(path):
    if path is None:
        with urlopen(CATALOG_URL, timeout=30) as response:
            return json.load(response)["videos"]
    return json.loads(path.read_text(encoding="utf-8"))["videos"]


def format_date(day):
    return f"{day:%b} {day.day}"


def fig_target_mix(rows):
    counts = Counter(categorize(row["description"]) for row in rows)
    categories, values = zip(*counts.most_common())
    positions = range(len(categories))
    colors = [RED, GOLD, CYAN, GREEN, PURPLE, "#ff8a5a", "#8cb5ff", "#64dace", MUTED]

    fig, ax = plt.subplots(figsize=(8, 5.1))
    ax.barh(positions, values, color=colors[:len(categories)], height=0.64)
    for position, value in zip(positions, values):
        ax.text(value + 0.6, position, str(value), va="center", fontsize=14, fontweight="bold")
    labels = [category.replace("sensors & equipment", "sensors\n& equipment")
              for category in categories]
    ax.set_yticks(positions, labels, fontsize=14, color=TXT)
    ax.invert_yaxis()
    ax.set_xlim(0, max(values) * 1.14)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel("Cataloged videos", fontsize=13)
    fig.suptitle(f"Targets named in the catalog  ·  {len(rows)} videos",
                 x=0.025, y=0.965, ha="left", fontsize=16)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(length=0)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(os.path.join(OUT, "target_mix.png"), dpi=150, facecolor=BG)
    plt.close(fig)
    print("target_mix.png", dict(counts.most_common()))


def fig_timeline(rows):
    daily = Counter(date.fromisoformat(row["date"]) for row in rows)
    dates = sorted(daily)
    first, last = dates[0], dates[-1]
    start = first - timedelta(days=1)
    cumulative = [0]
    for day in dates:
        cumulative.append(cumulative[-1] + daily[day])

    fig, ax = plt.subplots(figsize=(8, 3.9))
    ax.fill_between([start, *dates], cumulative, color=CYAN, alpha=0.18, step="post")
    ax.step([start, *dates], cumulative, where="post", color=CYAN, lw=2.2)
    ax.scatter(last, cumulative[-1], s=30, color=CYAN, zorder=3)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
    ax.set_xlim(start, last + timedelta(days=3))
    ax.set_ylim(0, len(rows) * 1.12)
    ax.set_ylabel("Cumulative videos", fontsize=13)
    ax.set_title("Cumulative videos by catalog date", fontsize=15, loc="left", pad=12)
    ax.text(0.03, 0.94,
            f"{len(rows)} videos\n{format_date(first)} – {format_date(last)}, {last.year}",
            transform=ax.transAxes, color=GOLD, fontsize=13, va="top", linespacing=1.4)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "timeline.png"), dpi=150, facecolor=BG)
    plt.close(fig)
    print("timeline.png", len(rows), "videos,", first, "through", last)


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
    """1200x630 card built around a real FPV strike-video frame (it's about the
    dataset, not the path extraction)."""
    import glob
    from matplotlib.image import imread
    fig = plt.figure(figsize=(12, 6.3), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_facecolor(BG)
    # a representative frame from the dataset: the target in view, late approach
    frames = sorted(glob.glob(os.path.join(HERE, "..", "vggt", "frames2", "*.jpg")))
    if not frames:
        frames = sorted(glob.glob(os.path.join(HERE, "..", "vggt", "frames", "*.jpg")))
    if frames:
        img = imread(frames[int(0.86 * (len(frames) - 1))])
        iax = fig.add_axes([0.46, 0.08, 0.51, 0.84]); iax.axis("off")
        iax.imshow(img)
        for s in iax.spines.values():
            s.set_visible(True); s.set_color("#333a45")
    ax.text(0.05, 0.83, "FPV drone strikes", color=TXT, fontsize=26,
            fontweight="bold", transform=ax.transAxes)
    ax.text(0.05, 0.73, "on the IDF, as a dataset", color=CYAN, fontsize=20,
            fontweight="bold", transform=ax.transAxes)
    ax.text(0.05, 0.58, "An open, constantly-updated\nOSINT collection of\nHezbollah FPV drone-strike\n"
            "videos — targets, methods,\nand the paths they fly.",
            color="#cdd3dc", fontsize=14, transform=ax.transAxes, va="top", linespacing=1.6)
    ax.text(0.05, 0.08, "itamar-weiss.com", color=GOLD, fontsize=13,
            transform=ax.transAxes)
    fig.savefig(os.path.join(OUT, "social.png"), dpi=100, facecolor=BG)
    plt.close(fig)
    print("social.png")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, help="Use a local catalog.json instead of the pinned snapshot.")
    parser.add_argument("--charts-only", action="store_true", help="Render only target_mix.png and timeline.png.")
    args = parser.parse_args()

    rows = load_catalog(args.catalog)
    fig_target_mix(rows)
    fig_timeline(rows)
    if not args.charts_only:
        fig_pipeline()
        fig_social()
