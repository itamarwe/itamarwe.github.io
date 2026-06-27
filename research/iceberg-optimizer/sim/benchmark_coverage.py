#!/usr/bin/env python3
"""
Benchmark coverage map for the Iceberg Optimizer Skill.
22 scenarios in 7 categories, displayed as one row per category.
"""

from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE   = Path(__file__).parent
OUTPUT = HERE.parents[2] / 'public' / 'img' / 'iceberg-optimizer' / 'benchmark_coverage.png'
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# ── palette ──────────────────────────────────────────────────────────────────
BLACK  = '#000000'
CYAN   = '#3fc1ff'
GOLD   = '#ffd166'
GREEN  = '#7CFC8A'
PURPLE = '#b48cff'
RED    = '#ff5a5a'
ORANGE = '#ff9f43'
TEXT   = '#ededed'
MUTED  = '#8b95a5'

# ── data ─────────────────────────────────────────────────────────────────────
GROUPS = [
    ('Streaming & Flink',    CYAN,   ['streaming thin spread', 'flink micro commit', 'streaming death spiral']),
    ('CDC & Deletes',        ORANGE, ['position delete accum.', 'cdc high churn', 'snapshot time-travel cdc', 'gdpr deletes', 'gdpr ordering mistake']),
    ('Partitioning',         GOLD,   ['partition misalignment', 'over-partitioned', 'mixed partition spec', 'hot partition conflict', 'late arriving data']),
    ('Metadata & Snapshots', PURPLE, ['snapshot bloat only', 'format version mismatch']),
    ('Maintenance Safety',   RED,    ['orphan files before expiry']),
    ('Indexes',              GREEN,  ['bloom filter high-cardinality', 'bloom filter wrong column', 'z-order too many columns']),
    ('Cost & Lifecycle',     MUTED,  ['cold archive', 'query cost vs maint. cost', 'wide table memory pressure']),
]

# ── layout constants ──────────────────────────────────────────────────────────
W, H, DPI    = 1000, 390, 100
MARGIN_L     = 22
LABEL_W      = 175   # width of the category label area
PILL_W       = 135
PILL_H       = 26
PILL_GAP     = 6
ROW_H        = PILL_H + 14   # vertical spacing between rows
PILLS_X0     = MARGIN_L + LABEL_W + 10   # x where pills start

fig = plt.figure(figsize=(W / DPI, H / DPI), facecolor=BLACK)
ax  = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis('off')
ax.set_facecolor(BLACK)

# ── title ─────────────────────────────────────────────────────────────────────
ax.text(W / 2, H - 18, '22 Benchmark Scenarios — PASS 22/22 · avg 5.0 / 5',
        color=TEXT, fontsize=13, fontweight='bold', ha='center', va='center')

# thin rule under title
ax.plot([MARGIN_L, W - MARGIN_L], [H - 32, H - 32], color='#1c1c1c', linewidth=1)

# ── rows ──────────────────────────────────────────────────────────────────────
n_groups = len(GROUPS)
usable_h = H - 50   # space below the title rule
row_step = usable_h / n_groups

for i, (label, accent, scenarios) in enumerate(GROUPS):
    # row centre y (rows drawn top → bottom)
    cy = H - 44 - i * row_step - row_step / 2 + 4

    # accent bar on far left
    ax.add_patch(FancyBboxPatch((MARGIN_L, cy - PILL_H / 2 - 2), 4, PILL_H + 4,
        boxstyle='round,pad=1', facecolor=accent, edgecolor='none', alpha=0.9))

    # category label
    ax.text(MARGIN_L + 12, cy, label,
            color=accent, fontsize=9.5, fontweight='bold', ha='left', va='center')

    # scenario pills
    px = PILLS_X0
    for scenario in scenarios:
        ax.add_patch(FancyBboxPatch((px, cy - PILL_H / 2), PILL_W, PILL_H,
            boxstyle='round,pad=3',
            facecolor=accent + '14',   # ~8% opacity fill
            edgecolor=accent, linewidth=1, alpha=0.95))
        ax.text(px + PILL_W / 2, cy, scenario,
                color=TEXT, fontsize=7.5, ha='center', va='center', linespacing=1.3)
        px += PILL_W + PILL_GAP

    # row separator (very faint)
    sep_y = cy - row_step / 2
    if i < n_groups - 1:
        ax.plot([MARGIN_L, W - MARGIN_L], [sep_y, sep_y],
                color='#111111', linewidth=0.8)

# ── bottom summary ────────────────────────────────────────────────────────────
ax.text(W / 2, 10,
        'Each scenario exercises a distinct real-world failure mode — '
        'no duplicates, no synthetic data.',
        color='#3a4a5a', fontsize=8.5, ha='center', va='bottom', style='italic')

plt.savefig(str(OUTPUT), dpi=DPI, bbox_inches='tight', pad_inches=0.1, facecolor=BLACK)
print(f'Saved → {OUTPUT}')
