"""
USAF 1951 MTF Benchmark — 3DGS Under-Vegetation Reconstruction Quality

Compares a 3DGS-reconstructed top-down image against the clean ground-truth
top-down image using Michelson contrast at each USAF bar group/element.

Pipeline
--------
1. Capture N training views with vegetation (capture_views.py --cov 0.50)
2. Train 3DGS on those views using the exported COLMAP poses
3. Render the top-down view from the trained model → topdown_recon.png
4. Run this script to measure reconstruction quality:

    python benchmark.py --recon topdown_recon.png --gt topdown_gt.png

Control (0% occlusion)
-----------------------
    python capture_views.py --cov 0.00 --out training_00
    # train 3DGS → render topdown → should give near-perfect MTF

    # Sanity check without running 3DGS (identity case):
    python benchmark.py --recon training_00/topdown_gt.png \\
                        --gt    training_00/topdown_gt.png
    # → all contrast values equal, recovery_ratio = 1.0

Camera parameters (must match index.html)
------------------------------------------
    PerspectiveCamera(fov=52°, ...) looking at origin
    GT view: az=0°, el=88°, dist=11 m
"""

import argparse
import json
import math
import pathlib
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
TARGET_SIZE_M  = 5.0
TEX_SIZE_PX    = 1024
MM_PER_PX      = (TARGET_SIZE_M * 1000) / TEX_SIZE_PX   # ≈ 4.88 mm / px

CAM_FOV_V_DEG  = 52.0   # vertical FOV (Three.js fov parameter = vertical)

# Ground-truth view parameters (must match GT_VIEW in capture_views.py)
GT_AZ_DEG  = 0
GT_EL_DEG  = 88
GT_DIST_M  = 11

# USAF group layout in 1024×1024 texture (matches index.html group() calls)
GROUPS = [
    dict(label=1, bx=0,   by=0,   bw=512, bh=1024, d0=32),
    dict(label=2, bx=512, by=0,   bw=512, bh=512,  d0=16),
    dict(label=3, bx=512, by=512, bw=256, bh=256,  d0=8),
    dict(label=4, bx=768, by=512, bw=256, bh=256,  d0=4),
]
N_ELEMENTS = 6

BG  = "#0e1116"; CY = "#3fc1ff"; GLD = "#ffd166"
GRN = "#7CFC8A"; RED = "#ff5a5a"; TXT = "#ededed"; MUT = "#8b95a5"

SCRIPT_DIR = pathlib.Path(__file__).parent


# ── USAF element geometry ─────────────────────────────────────────────────────
def element_d(d0: int, e: int) -> int:
    return max(1, round(d0 * (2 ** (-(e - 1) / 6))))


def element_box_in_texture(grp: dict, e: int):
    """(x0, y0, x1, y1) in texture px for the VERTICAL bars of element e."""
    bx, by, d0 = grp['bx'], grp['by'], grp['d0']
    label_fs = min(22, max(7, round(d0 * 1.1)))
    cy = by + label_fs + 6
    for ei in range(1, e + 1):
        d   = element_d(d0, ei)
        eh  = 5 * d
        gap = max(2, round(d * 0.4))
        if ei == e:
            return (bx + 4, cy, bx + 4 + 5 * d, cy + eh)
        cy += eh + gap
    return None


# ── Camera projection ─────────────────────────────────────────────────────────
def build_camera_basis(az_deg, el_deg, dist):
    az = math.radians(az_deg)
    el = math.radians(el_deg)
    pos = np.array([
        dist * math.cos(el) * math.sin(az),
        dist * math.sin(el),
        dist * math.cos(el) * math.cos(az),
    ])
    z_axis = pos / np.linalg.norm(pos)          # points away from scene
    world_up = np.array([0., 1., 0.])
    right = np.cross(world_up, z_axis)
    right /= np.linalg.norm(right)
    up = np.cross(z_axis, right)
    return pos, right, up, z_axis


def tex_to_world(tx: float, ty: float) -> np.ndarray:
    """Texture pixel → world-space 3-D point on the ground plane (y=0)."""
    s = TARGET_SIZE_M / TEX_SIZE_PX
    return np.array([tx * s - TARGET_SIZE_M / 2, 0.0,
                     ty * s - TARGET_SIZE_M / 2])


def project(world_pt, cam_pos, right, up, z_axis, img_w, img_h):
    f_v = 1.0 / math.tan(math.radians(CAM_FOV_V_DEG) / 2)
    aspect = img_w / img_h
    v = world_pt - cam_pos
    x_cam = np.dot(v, right)
    y_cam = np.dot(v, up)
    z_cam = -np.dot(v, z_axis)   # positive = in front
    if z_cam <= 0:
        return None
    return ((x_cam / z_cam) * (f_v / aspect) + 1) / 2 * img_w, \
           (1 - (y_cam / z_cam) * f_v) / 2 * img_h


