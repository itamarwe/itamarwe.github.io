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
    mtf_{view}.png          — MTF curves per view pair
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

# Camera FOV matching index.html: PerspectiveCamera(52, aspect, 0.1, 300)
CAM_FOV_V_DEG  = 52.0   # vertical FOV (Three.js fov = vertical)

# USAF group layout in the 1024×1024 texture (bx, by, bw, bh, d0_px)
# These MUST match the group() calls in makeUSAFTexture() in index.html.
GROUPS = [
    dict(label=1, bx=0,   by=0,   bw=512, bh=1024, d0=32),
    dict(label=2, bx=512, by=0,   bw=512, bh=512,  d0=16),
    dict(label=3, bx=512, by=512, bw=256, bh=256,  d0=8),
    dict(label=4, bx=768, by=512, bw=256, bh=256,  d0=4),
]
N_ELEMENTS = 6   # elements per group

# Camera views matching capture_views.py VIEWS list.
# label → (az_deg, el_deg, dist_m)
CAPTURE_VIEWS = {
    "topdown":  (  0,  88, 11),
    "hi_N":     (  0,  72, 13),  "hi_E":  ( 90,  72, 13),
    "hi_S":     (180,  72, 13),  "hi_W":  (270,  72, 13),
    "mid_N":    (  0,  55, 14),  "mid_E": ( 90,  55, 14),
    "mid_S":    (180,  55, 14),  "mid_W": (270,  55, 14),
    "low_NE":   ( 45,  38, 14),  "low_SE": (135, 38, 14),
    "low_SW":   (225,  38, 14),  "low_NW": (315, 38, 14),
}

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
    # First row offset: label row + small gap (mirrors group() in index.html).
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


# ── Camera projection ─────────────────────────────────────────────────────────
def build_camera_basis(az_deg: float, el_deg: float, dist: float):
    """
    Returns (cam_pos, right, up, z_axis) for the Three.js camera.

    The camera sits at the spherical position (az, el, dist) looking at origin.
    Formula from index.html:
        x = dist * cos(el) * sin(az)
        y = dist * sin(el)
        z = dist * cos(el) * cos(az)
    World up = (0, 1, 0).
    """
    az = math.radians(az_deg)
    el = math.radians(el_deg)
    cam_pos = np.array([
        dist * math.cos(el) * math.sin(az),
        dist * math.sin(el),
        dist * math.cos(el) * math.cos(az),
    ])
    look_at = np.zeros(3)

    # Camera basis (matches Three.js lookAt)
    z_axis = cam_pos - look_at          # points away from scene
    z_axis /= np.linalg.norm(z_axis)
    world_up = np.array([0., 1., 0.])
    right = np.cross(world_up, z_axis)
    right /= np.linalg.norm(right)
    up = np.cross(z_axis, right)         # camera up

    return cam_pos, right, up, z_axis


def project_world_to_image(world_pt, cam_pos, right, up, z_axis,
                           img_w: int, img_h: int,
                           fov_v_deg: float = CAM_FOV_V_DEG):
    """Project a world-space point to image pixel coordinates."""
    aspect = img_w / img_h
    f_v = 1.0 / math.tan(math.radians(fov_v_deg) / 2)

    v = world_pt - cam_pos
    x_cam = np.dot(v, right)
    y_cam = np.dot(v, up)
    z_cam = -np.dot(v, z_axis)          # positive = in front of camera

    if z_cam <= 0:
        return None                     # behind camera

    x_ndc = (x_cam / z_cam) * (f_v / aspect)
    y_ndc = (y_cam / z_cam) * f_v

    img_x = (x_ndc + 1) / 2 * img_w
    img_y = (1 - y_ndc) / 2 * img_h
    return img_x, img_y


def target_tex_to_world(tex_x: float, tex_y: float) -> np.ndarray:
    """
    Map texture pixel (tex_x, tex_y) to world-space 3-D point on the ground plane.

    PlaneGeometry(5,5) rotated -π/2 around X:
        world_x = tex_x/1024 * 5.0 - 2.5
        world_y = 0
        world_z = tex_y/1024 * 5.0 - 2.5

    Derivation: UV(0,1)→canvas(0,0)→world(-2.5,0,-2.5)  etc.
    """
    s = TARGET_SIZE_M / TEX_SIZE_PX
    return np.array([
        tex_x * s - TARGET_SIZE_M / 2,
        0.0,
        tex_y * s - TARGET_SIZE_M / 2,
    ])


def compute_homography(src_pts, dst_pts) -> np.ndarray:
    """
    Compute 3×3 homography H such that dst = H * src (homogeneous).
    src_pts, dst_pts: lists/arrays of 4 (x, y) pairs.
    Uses the DLT algorithm (SVD).
    """
    A = []
    for (sx, sy), (dx, dy) in zip(src_pts, dst_pts):
        A.append([-sx, -sy, -1,   0,   0,  0, dx * sx, dx * sy, dx])
        A.append([  0,   0,  0, -sx, -sy, -1, dy * sx, dy * sy, dy])
    A = np.array(A, dtype=float)
    _, _, Vt = np.linalg.svd(A)
    h = Vt[-1].reshape(3, 3)
    return h / h[2, 2]


def apply_homography(H: np.ndarray, x: float, y: float):
    pt = H @ np.array([x, y, 1.0])
    return pt[0] / pt[2], pt[1] / pt[2]


