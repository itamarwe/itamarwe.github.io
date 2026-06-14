"""
USAF 1951 Target Benchmark — Gaussian Splatting Under Occlusion

Measures how well a reconstruction algorithm recovers spatial detail
from images captured through a straw/vegetation occlusion layer.

Metric: Michelson contrast  C = (Imax − Imin) / (Imax + Imin)
        at each USAF bar group / element.
        C > 0.20 → bars are "resolved" (standard threshold).

Pipeline
--------
1. Capture *_noveg.png  (no occlusion, ground truth)
2. Capture *_veg.png    (with straw roof, degraded observations)
3. [Optional] Run 3DGS on veg views → render novel *_recon.png
4. Run this script to compare contrast at each frequency.

Usage
-----
    python benchmark.py [--images DIR] [--out DIR]

Outputs
-------
    benchmark_report.json   — per-frequency contrast table + scores
    mtf_curves.png          — MTF curves (ideal vs. occluded vs. reconstructed)
"""

import argparse
import json
import math
import pathlib
import re
import sys
from dataclasses import dataclass, asdict

import numpy as np

try:
    from PIL import Image
except ImportError:
    sys.exit("pip install Pillow")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("Warning: matplotlib not found — skipping MTF plot")

# ── Scene / texture constants (must match index.html) ─────────────────────────
TARGET_SIZE_M  = 5.0     # physical target side length (metres)
TEX_SIZE_PX    = 1024    # canvas texture size (pixels)
MM_PER_PX      = (TARGET_SIZE_M * 1000) / TEX_SIZE_PX   # ≈ 4.88 mm / px

# USAF group layout in the 1024×1024 texture (bx, by, bw, bh, d0_px)
# These MUST match the group() calls in makeUSAFTexture() in index.html.
GROUPS = [
    dict(label=1, bx=0,   by=0,   bw=512, bh=1024, d0=32),
    dict(label=2, bx=512, by=0,   bw=512, bh=512,  d0=16),
    dict(label=3, bx=512, by=512, bw=256, bh=256,  d0=8),
    dict(label=4, bx=768, by=512, bw=256, bh=256,  d0=4),
]
N_ELEMENTS = 6   # elements per group

# ── Palette ───────────────────────────────────────────────────────────────────
BG  = "#0e1116"; CY = "#3fc1ff"; GLD = "#ffd166"
GRN = "#7CFC8A"; RED = "#ff5a5a"; PRP = "#b48cff"; TXT = "#ededed"; MUT = "#8b95a5"

SCRIPT_DIR = pathlib.Path(__file__).parent


# ── USAF geometry helpers ─────────────────────────────────────────────────────
def element_d(d0: int, e: int) -> int:
    """Bar width (px) for group with base d0 and element index e (1-based)."""
    return max(1, round(d0 * (2 ** (-(e - 1) / 6))))


def element_box_in_texture(grp: dict, e: int):
    """
    Returns (x0, y0, x1, y1) in texture pixels for USAF element e (1-based)
    within group grp, covering only the VERTICAL bars sub-section.

    The vertical bars sub-section is at the left side of each element:
        x ∈ [bx+4,  bx+4+5*d]
        y ∈ [element_top, element_top + 5*d]

    We measure contrast on vertical bars (they test horizontal spatial frequency).
    """
    bx, by = grp['bx'], grp['by']
    d0 = grp['d0']
    # Stack elements from top; each element uses (5*d + gap) rows.
    # First row offset: label row + small gap.
    label_fs = min(22, max(7, round(d0 * 1.1)))
    cy = by + label_fs + 6

    for ei in range(1, e + 1):
        d  = element_d(d0, ei)
        eh = 5 * d
        gap = max(2, round(d * 0.4))
        if ei == e:
            return (bx + 4, cy, bx + 4 + 5 * d, cy + eh)
        cy += eh + gap

    return None  # element doesn't fit


# ── Contrast measurement ──────────────────────────────────────────────────────
def crop_region(img: np.ndarray, tex_box, img_w: int, img_h: int,
                target_px_w: float, target_px_h: float,
                target_origin_x: float, target_origin_y: float):
    """
    Map a texture-space box (in px on the 1024 canvas) to image-space pixels.

    img_w, img_h       : rendered image dimensions
    target_px_w/h      : width/height of the 5m target IN IMAGE PIXELS
    target_origin_x/y  : image pixel of the target's top-left corner
    """
    tx0, ty0, tx1, ty1 = tex_box
    # Texture → normalised [0,1]
    n0 = tx0 / TEX_SIZE_PX; n1 = tx1 / TEX_SIZE_PX
    m0 = ty0 / TEX_SIZE_PX; m1 = ty1 / TEX_SIZE_PX
    # Normalised → image pixels
    ix0 = int(target_origin_x + n0 * target_px_w)
    ix1 = int(target_origin_x + n1 * target_px_w)
    iy0 = int(target_origin_y + m0 * target_px_h)
    iy1 = int(target_origin_y + m1 * target_px_h)
    # Clamp
    ix0 = max(0, min(ix0, img_w - 1))
    ix1 = max(0, min(ix1, img_w))
    iy0 = max(0, min(iy0, img_h - 1))
    iy1 = max(0, min(iy1, img_h))
    if ix1 <= ix0 or iy1 <= iy0:
        return None
    return img[iy0:iy1, ix0:ix1]


