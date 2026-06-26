#!/usr/bin/env python3
"""
Social card (1200×630) for the Iceberg Optimizer Skill blog post.
Left panel: title + platform pills + version badge.
Right panel: Claude AI symbol + Apache Iceberg logo.

Requires: pip install matplotlib numpy pillow requests

Run locally to produce public/img/iceberg-optimizer/social.png with the
real brand logos (downloads them from their canonical URLs). The remote CI
environment blocks those domains, so the committed PNG was generated with
hand-drawn stand-ins; re-run this script locally to upgrade it.
"""

import io
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from PIL import Image

HERE   = Path(__file__).parent
OUTPUT = HERE.parents[2] / 'public' / 'img' / 'iceberg-optimizer' / 'social.png'
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

ICEBERG_URL = 'https://www.dremio.com/wp-content/uploads/2021/06/iceberg-logo-with-name.png'
CLAUDE_URL  = 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Claude_AI_symbol.svg/1280px-Claude_AI_symbol.svg.png'

# ── palette ──────────────────────────────────────────────────────────────────
BLACK  = '#000000'
CYAN   = '#3fc1ff'
GOLD   = '#ffd166'
GREEN  = '#7CFC8A'
TEXT   = '#ededed'
MUTED  = '#8b95a5'

W, H, DPI = 1200, 630, 100


def fetch_logo(url: str) -> Image.Image | None:
    try:
        import requests
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert('RGBA')
    except Exception as e:
        print(f'Warning: could not fetch {url}: {e}', file=sys.stderr)
        return None


def logo_to_array(img: Image.Image, width_px: int) -> np.ndarray:
    """Resize keeping aspect ratio, return RGBA float array."""
    ratio  = width_px / img.width
    height = int(img.height * ratio)
    img    = img.resize((width_px, height), Image.LANCZOS)
    return np.asarray(img) / 255.0


# ── fetch logos ───────────────────────────────────────────────────────────────
iceberg_img = fetch_logo(ICEBERG_URL)
claude_img  = fetch_logo(CLAUDE_URL)

# ── canvas ────────────────────────────────────────────────────────────────────
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

platforms = ['Spark', 'Trino', 'AWS Glue', 'Snowflake', 'Flink']
tx, ty = lx, 356
for p in platforms:
    pw = len(p) * 8.5 + 20
    ax.add_patch(FancyBboxPatch((tx, ty - 13), pw, 26,
        boxstyle='round,pad=3', facecolor='#0e0e0e', edgecolor=MUTED, linewidth=1))
    ax.text(tx + pw / 2, ty, p, color=MUTED, fontsize=10.5, ha='center', va='center')
    tx += pw + 7

ax.add_patch(FancyBboxPatch((lx, 288), 62, 26,
    boxstyle='round,pad=3', facecolor='#050f05', edgecolor=GREEN, linewidth=1.5))
ax.text(lx + 31, 301, 'v 0.1', color=GREEN, fontsize=12, fontweight='bold',
        ha='center', va='center')

ax.text(lx, 248, 'Open source · community contributions welcome',
        color=MUTED, fontsize=11, ha='left', va='center')
ax.text(lx, 36, 'itamar-weiss.com', color=MUTED, fontsize=11, ha='left', va='center')

# thin vertical divider
ax.plot([640, 640], [36, H - 36], color='#1a1a1a', linewidth=1.5)

# ── RIGHT PANEL – logos ───────────────────────────────────────────────────────
LOGO_W = 200   # display width for each logo in data-units (px)

