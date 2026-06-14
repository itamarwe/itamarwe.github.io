"""
Gaussian Splatting Under-Vegetation Benchmark

Evaluates reconstruction difficulty by comparing paired images (with/without
vegetation) and computing per-view metrics on the soldier region.

Inputs  : paired images in sample_images/  (from capture_views.py)
Outputs : benchmark_report.json + benchmark_summary.png

Usage:
    python benchmark.py [--images DIR] [--out DIR]

Metrics
-------
For each camera view:
  occlusion_ratio   fraction of soldier-region pixels that differ significantly
                    between veg/no-veg renders (proxy for hidden pixels)
  psnr              peak signal-to-noise ratio of full frame (veg vs. no-veg)
  ssim              structural similarity index of full frame
  soldier_psnr      PSNR restricted to the central soldier ROI
  soldier_ssim      SSIM restricted to the central soldier ROI

Summary stats:
  mean/min/max across all views at each elevation tier (top/high/mid/low)
  scene_difficulty  composite score [0,1] — higher = harder for a reconstruction
                    algorithm (more occlusion, less angular diversity)
"""

import argparse
import json
import math
import pathlib
import re
import sys

import numpy as np

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow required: pip install Pillow")

try:
    from skimage.metrics import structural_similarity as _ssim, peak_signal_noise_ratio as _psnr
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False
    print("Warning: scikit-image not installed — SSIM/PSNR computed with numpy fallback.")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("Warning: matplotlib not installed — skipping summary figure.")

# ─── Palette (3B1B style) ─────────────────────────────────────────────────────
BG  = "#0e1116"
CY  = "#3fc1ff"
GLD = "#ffd166"
GRN = "#7CFC8A"
RED = "#ff5a5a"
PRP = "#b48cff"
TXT = "#ededed"
MUT = "#8b95a5"

SCRIPT_DIR = pathlib.Path(__file__).parent

# ─── Elevation tiers ─────────────────────────────────────────────────────────
def el_tier(label: str) -> str:
    if "topdown" in label: return "top (el≥78°)"
    if "high"    in label: return "high (el≈62°)"
    if "oblique" in label: return "mid (el≈42°)"
    if "low"     in label: return "low (el≈18°)"
    return "other"

# ─── Metrics ─────────────────────────────────────────────────────────────────
def to_float(img: np.ndarray) -> np.ndarray:
    return img.astype(np.float32) / 255.0

def soldier_roi(h: int, w: int):
    """Central crop that covers the soldier (roughly middle 30% × 40%)."""
    r0 = int(h * 0.28); r1 = int(h * 0.78)
    c0 = int(w * 0.35); c1 = int(w * 0.65)
    return slice(r0, r1), slice(c0, c1)

def psnr_np(a: np.ndarray, b: np.ndarray) -> float:
    mse = np.mean((a - b) ** 2)
    if mse < 1e-12: return 100.0
    return float(10 * math.log10(1.0 / mse))

def ssim_np(a: np.ndarray, b: np.ndarray) -> float:
    """Simple luminance SSIM (channel-averaged, no skimage fallback)."""
    ag = a.mean(axis=2); bg_ = b.mean(axis=2)
    mu_a = ag.mean(); mu_b = bg_.mean()
    sig_a = ag.std(); sig_b = bg_.std()
    sig_ab = np.mean((ag - mu_a) * (bg_ - mu_b))
    C1, C2 = 0.01**2, 0.03**2
    return float((2*mu_a*mu_b + C1) * (2*sig_ab + C2) /
                 ((mu_a**2 + mu_b**2 + C1) * (sig_a**2 + sig_b**2 + C2)))

def compute_metrics(veg_img: np.ndarray, noveg_img: np.ndarray) -> dict:
    H, W = veg_img.shape[:2]
    rs, cs = soldier_roi(H, W)

    veg_f   = to_float(veg_img)
    noveg_f = to_float(noveg_img)

    # Occlusion proxy: pixels where brightness differs by >15%
    diff = np.abs(veg_f - noveg_f).mean(axis=2)
    occ  = float((diff > 0.15).mean())

    # Full-frame metrics
    if HAS_SKIMAGE:
        psnr_full = float(_psnr(noveg_f, veg_f, data_range=1.0))
        ssim_full = float(_ssim(noveg_f, veg_f, data_range=1.0, channel_axis=2))
    else:
        psnr_full = psnr_np(noveg_f, veg_f)
        ssim_full = ssim_np(noveg_f, veg_f)

    # Soldier-region metrics
    veg_roi   = veg_f[rs, cs]
    noveg_roi = noveg_f[rs, cs]
    if HAS_SKIMAGE:
        s_psnr = float(_psnr(noveg_roi, veg_roi, data_range=1.0))
        s_ssim = float(_ssim(noveg_roi, veg_roi, data_range=1.0, channel_axis=2))
    else:
        s_psnr = psnr_np(noveg_roi, veg_roi)
        s_ssim = ssim_np(noveg_roi, veg_roi)

    return {
        "occlusion_ratio": round(occ,  4),
        "psnr":            round(psnr_full, 2),
        "ssim":            round(ssim_full, 4),
        "soldier_psnr":    round(s_psnr,  2),
        "soldier_ssim":    round(s_ssim,  4),
    }