def michelson_contrast(patch: np.ndarray) -> float:
    """Michelson contrast on a greyscale crop."""
    if patch is None or patch.size == 0:
        return float('nan')
    grey = patch.mean(axis=2) if patch.ndim == 3 else patch
    lo, hi = float(grey.min()), float(grey.max())
    if hi + lo < 1e-6:
        return float('nan')
    return (hi - lo) / (hi + lo)


# ── Locate target in image (simple centroid of bright region) ─────────────────
def locate_target(img: np.ndarray, img_w: int, img_h: int):
    """
    Rough estimate of the target bounding box in image pixels.

    The USAF target uses a light grey background (#d4d4d4 ≈ 0.83 brightness).
    We threshold to find bright near-white pixels, cluster them, and return
    the bounding box.

    Returns: (x0, y0, x1, y1, origin_x, origin_y, w_px, h_px)
    or None if not detectable.
    """
    grey = img.mean(axis=2)
    # Light grey threshold
    mask = grey > 160          # 0-255 scale
    ys, xs = np.where(mask)
    if len(xs) < 100:
        return None
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    return x0, y0, x1, y1, x0, y0, x1 - x0, y1 - y0


@dataclass
class ElementResult:
    group: int
    element: int
    bar_width_mm: float    # physical bar width in mm
    lp_per_mm: float       # spatial frequency in line pairs / mm
    contrast_ideal: float  # contrast in no-occlusion ground truth
    contrast_occ: float    # contrast with occlusion
    contrast_recon: float  # contrast in reconstruction (NaN if not provided)
    resolved_ideal: bool
    resolved_occ: bool


# ── Main analysis ─────────────────────────────────────────────────────────────
def analyse_pair(noveg_path: pathlib.Path, veg_path: pathlib.Path,
                 recon_path: pathlib.Path = None) -> list[ElementResult]:
    ideal_img = np.array(Image.open(noveg_path).convert('RGB'))
    occ_img   = np.array(Image.open(veg_path).convert('RGB'))
    recon_img = np.array(Image.open(recon_path).convert('RGB')) if (recon_path and recon_path.exists()) else None

    H, W = ideal_img.shape[:2]
    results = []

    # Locate target in the ideal (no-veg) image
    loc = locate_target(ideal_img, W, H)
    if loc is None:
        print(f"  Warning: could not locate target in {noveg_path.name}")
        return results
    x0, y0, x1, y1, ox, oy, tw, th = loc

    for grp in GROUPS:
        for e in range(1, N_ELEMENTS + 1):
            box = element_box_in_texture(grp, e)
            if box is None:
                continue

            d   = element_d(grp['d0'], e)
            bw_mm   = d * MM_PER_PX          # physical bar width (mm)
            lp_mm   = 1.0 / (2 * bw_mm)     # line pairs per mm (1 lp = bar + gap)

            def contrast_for(img):
                patch = crop_region(img, box, W, H, tw, th, ox, oy)
                return michelson_contrast(patch)

            ci = contrast_for(ideal_img)
            co = contrast_for(occ_img)
            cr = contrast_for(recon_img) if recon_img is not None else float('nan')

            results.append(ElementResult(
                group=grp['label'], element=e,
                bar_width_mm=round(bw_mm, 2),
                lp_per_mm=round(lp_mm, 4),
                contrast_ideal=round(ci, 4) if not math.isnan(ci) else None,
                contrast_occ=round(co, 4)   if not math.isnan(co) else None,
                contrast_recon=round(cr, 4) if not math.isnan(cr) else None,
                resolved_ideal=ci > 0.20 if not math.isnan(ci) else False,
                resolved_occ=co > 0.20   if not math.isnan(co) else False,
            ))

    return results


