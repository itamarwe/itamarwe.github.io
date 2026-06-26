#!/usr/bin/env python3
"""
Social card (1200×630) for the Iceberg Optimizer Skill blog post.
Left panel: title + platform pills + version badge.
Right panel: stylised Claude Code icon + Apache Iceberg icon.
Pure-black background, site palette.
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

HERE   = Path(__file__).parent
OUTPUT = HERE.parents[2] / 'public' / 'img' / 'iceberg-optimizer' / 'social.png'
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# ── palette ──────────────────────────────────────────────────────────────────
BLACK  = '#000000'
CYAN   = '#3fc1ff'
GOLD   = '#ffd166'
GREEN  = '#7CFC8A'
TEXT   = '#ededed'
MUTED  = '#8b95a5'

W, H, DPI = 1200, 630, 100

fig = plt.figure(figsize=(W / DPI, H / DPI), facecolor=BLACK)
ax  = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis('off')
ax.set_facecolor(BLACK)

# ── LEFT PANEL – text ────────────────────────────────────────────────────────
lx = 52

ax.text(lx, 548, 'Codifying a Year of',      color=TEXT,  fontsize=33, fontweight='bold', ha='left', va='center')
ax.text(lx, 490, 'Apache Iceberg Pain',       color=CYAN,  fontsize=33, fontweight='bold', ha='left', va='center')
ax.text(lx, 432, 'into a Claude Code Skill',  color=TEXT,  fontsize=33, fontweight='bold', ha='left', va='center')

# platform pills
platforms = ['Spark', 'Trino', 'AWS Glue', 'Snowflake', 'Flink']
tx = lx
ty = 356
for p in platforms:
    pw = len(p) * 8.5 + 20
    badge = FancyBboxPatch((tx, ty - 13), pw, 26,
        boxstyle='round,pad=3', facecolor='#0e0e0e', edgecolor=MUTED, linewidth=1)
    ax.add_patch(badge)
    ax.text(tx + pw / 2, ty, p, color=MUTED, fontsize=10.5, ha='center', va='center')
    tx += pw + 7

# version badge
vb = FancyBboxPatch((lx, 288), 62, 26,
    boxstyle='round,pad=3', facecolor='#050f05', edgecolor=GREEN, linewidth=1.5)
ax.add_patch(vb)
ax.text(lx + 31, 301, 'v 0.1', color=GREEN, fontsize=12, fontweight='bold',
        ha='center', va='center')

# open-source call-out
ax.text(lx, 248, 'Open source · community contributions welcome',
        color=MUTED, fontsize=11, ha='left', va='center')

# site URL
ax.text(lx, 36, 'itamar-weiss.com', color=MUTED, fontsize=11, ha='left', va='center')

# thin vertical divider
ax.plot([640, 640], [36, H - 36], color='#1a1a1a', linewidth=1.5)

# ── RIGHT PANEL – icons ───────────────────────────────────────────────────────
# Centres for the two icons
cc_x, cc_y  = 770, 360   # Claude Code icon
ice_x, ice_y = 1040, 360  # Apache Iceberg icon

# ── Claude Code: sunburst mark ────────────────────────────────────────────────
r_in, r_out = 30, 50
n_rays = 8
for i in range(n_rays):
    ang = np.radians(i * 360 / n_rays + 22.5)   # 22.5° offset so rays point diagonally
    ax.plot(
        [cc_x + r_in  * np.cos(ang), cc_x + r_out * np.cos(ang)],
        [cc_y + r_in  * np.sin(ang), cc_y + r_out * np.sin(ang)],
        color=GOLD, linewidth=4, solid_capstyle='round', zorder=6
    )

inner = plt.Circle((cc_x, cc_y), r_in - 1,
    facecolor='#0c0900', edgecolor=GOLD, linewidth=2.5, zorder=7)
ax.add_patch(inner)
ax.text(cc_x, cc_y + 5,  'Claude', color=GOLD, fontsize=9, ha='center', va='center',
        fontweight='bold', zorder=8)
ax.text(cc_x, cc_y - 7,  'Code',   color=GOLD, fontsize=9, ha='center', va='center',
        fontweight='bold', zorder=8)

ax.text(cc_x, cc_y - 70, 'Claude Code',
        color=GOLD, fontsize=11.5, ha='center', va='top', fontweight='bold', alpha=0.8)

# ── Apache Iceberg: classic iceberg schematic ─────────────────────────────────
waterline_y = ice_y

# water fill
water = mpatches.FancyBboxPatch((ice_x - 130, 80), 260, waterline_y - 80,
    boxstyle='square,pad=0', facecolor='#060d18', edgecolor='none', alpha=0.7)
ax.add_patch(water)

# waterline
ax.plot([ice_x - 130, ice_x + 130], [waterline_y, waterline_y],
        color=CYAN, linewidth=1.5, alpha=0.4, linestyle='--')

# tip (above water) – triangle
tip_pts = [(ice_x - 60, waterline_y), (ice_x + 60, waterline_y), (ice_x, waterline_y + 155)]
tip = plt.Polygon(tip_pts, closed=True,
    facecolor='#0e2a40', edgecolor=CYAN, linewidth=2.5, zorder=5)
ax.add_patch(tip)

# subtle horizontal strata inside tip
for frac in [0.30, 0.58, 0.80]:
    yl  = waterline_y + frac * 155
    xlo = ice_x - 60 * (1 - frac)
    xhi = ice_x + 60 * (1 - frac)
    ax.plot([xlo, xhi], [yl, yl], color=CYAN, linewidth=0.8, alpha=0.22)

# body (below water) – wider irregular shape, dashed
body_pts = [
    (ice_x - 60,  waterline_y),
    (ice_x + 60,  waterline_y),
    (ice_x + 125, waterline_y - 80),
    (ice_x + 100, 95),
    (ice_x - 65,  95),
    (ice_x - 125, waterline_y - 90),
]
body = plt.Polygon(body_pts, closed=True,
    facecolor='#060d18', edgecolor='#1a4070', linewidth=1.5, linestyle='--',
    alpha=0.9, zorder=4)
ax.add_patch(body)

# "93% hidden" label inside body
ax.text(ice_x, 215, '93%',
        color='#1f4f80', fontsize=24, ha='center', va='center',
        fontweight='bold', alpha=0.85, zorder=5)
ax.text(ice_x, 170, 'hidden complexity',
        color='#1f4f80', fontsize=9.5, ha='center', va='center', alpha=0.8, zorder=5)

ax.text(ice_x, ice_y + 173, 'Apache Iceberg',
        color=CYAN, fontsize=11.5, ha='center', va='bottom', fontweight='bold', alpha=0.8)

# ── "+" connector ─────────────────────────────────────────────────────────────
mid_x = (cc_x + ice_x) / 2
ax.text(mid_x, ice_y, '+', color=MUTED, fontsize=40, ha='center', va='center', alpha=0.55)

plt.savefig(str(OUTPUT), dpi=DPI, bbox_inches='tight', pad_inches=0, facecolor=BLACK)
print(f'Saved → {OUTPUT}')