def build_tex_to_image_homography(az_deg, el_deg, dist, img_w, img_h):
    """
    Return a 3×3 homography mapping texture pixels → image pixels
    using the known camera parameters and target geometry.
    """
    cam_pos, right, up, z_axis = build_camera_basis(az_deg, el_deg, dist)

    # Four texture corners: (0,0), (W,0), (0,H), (W,H)
    tex_corners = [
        (0.0,          0.0),
        (TEX_SIZE_PX,  0.0),
        (0.0,          TEX_SIZE_PX),
        (TEX_SIZE_PX,  TEX_SIZE_PX),
    ]
    img_corners = []
    for tx, ty in tex_corners:
        world = target_tex_to_world(tx, ty)
        pt = project_world_to_image(world, cam_pos, right, up, z_axis, img_w, img_h)
        if pt is None:
            return None
        img_corners.append(pt)

    return compute_homography(tex_corners, img_corners)


# ── Crop a texture-space box out of the image ─────────────────────────────────
def crop_region(img: np.ndarray, tex_box, H: np.ndarray):
    """
    Map texture-space box (tx0, ty0, tx1, ty1) to image pixels via homography H.
    Returns the axis-aligned image crop.
    """
    tx0, ty0, tx1, ty1 = tex_box
    img_h, img_w = img.shape[:2]

    corners_img = [
        apply_homography(H, tx0, ty0),
        apply_homography(H, tx1, ty0),
        apply_homography(H, tx0, ty1),
        apply_homography(H, tx1, ty1),
    ]
    xs = [c[0] for c in corners_img]
    ys = [c[1] for c in corners_img]

    ix0 = max(0, math.floor(min(xs)))
    ix1 = min(img_w, math.ceil(max(xs)))
    iy0 = max(0, math.floor(min(ys)))
    iy1 = min(img_h, math.ceil(max(ys)))

    if ix1 <= ix0 or iy1 <= iy0:
        return None
    return img[iy0:iy1, ix0:ix1]


# ── Contrast measurement ──────────────────────────────────────────────────────
def michelson_contrast(patch: np.ndarray) -> float:
    """Michelson contrast on a greyscale crop."""
    if patch is None or patch.size == 0:
        return float('nan')
    grey = patch.mean(axis=2) if patch.ndim == 3 else patch
    lo, hi = float(grey.min()), float(grey.max())
    if hi + lo < 1e-6:
        return float('nan')
    return (hi - lo) / (hi + lo)


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
                 recon_path: pathlib.Path = None,
                 az: float = 0, el: float = 88, dist: float = 11,
                 ) -> list[ElementResult]:
    ideal_img = np.array(Image.open(noveg_path).convert('RGB'))
    occ_img   = np.array(Image.open(veg_path).convert('RGB'))
    recon_img = np.array(Image.open(recon_path).convert('RGB')) if (recon_path and recon_path.exists()) else None

    H, W = ideal_img.shape[:2]

    # Build homography from camera parameters (same for all three images).
    hom = build_tex_to_image_homography(az, el, dist, W, H)
    if hom is None:
        print(f"  Warning: homography failed for az={az} el={el} d={dist}")
        return []

    results = []
    for grp in GROUPS:
        for e in range(1, N_ELEMENTS + 1):
            box = element_box_in_texture(grp, e)
            if box is None:
                continue

            d       = element_d(grp['d0'], e)
            bw_mm   = d * MM_PER_PX
            lp_mm   = 1.0 / (2 * bw_mm)

            def contrast_for(img):
                patch = crop_region(img, box, hom)
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
def plot_mtf(results: list[ElementResult], out_path: pathlib.Path,
             view_label: str = ""):
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

    # Group dividers and labels
    group_bounds = {}
    for r in results:
        group_bounds.setdefault(r.group, []).append(r.lp_per_mm)
    for g, fs in group_bounds.items():
        mid = sum(fs) / len(fs)
        ax.text(mid, 0.97, f'G{g}', color=MUT, fontsize=8,
                ha='center', va='top', transform=ax.get_xaxis_transform())
        ax.axvline(max(fs), color=MUT, linewidth=0.5, linestyle=':')

    title = 'MTF — USAF 1951 target through straw occlusion'
    if view_label:
        title += f'  [{view_label}]'
    ax.set_xlabel('Spatial frequency  (lp / mm physical)', color=TXT, fontsize=10)
    ax.set_ylabel('Michelson contrast', color=TXT, fontsize=10)
    ax.set_title(title, color=TXT, fontsize=12, pad=10)
    ax.set_ylim(0, 1.05)
    ax.legend(facecolor=BG, edgecolor=MUT, labelcolor=TXT, fontsize=9)

    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    print(f"  MTF plot → {out_path}")


# ── Summary scoring ───────────────────────────────────────────────────────────
def score(results: list[ElementResult]) -> dict:
    """
    occlusion_loss : area between ideal MTF and occluded MTF
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

    noveg_files = sorted(img_dir.glob('*_noveg.png'))
    if not noveg_files:
        sys.exit(f'No *_noveg.png files in {img_dir}. Run capture_views.py first.')

    all_results = {}
    for nv in noveg_files:
        stem  = re.sub(r'_noveg$', '', nv.stem)
        veg   = img_dir / f'{stem}_veg.png'
        recon = img_dir / f'{stem}_recon.png'
        if not veg.exists():
            continue

        # Look up camera parameters from the view label
        if stem not in CAPTURE_VIEWS:
            print(f'\n  Skipping {stem}: no camera params (not in CAPTURE_VIEWS)')
            continue
        az, el, dist = CAPTURE_VIEWS[stem]

        print(f'\n  Analysing: {stem}  (az={az}° el={el}° d={dist}m)')
        res = analyse_pair(nv, veg, recon if recon.exists() else None,
                           az=az, el=el, dist=dist)
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
        plot_mtf(res, out_dir / f'mtf_{stem}.png', view_label=stem)

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