# ── MTF plot ──────────────────────────────────────────────────────────────────
def plot_mtf(results: list[ElementResult], out_path: pathlib.Path):
    if not HAS_MPL:
        return
    fig, ax = plt.subplots(figsize=(10, 6), facecolor=BG)
    ax.set_facecolor(BG)
    ax.spines[['top', 'right']].set_visible(False)
    ax.spines[['left', 'bottom']].set_color(MUT)
    ax.tick_params(colors=MUT, labelsize=9)

    freqs = [r.lp_per_mm for r in results]
    ci    = [r.contrast_ideal or 0 for r in results]
    co    = [r.contrast_occ   or 0 for r in results]
    cr    = [r.contrast_recon or 0 for r in results]

    ax.plot(freqs, ci, 'o-', color=GRN,  linewidth=2, markersize=5, label='Ground truth (no occlusion)')
    ax.plot(freqs, co, 's-', color=GLD,  linewidth=2, markersize=5, label='With straw occlusion')
    if any(v > 0 for v in cr):
        ax.plot(freqs, cr, '^-', color=CY, linewidth=2, markersize=5, label='3DGS reconstruction')

    ax.axhline(0.20, color=RED, linewidth=1.2, linestyle='--', label='Resolution threshold (C=0.20)')

    # Group dividers
    group_bounds = {}
    for r in results:
        group_bounds.setdefault(r.group, []).append(r.lp_per_mm)
    for g, fs in group_bounds.items():
        mid = sum(fs) / len(fs)
        ax.text(mid, 0.97, f'G{g}', color=MUT, fontsize=8,
                ha='center', va='top', transform=ax.get_xaxis_transform())
        ax.axvline(max(fs), color=MUT, linewidth=0.5, linestyle=':')

    ax.set_xlabel('Spatial frequency  (lp / mm physical)', color=TXT, fontsize=10)
    ax.set_ylabel('Michelson contrast', color=TXT, fontsize=10)
    ax.set_title('MTF — USAF 1951 target through straw occlusion', color=TXT, fontsize=12, pad=10)
    ax.set_ylim(0, 1.05)
    ax.legend(facecolor=BG, edgecolor=MUT, labelcolor=TXT, fontsize=9)

    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    print(f"  MTF plot → {out_path}")


# ── Summary scoring ───────────────────────────────────────────────────────────
def score(results: list[ElementResult]) -> dict:
    """
    occlusion_loss : area between ideal MTF and occluded MTF (lower = harder)
    resolved_ideal : highest spatial freq resolved in ground truth
    resolved_occ   : highest spatial freq resolved with occlusion
    recovery_ratio : resolved_occ / resolved_ideal  (1.0 = perfect)
    """
    ideal_r = [r for r in results if r.resolved_ideal]
    occ_r   = [r for r in results if r.resolved_occ]
    max_ideal = max((r.lp_per_mm for r in ideal_r), default=0)
    max_occ   = max((r.lp_per_mm for r in occ_r),   default=0)

    ci = np.array([r.contrast_ideal or 0 for r in results])
    co = np.array([r.contrast_occ   or 0 for r in results])
    loss = float(np.mean(np.clip(ci - co, 0, 1)))

    return dict(
        occlusion_loss   = round(loss, 4),
        max_freq_ideal   = round(max_ideal, 4),
        max_freq_occ     = round(max_occ, 4),
        recovery_ratio   = round(max_occ / max_ideal, 4) if max_ideal > 0 else 0,
        n_elements_total = len(results),
        n_resolved_ideal = len(ideal_r),
        n_resolved_occ   = len(occ_r),
    )


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--images', default=str(SCRIPT_DIR / 'sample_images'))
    ap.add_argument('--out',    default=str(SCRIPT_DIR))
    args = ap.parse_args()

    img_dir = pathlib.Path(args.images)
    out_dir  = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Find all noveg / veg pairs
    noveg_files = sorted(img_dir.glob('*_noveg.png'))
    if not noveg_files:
        sys.exit(f'No *_noveg.png files in {img_dir}. Run capture_views.py first.')

    all_results = {}
    for nv in noveg_files:
        stem  = re.sub(r'_noveg$', '', nv.stem)
        veg   = img_dir / f'{stem}_veg.png'
        recon = img_dir / f'{stem}_recon.png'   # optional, from 3DGS
        if not veg.exists():
            continue

        print(f'\n  Analysing: {stem}')
        res = analyse_pair(nv, veg, recon if recon.exists() else None)
        if not res:
            continue

        sc = score(res)
        print(f'    loss={sc["occlusion_loss"]:.3f}  '
              f'max_ideal={sc["max_freq_ideal"]:.4f} lp/mm  '
              f'max_occ={sc["max_freq_occ"]:.4f} lp/mm  '
              f'recovery={sc["recovery_ratio"]:.3f}')

        for r in res:
            flag = '✓' if r.resolved_occ else '✗'
            print(f'      G{r.group}E{r.element} '
                  f'{r.bar_width_mm:6.1f}mm  '
                  f'ideal={r.contrast_ideal or 0:.3f}  '
                  f'occ={r.contrast_occ or 0:.3f}  {flag}')

        all_results[stem] = {'elements': [asdict(r) for r in res], 'score': sc}

        plot_mtf(res, out_dir / f'mtf_{stem}.png')

    report = {
        'target_size_m':  TARGET_SIZE_M,
        'mm_per_px':      round(MM_PER_PX, 3),
        'contrast_threshold': 0.20,
        'pairs': all_results,
    }
    rp = out_dir / 'benchmark_report.json'
    rp.write_text(json.dumps(report, indent=2))
    print(f'\n  Report → {rp}')


if __name__ == '__main__':
    main()
