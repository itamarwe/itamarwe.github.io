#!/usr/bin/env python3
"""
Phase-flow diagram for the Iceberg Optimizer Skill.
Shows the 6 phases (0-5) as a two-row flow with connecting arrows.
"""

from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE   = Path(__file__).parent
OUTPUT = HERE.parents[2] / 'public' / 'img' / 'iceberg-optimizer' / 'phases_flow.png'
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# ── palette ──────────────────────────────────────────────────────────────────
BLACK  = '#000000'
CYAN   = '#3fc1ff'
GOLD   = '#ffd166'
GREEN  = '#7CFC8A'
PURPLE = '#b48cff'
RED    = '#ff5a5a'
TEXT   = '#ededed'
MUTED  = '#8b95a5'
DIM    = '#1c1c1c'

W, H, DPI = 1000, 420, 100

phases = [
    # (num, name, subtitle, accent_color, lines)
    ('0', 'Scope &\nSafety', 'Identify table, engine\n& access mode\nRead-only until Phase 5',
     MUTED, '#111111'),
    ('1', 'Profile', 'Extract file-size health\nsnapshot bloat\ndelete pressure',
     CYAN, '#061318'),
    ('2', 'Reconstruct', 'Derive write cadence\nquery access patterns\n+ owner interview',
     '#60d0ff', '#061318'),
    ('3', 'Decide', 'Apply decision gates\nrank actions across\nlayout · ingest · maint.',
     GOLD, '#131000'),
    ('4', 'Simulate', 'Model 5 scenarios\nDo-nothing → Storage-min\nacross 4 cost axes',
     GREEN, '#041004'),
    ('5', 'Plan', 'Engine-specific commands\nwith schedules &\nmonitoring thresholds',
     PURPLE, '#0d0814'),
]

# Layout: two rows of 3
#  Row 1: phases 0, 1, 2  (left → right)
#  Row 2: phases 3, 4, 5  (left → right, connected from row1 end)
BOX_W, BOX_H = 260, 140
GAP_X, GAP_Y = 50, 60
MARGIN_X, MARGIN_Y = 50, 50
ROW2_Y = MARGIN_Y + BOX_H + GAP_Y

# centres: row1 left-to-right, row2 left-to-right
def box_pos(col, row):
    x = MARGIN_X + col * (BOX_W + GAP_X)
    y = MARGIN_Y + row * (BOX_H + GAP_Y)
    return x, y   # bottom-left corner

fig = plt.figure(figsize=(W / DPI, H / DPI), facecolor=BLACK)
ax  = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis('off')
ax.set_facecolor(BLACK)

def draw_box(ax, bx, by, num, name, subtitle, accent, bg):
    """Draw one phase box."""
    # background
    box = FancyBboxPatch((bx, by), BOX_W, BOX_H,
        boxstyle='round,pad=6', facecolor=bg, edgecolor=accent, linewidth=2, zorder=3)
    ax.add_patch(box)

    # phase number badge (top-left)
    badge = FancyBboxPatch((bx + 10, by + BOX_H - 32), 34, 24,
        boxstyle='round,pad=3', facecolor=accent, edgecolor='none', zorder=4)
    ax.add_patch(badge)
    ax.text(bx + 27, by + BOX_H - 20, num,
        color=BLACK, fontsize=11, fontweight='bold', ha='center', va='center', zorder=5)

    # phase name
    cx = bx + BOX_W / 2
    ax.text(cx, by + BOX_H - 22, name,
        color=accent, fontsize=13, fontweight='bold', ha='center', va='top',
        linespacing=1.25, zorder=4)

    # subtitle
    ax.text(cx, by + 10, subtitle,
        color=MUTED, fontsize=8.5, ha='center', va='bottom',
        linespacing=1.4, zorder=4)

def arrow(ax, x0, y0, x1, y1, color=MUTED):
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
        arrowprops=dict(arrowstyle='->', color=color, lw=1.8),
        zorder=2)

# Row 1: phases 0, 1, 2
for col in range(3):
    ph = phases[col]
    bx, by = box_pos(col, 1)
    draw_box(ax, bx, by, *ph)
    if col < 2:
        arrow(ax, bx + BOX_W + 4, by + BOX_H / 2,
                  bx + BOX_W + GAP_X - 4, by + BOX_H / 2)

# Row 2: phases 3, 4, 5
for col in range(3):
    ph = phases[col + 3]
    bx, by = box_pos(col, 0)
    draw_box(ax, bx, by, *ph)
    if col < 2:
        arrow(ax, bx + BOX_W + 4, by + BOX_H / 2,
                  bx + BOX_W + GAP_X - 4, by + BOX_H / 2)

# Down-arrow from phase 2 (row1 rightmost) to phase 3 (row2 leftmost)
# Phase 2 bottom-right → go right → go down → phase 3 top-left
r1_bx, r1_by = box_pos(2, 1)   # phase 2 box
r2_bx, r2_by = box_pos(0, 0)   # phase 3 box

# elbow: right side of phase-2 → right edge → down → left edge → top of phase-3
elbow_x = r1_bx + BOX_W + GAP_X / 2
ax.annotate('', xy=(r2_bx + BOX_W / 2, r2_by + BOX_H + 4),
    xytext=(r1_bx + BOX_W / 2, r1_by - 4),
    arrowprops=dict(arrowstyle='->', color=MUTED, lw=1.8,
        connectionstyle='arc3,rad=0'), zorder=2)

# "observe → ask → simulate → recommend" mantra below
ax.text(W / 2, 12,
    'observe before you ask  ·  ask before you decide  ·  simulate before you recommend',
    color='#3a4a5a', fontsize=9, ha='center', va='bottom', style='italic')

plt.savefig(str(OUTPUT), dpi=DPI, bbox_inches='tight', pad_inches=0.1, facecolor=BLACK)
print(f'Saved → {OUTPUT}')