def build_homography(az_deg, el_deg, dist, img_w, img_h):
    """DLT homography from texture pixels → image pixels."""
    cam_pos, right, up, z_axis = build_camera_basis(az_deg, el_deg, dist)
    tex_corners = [(0., 0.), (TEX_SIZE_PX, 0.),
                   (0., TEX_SIZE_PX), (TEX_SIZE_PX, TEX_SIZE_PX)]
    img_corners = []
    for tx, ty in tex_corners:
        pt = project(tex_to_world(tx, ty), cam_pos, right, up, z_axis, img_w, img_h)
        if pt is None:
            return None
        img_corners.append(pt)

    A = []
    for (sx, sy), (dx, dy) in zip(tex_corners, img_corners):
        A.append([-sx, -sy, -1,   0,   0,  0, dx*sx, dx*sy, dx])
        A.append([  0,   0,  0, -sx, -sy, -1, dy*sx, dy*sy, dy])
    _, _, Vt = np.linalg.svd(np.array(A, dtype=float))
    h = Vt[-1].reshape(3, 3)
    return h / h[2, 2]


def apply_h(H, tx, ty):
    pt = H @ np.array([tx, ty, 1.0])
    return pt[0] / pt[2], pt[1] / pt[2]


# ── Crop and contrast ─────────────────────────────────────────────────────────
def crop_region(img: np.ndarray, tex_box, H: np.ndarray):
    tx0, ty0, tx1, ty1 = tex_box
    img_h, img_w = img.shape[:2]
    corners = [apply_h(H, x, y)
               for x, y in [(tx0,ty0),(tx1,ty0),(tx0,ty1),(tx1,ty1)]]
    xs = [c[0] for c in corners]; ys = [c[1] for c in corners]
    ix0 = max(0, math.floor(min(xs)))
    ix1 = min(img_w, math.ceil(max(xs)))
    iy0 = max(0, math.floor(min(ys)))
    iy1 = min(img_h, math.ceil(max(ys)))
    if ix1 <= ix0 or iy1 <= iy0:
        return None
    return img[iy0:iy1, ix0:ix1]


def michelson(patch: np.ndarray) -> float:
    if patch is None or patch.size == 0:
        return float('nan')
    grey = patch.mean(axis=2) if patch.ndim == 3 else patch
    lo, hi = float(grey.min()), float(grey.max())
    if hi + lo < 1e-6:
        return float('nan')
    return (hi - lo) / (hi + lo)


# ── Per-element result ────────────────────────────────────────────────────────
@dataclass
class ElementResult:
    group: int
    element: int
    bar_width_mm: float
    lp_per_mm: float
    contrast_gt:    float    # ground truth (clean top-down)
    contrast_recon: float    # 3DGS reconstruction


def analyse(gt_img: np.ndarray, recon_img: np.ndarray,
            az=GT_AZ_DEG, el=GT_EL_DEG, dist=GT_DIST_M) -> list[ElementResult]:
    H, W = gt_img.shape[:2]
    hom = build_homography(az, el, dist, W, H)
    if hom is None:
        return []

    results = []
    for grp in GROUPS:
        for e in range(1, N_ELEMENTS + 1):
            box = element_box_in_texture(grp, e)
            if box is None:
                continue
            d      = element_d(grp['d0'], e)
            bw_mm  = d * MM_PER_PX
            lp_mm  = 1.0 / (2 * bw_mm)

            cgt = michelson(crop_region(gt_img, box, hom))
            cr  = michelson(crop_region(recon_img, box, hom))

            results.append(ElementResult(
                group=grp['label'], element=e,
                bar_width_mm=round(bw_mm, 2),
                lp_per_mm=round(lp_mm, 4),
                contrast_gt=round(cgt, 4)    if not math.isnan(cgt) else None,
                contrast_recon=round(cr, 4)  if not math.isnan(cr)  else None,
            ))
    return results