if claude_img is not None and iceberg_img is not None:
    # Place Claude logo: left of centre, vertically centred
    c_arr  = logo_to_array(claude_img, LOGO_W)
    c_h    = int(c_arr.shape[0])
    c_x0, c_y0 = 680, H // 2 - c_h // 2          # bottom-left corner in data coords
    ax.imshow(c_arr, extent=[c_x0, c_x0 + LOGO_W, c_y0, c_y0 + c_h],
              origin='upper', aspect='auto', zorder=5)
    ax.text(c_x0 + LOGO_W / 2, c_y0 - 22, 'Claude Code',
            color=GOLD, fontsize=11, ha='center', va='top', fontweight='bold', alpha=0.85)

    # "+" connector
    mid_x = 680 + LOGO_W + 60
    ax.text(mid_x, H // 2, '+', color=MUTED, fontsize=40, ha='center', va='center', alpha=0.55)

    # Place Iceberg logo: right of centre
    i_arr  = logo_to_array(iceberg_img, LOGO_W)
    i_h    = int(i_arr.shape[0])
    i_x0   = mid_x + 60
    i_y0   = H // 2 - i_h // 2
    # Make white/light background transparent for Iceberg logo
    ax.imshow(i_arr, extent=[i_x0, i_x0 + LOGO_W, i_y0, i_y0 + i_h],
              origin='upper', aspect='auto', zorder=5)
    ax.text(i_x0 + LOGO_W / 2, i_y0 - 22, 'Apache Iceberg',
            color=CYAN, fontsize=11, ha='center', va='top', fontweight='bold', alpha=0.85)

else:
    # ── fallback: hand-drawn stand-ins ───────────────────────────────────────
    print('Using hand-drawn fallback icons (run locally to get real logos)')

    cc_x, cc_y  = 770, 360
    ice_x, ice_y = 1040, 360

    # Claude Code sunburst
    r_in, r_out = 30, 50
    for i in range(8):
        ang = np.radians(i * 45 + 22.5)
        ax.plot([cc_x + r_in * np.cos(ang), cc_x + r_out * np.cos(ang)],
                [cc_y + r_in * np.sin(ang), cc_y + r_out * np.sin(ang)],
                color=GOLD, linewidth=4, solid_capstyle='round', zorder=6)
    ax.add_patch(plt.Circle((cc_x, cc_y), r_in - 1,
        facecolor='#0c0900', edgecolor=GOLD, linewidth=2.5, zorder=7))
    ax.text(cc_x, cc_y + 5,  'Claude', color=GOLD, fontsize=9, ha='center', va='center',
            fontweight='bold', zorder=8)
    ax.text(cc_x, cc_y - 7,  'Code',   color=GOLD, fontsize=9, ha='center', va='center',
            fontweight='bold', zorder=8)
    ax.text(cc_x, cc_y - 70, 'Claude Code',
            color=GOLD, fontsize=11.5, ha='center', va='top', fontweight='bold', alpha=0.8)

    # Apache Iceberg schematic
    wl_y = ice_y
    ax.add_patch(mpatches.FancyBboxPatch((ice_x - 130, 80), 260, wl_y - 80,
        boxstyle='square,pad=0', facecolor='#060d18', edgecolor='none', alpha=0.7))
    ax.plot([ice_x - 130, ice_x + 130], [wl_y, wl_y],
            color=CYAN, linewidth=1.5, alpha=0.4, linestyle='--')
    tip = plt.Polygon([(ice_x - 60, wl_y), (ice_x + 60, wl_y), (ice_x, wl_y + 155)],
        closed=True, facecolor='#0e2a40', edgecolor=CYAN, linewidth=2.5, zorder=5)
    ax.add_patch(tip)
    body = plt.Polygon([
        (ice_x - 60, wl_y), (ice_x + 60, wl_y),
        (ice_x + 125, wl_y - 80), (ice_x + 100, 95),
        (ice_x - 65, 95), (ice_x - 125, wl_y - 90)],
        closed=True, facecolor='#060d18', edgecolor='#1a4070',
        linewidth=1.5, linestyle='--', alpha=0.9, zorder=4)
    ax.add_patch(body)
    ax.text(ice_x, 215, '93%', color='#1f4f80', fontsize=24,
            ha='center', va='center', fontweight='bold', alpha=0.85, zorder=5)
    ax.text(ice_x, 170, 'hidden complexity', color='#1f4f80', fontsize=9.5,
            ha='center', va='center', alpha=0.8, zorder=5)
    ax.text(ice_x, ice_y + 173, 'Apache Iceberg',
            color=CYAN, fontsize=11.5, ha='center', va='bottom', fontweight='bold', alpha=0.8)

    ax.text((cc_x + ice_x) / 2, ice_y, '+', color=MUTED, fontsize=40,
            ha='center', va='center', alpha=0.55)

plt.savefig(str(OUTPUT), dpi=DPI, bbox_inches='tight', pad_inches=0, facecolor=BLACK)
print(f'Saved → {OUTPUT}')