# ─── Summary figure ───────────────────────────────────────────────────────────
def make_figure(results: list[dict], pairs: list, out_dir: pathlib.Path):
    if not HAS_MPL: return

    labels    = [r["label"] for r in results]
    occlusion = [r["occlusion_ratio"] for r in results]
    sol_psnr  = [r["soldier_psnr"]    for r in results]
    sol_ssim  = [r["soldier_ssim"]    for r in results]

    # Tier colour map
    tier_colors = {
        "top (el≥78°)":  RED,
        "high (el≈62°)": GLD,
        "mid (el≈42°)":  CY,
        "low (el≈18°)":  GRN,
        "other":         PRP,
    }
    bar_colors = [tier_colors.get(el_tier(l), PRP) for l in labels]

    fig = plt.figure(figsize=(18, 13), facecolor=BG)
    gs  = gridspec.GridSpec(3, 3, figure=fig, hspace=0.45, wspace=0.35)

    ax_occ  = fig.add_subplot(gs[0, :])
    ax_psnr = fig.add_subplot(gs[1, :2])
    ax_ssim = fig.add_subplot(gs[1, 2])

    def style_ax(ax, title, ylabel):
        ax.set_facecolor(BG)
        ax.spines[["top","right"]].set_visible(False)
        ax.spines[["left","bottom"]].set_color(MUT)
        ax.tick_params(colors=MUT, labelsize=8)
        ax.set_title(title, color=TXT, fontsize=11, pad=6)
        ax.set_ylabel(ylabel, color=MUT, fontsize=9)

    x = np.arange(len(labels))
    ax_occ.bar(x, occlusion, color=bar_colors, alpha=0.9, width=0.7)
    ax_occ.axhline(np.mean(occlusion), color=TXT, lw=1, ls="--", alpha=0.6, label=f"mean={np.mean(occlusion):.2f}")
    ax_occ.set_xticks(x); ax_occ.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax_occ.set_ylim(0, 1); ax_occ.legend(fontsize=8, labelcolor=TXT, facecolor=BG, edgecolor=MUT)
    style_ax(ax_occ, "Per-view Occlusion Ratio  (fraction of soldier ROI altered by vegetation)", "occlusion ratio")

    ax_psnr.bar(x[: len(sol_psnr)], sol_psnr, color=bar_colors, alpha=0.9, width=0.7)
    ax_psnr.set_xticks(x); ax_psnr.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax_psnr.legend(handles=[
        plt.Rectangle((0,0),1,1, color=c, label=t) for t, c in tier_colors.items()
    ], fontsize=7, labelcolor=TXT, facecolor=BG, edgecolor=MUT, loc="upper right")
    style_ax(ax_psnr, "Soldier-region PSNR  (veg vs. no-veg,  higher = easier to reconstruct)", "dB")

    ax_ssim.bar(x[: len(sol_ssim)], sol_ssim, color=bar_colors, alpha=0.9, width=0.7)
    ax_ssim.set_xticks(x); ax_ssim.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax_ssim.set_ylim(0, 1)
    style_ax(ax_ssim, "Soldier SSIM", "SSIM")

    # Sample pair panel
    if pairs:
        ax_pairs = [fig.add_subplot(gs[2, i]) for i in range(min(3, len(pairs)))]
        for ax, (lbl, vp, np_) in zip(ax_pairs, pairs[:3]):
            # side by side
            combined = np.concatenate([vp, np_], axis=1)
            ax.imshow(combined)
            ax.set_title(f"{lbl}\nveg | no-veg", color=TXT, fontsize=7, pad=3)
            ax.axis("off")

    # Legend text
    fig.text(0.01, 0.01, "Colour key: RED=top-down  GOLD=high oblique  CYAN=mid  GREEN=low",
             color=MUT, fontsize=7)

    out_path = out_dir / "benchmark_summary.png"
    fig.savefig(out_path, dpi=140, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  Summary figure → {out_path}")

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default=str(SCRIPT_DIR / "sample_images"))
    ap.add_argument("--out",    default=str(SCRIPT_DIR))
    args = ap.parse_args()

    img_dir = pathlib.Path(args.images)
    out_dir  = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    veg_files = sorted(img_dir.glob("*_veg.png"))
    if not veg_files:
        sys.exit(f"No *_veg.png files found in {img_dir}. Run capture_views.py first.")

    results = []
    pairs   = []

    for veg_path in veg_files:
        label     = re.sub(r"_veg$", "", veg_path.stem)
        noveg_path = img_dir / f"{label}_noveg.png"
        if not noveg_path.exists():
            print(f"  SKIP {label}: no-veg image missing")
            continue

        veg_arr   = np.array(Image.open(veg_path).convert("RGB"))
        noveg_arr = np.array(Image.open(noveg_path).convert("RGB"))

        if veg_arr.shape != noveg_arr.shape:
            print(f"  SKIP {label}: shape mismatch {veg_arr.shape} vs {noveg_arr.shape}")
            continue

        m = compute_metrics(veg_arr, noveg_arr)
        m["label"] = label
        m["tier"]  = el_tier(label)
        results.append(m)

        # Downscale for figure panel
        h, w = veg_arr.shape[:2]
        small_h = 120
        ratio   = small_h / h
        small_w = int(w * ratio)
        from PIL import Image as PILImage
        vp = np.array(PILImage.fromarray(veg_arr).resize((small_w, small_h)))
        np_ = np.array(PILImage.fromarray(noveg_arr).resize((small_w, small_h)))
        pairs.append((label, vp, np_))

        print(f"  {label:35s}  occ={m['occlusion_ratio']:.3f}  "
              f"sol_psnr={m['soldier_psnr']:5.1f}dB  sol_ssim={m['soldier_ssim']:.3f}")

    if not results:
        sys.exit("No valid pairs found.")

    # Tier summaries
    tiers = {}
    for r in results:
        tiers.setdefault(r["tier"], []).append(r)

    tier_summary = {}
    for tier, rs in tiers.items():
        tier_summary[tier] = {
            "n": len(rs),
            "mean_occlusion":   round(np.mean([r["occlusion_ratio"] for r in rs]), 3),
            "mean_soldier_psnr": round(np.mean([r["soldier_psnr"]   for r in rs]), 2),
            "mean_soldier_ssim": round(np.mean([r["soldier_ssim"]   for r in rs]), 3),
        }

    # Scene difficulty: high occlusion + top-down views dominate
    occ_all  = np.array([r["occlusion_ratio"] for r in results])
    psnr_all = np.array([r["soldier_psnr"]    for r in results])
    # Normalise PSNR: 40dB = easy (0.0), 10dB = hard (1.0)
    psnr_norm = np.clip((40 - psnr_all) / 30, 0, 1)
    difficulty = float(np.mean(occ_all * 0.5 + psnr_norm * 0.5))

    report = {
        "n_views":        len(results),
        "scene_difficulty": round(difficulty, 3),
        "views":          results,
        "tier_summary":   tier_summary,
        "interpretation": {
            "occlusion_ratio": "fraction of ROI pixels significantly altered by vegetation (0=clear, 1=fully hidden)",
            "soldier_psnr":    "PSNR of soldier crop between veg and no-veg renders (lower = harder reconstruction)",
            "soldier_ssim":    "SSIM of soldier crop (lower = harder reconstruction)",
            "scene_difficulty": "composite [0,1]; >0.5 = significantly challenging for standard 3DGS",
        },
    }

    report_path = out_dir / "benchmark_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Report → {report_path}")
    print(f"  Scene difficulty score: {difficulty:.3f}  (0=easy, 1=fully occluded)")
    print(f"\n  Tier breakdown:")
    for tier, ts in tier_summary.items():
        print(f"    {tier:20s}  n={ts['n']}  occ={ts['mean_occlusion']:.3f}  "
              f"PSNR={ts['mean_soldier_psnr']:.1f}dB  SSIM={ts['mean_soldier_ssim']:.3f}")

    make_figure(results, pairs, out_dir)

if __name__ == "__main__":
    main()