# ── MTF plot ──────────────────────────────────────────────────────────────────
def plot_mtf(results: list[ElementResult], out_path: pathlib.Path,
             title_extra: str = ""):
    if not HAS_MPL:
        return
    fig, ax = plt.subplots(figsize=(10, 6), facecolor=BG)
    ax.set_facecolor(BG)
    for spine in ax.spines.values():
        spine.set_color(MUT)
    ax.spines[['top','right']].set_visible(False)
    ax.tick_params(colors=MUT, labelsize=9)

    freqs = [r.lp_per_mm for r in results]
    cgt   = [r.contrast_gt    or 0 for r in results]
    crecon= [r.contrast_recon or 0 for r in results]

    ax.plot(freqs, cgt,    'o-', color=GRN, lw=2, ms=5, label='Ground truth (no straw)')
    ax.plot(freqs, crecon, 's-', color=CY,  lw=2, ms=5, label='3DGS reconstruction')
    ax.axhline(0.20, color=RED, lw=1.2, ls='--', label='Resolution threshold (C=0.20)')

    group_bounds = {}
    for r in results:
        group_bounds.setdefault(r.group, []).append(r.lp_per_mm)
    for g, fs in group_bounds.items():
        ax.text(sum(fs)/len(fs), 0.97, f'G{g}', color=MUT, fontsize=8,
                ha='center', va='top', transform=ax.get_xaxis_transform())
        ax.axvline(max(fs), color=MUT, lw=0.5, ls=':')

    ax.set_xlabel('Spatial frequency  (lp / mm physical)', color=TXT, fontsize=10)
    ax.set_ylabel('Michelson contrast', color=TXT, fontsize=10)
    title = '3DGS Reconstruction MTF — USAF 1951 target'
    if title_extra:
        title += f'  [{title_extra}]'
    ax.set_title(title, color=TXT, fontsize=12, pad=10)
    ax.set_ylim(0, 1.05)
    ax.legend(facecolor=BG, edgecolor=MUT, labelcolor=TXT, fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    print(f"  MTF plot → {out_path}")


# ── Score ─────────────────────────────────────────────────────────────────────
def score(results: list[ElementResult]) -> dict:
    gt_r    = [r for r in results if (r.contrast_gt or 0)    > 0.20]
    recon_r = [r for r in results if (r.contrast_recon or 0) > 0.20]
    max_gt    = max((r.lp_per_mm for r in gt_r),    default=0)
    max_recon = max((r.lp_per_mm for r in recon_r), default=0)

    cgt   = np.array([r.contrast_gt    or 0 for r in results])
    crecon= np.array([r.contrast_recon or 0 for r in results])
    loss  = float(np.mean(np.clip(cgt - crecon, 0, 1)))

    return dict(
        reconstruction_loss = round(loss, 4),
        max_freq_gt         = round(max_gt,    4),
        max_freq_recon      = round(max_recon, 4),
        recovery_ratio      = round(max_recon / max_gt, 4) if max_gt > 0 else 0,
        n_resolved_gt       = len(gt_r),
        n_resolved_recon    = len(recon_r),
    )


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('--recon', required=True,
                    help='Rendered top-down from 3DGS (or GT for identity control)')
    ap.add_argument('--gt',    required=True,
                    help='Ground-truth top-down (topdown_gt.png, veg=0)')
    ap.add_argument('--out',   default=str(SCRIPT_DIR),
                    help='Output directory for JSON + PNG')
    ap.add_argument('--label', default='',
                    help='Short label for the plot title (e.g. "cov50")')
    args = ap.parse_args()

    gt_img    = np.array(Image.open(args.gt).convert('RGB'))
    recon_img = np.array(Image.open(args.recon).convert('RGB'))

    H, W = gt_img.shape[:2]
    if recon_img.shape[:2] != (H, W):
        from PIL import Image as PILImage
        recon_img = np.array(
            PILImage.open(args.recon).convert('RGB').resize((W, H), PILImage.LANCZOS))

    print(f"  GT:    {args.gt}  ({W}×{H})")
    print(f"  Recon: {args.recon}")

    results = analyse(gt_img, recon_img)
    if not results:
        sys.exit("Analysis failed — check camera parameters.")

    sc = score(results)
    print(f"\n  recovery_ratio = {sc['recovery_ratio']:.3f}")
    print(f"  loss           = {sc['reconstruction_loss']:.4f}")
    print(f"  max_freq_gt    = {sc['max_freq_gt']:.4f} lp/mm  "
          f"({sc['n_resolved_gt']} elements resolved)")
    print(f"  max_freq_recon = {sc['max_freq_recon']:.4f} lp/mm  "
          f"({sc['n_resolved_recon']} elements resolved)")

    print()
    for r in results:
        flag = '✓' if (r.contrast_recon or 0) > 0.20 else '✗'
        print(f"    G{r.group}E{r.element}  {r.bar_width_mm:6.1f}mm  "
              f"gt={r.contrast_gt or 0:.3f}  recon={r.contrast_recon or 0:.3f}  {flag}")

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    label = args.label or pathlib.Path(args.recon).stem

    report = {
        'gt_path': args.gt, 'recon_path': args.recon,
        'target_size_m': TARGET_SIZE_M, 'mm_per_px': round(MM_PER_PX, 3),
        'contrast_threshold': 0.20, 'score': sc,
        'elements': [asdict(r) for r in results],
    }
    rp = out_dir / f'benchmark_{label}.json'
    rp.write_text(json.dumps(report, indent=2))
    print(f"\n  Report → {rp}")

    plot_mtf(results, out_dir / f'mtf_{label}.png', title_extra=label)


if __name__ == '__main__':
    main()
