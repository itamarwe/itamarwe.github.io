"""
Multi-view ground-plane projection — stand-in for 3DGS reconstruction.

Since the USAF target is a flat texture at world y=0 and we know all 40
camera poses exactly, we can reconstruct the top-down view without training
a neural model:

  For each pixel in the output (top-down) image:
    1. Back-project the ray from the GT camera through that pixel
    2. Intersect it with the y=0 ground plane → world point (wx, 0, wz)
    3. Project that world point into every training view → sample RGB
    4. Pixel-wise MEDIAN across 40 views → output pixel

Why the median works:
  - The USAF target is at y=0 → projects to a CONSISTENT location
    in every training view (exactly where it should be).
  - Straw sticks are above y=0 → project to DIFFERENT locations
    depending on view angle (parallax).  They appear as outliers
    in the stack of 40 samples and are suppressed by the median.

This gives an "oracle" upper bound for reconstruction quality:
  best possible 3DGS result for a flat planar scene.

Usage
-----
    python reconstruct_mv.py --train /tmp/train_50 --out /tmp/train_50/topdown_recon.png
    python benchmark.py --recon /tmp/train_50/topdown_recon.png --gt /tmp/train_50/topdown_gt.png

For the 0% control:
    python reconstruct_mv.py --train /tmp/train_00 --out /tmp/train_00/topdown_recon.png
"""

import argparse
import json
import math
import pathlib
import sys
import time

import numpy as np
try:
    from PIL import Image
except ImportError:
    sys.exit("pip install Pillow")

# ── Scene / camera constants (must match index.html / capture_views.py) ───────
TARGET_SIZE_M = 5.0
CAM_FOV_V_DEG = 52.0

# Ground-truth view parameters (same as GT_VIEW in capture_views.py)
GT_AZ, GT_EL, GT_DIST = 0, 88, 11


def _camera_basis(az_deg, el_deg, dist):
    az = math.radians(az_deg)
    el = math.radians(el_deg)
    pos = np.array([
        dist * math.cos(el) * math.sin(az),
        dist * math.sin(el),
        dist * math.cos(el) * math.cos(az),
    ])
    z_axis = pos / np.linalg.norm(pos)       # away from scene
    world_up = np.array([0., 1., 0.])
    right = np.cross(world_up, z_axis)
    right /= np.linalg.norm(right)
    up = np.cross(z_axis, right)
    return pos, right, up, z_axis


def backproject_to_ground(az_deg, el_deg, dist, img_w, img_h):
    """
    For every pixel in the image captured at (az, el, dist), compute the
    3-D world point on the y=0 ground plane that the pixel sees.

    Returns
    -------
    wx, wz : (H, W) arrays of world X and Z coordinates
    valid  : (H, W) bool mask  (False where ray misses the target square
             or points away from the ground)
    """
    cam_pos, right, up, z_axis = _camera_basis(az_deg, el_deg, dist)
    f_v    = 1.0 / math.tan(math.radians(CAM_FOV_V_DEG) / 2)
    aspect = img_w / img_h

    ix = np.arange(img_w, dtype=float)
    iy = np.arange(img_h, dtype=float)
    IY, IX = np.meshgrid(iy, ix, indexing='ij')   # (H, W)

    x_ndc = 2 * IX / img_w - 1
    y_ndc = 1 - 2 * IY / img_h

    x_cam = x_ndc * aspect / f_v
    y_cam = y_ndc / f_v

    # World-space ray direction for each pixel
    # d = x_cam * right + y_cam * up - z_axis   (z_axis points away from scene)
    d = (x_cam[:, :, None] * right +
         y_cam[:, :, None] * up -
         z_axis)                                  # (H, W, 3)

    # Intersect with plane y=0:  cam_pos[1] + t * d[...,1] = 0
    d_y = d[..., 1]
    with np.errstate(divide='ignore', invalid='ignore'):
        t = -cam_pos[1] / d_y                      # (H, W)

    wx = cam_pos[0] + t * d[..., 0]
    wz = cam_pos[2] + t * d[..., 2]

    half = TARGET_SIZE_M / 2
    valid = (t > 0) & (wx >= -half) & (wx <= half) & (wz >= -half) & (wz <= half)
    return wx, wz, valid


def project_to_image(wx, wz, az_deg, el_deg, dist, img_w, img_h):
    """
    Project world points (wx, 0, wz) into the training image at (az, el, dist).

    Returns pixel_x, pixel_y arrays (H, W) and a validity mask.
    """
    cam_pos, right, up, z_axis = _camera_basis(az_deg, el_deg, dist)
    f_v    = 1.0 / math.tan(math.radians(CAM_FOV_V_DEG) / 2)
    aspect = img_w / img_h

    wx = np.asarray(wx)
    wz = np.asarray(wz)

    v = np.stack([wx - cam_pos[0],
                  -cam_pos[1] * np.ones_like(wx),
                  wz - cam_pos[2]], axis=-1)        # (H, W, 3)

    x_cam = (v * right).sum(axis=-1)
    y_cam = (v * up   ).sum(axis=-1)
    z_cam = -(v * z_axis).sum(axis=-1)              # positive = in front

    with np.errstate(divide='ignore', invalid='ignore'):
        pix_x = (x_cam / z_cam * (f_v / aspect) + 1) / 2 * img_w
        pix_y = (1 - y_cam / z_cam * f_v)         / 2 * img_h

    in_frame = (z_cam > 0) & (pix_x >= 0) & (pix_x < img_w) & \
               (pix_y >= 0) & (pix_y < img_h)
    return pix_x, pix_y, in_frame


def bilinear_sample(img: np.ndarray, px, py, valid_mask):
    """
    Bilinear sample from img (H, W, C) at float coordinates (px, py).
    Returns (H, W, C) float array; pixels outside valid_mask are NaN.
    """
    H, W, C = img.shape
    px = np.clip(px, 0, W - 1.001)
    py = np.clip(py, 0, H - 1.001)
    x0 = np.floor(px).astype(int)
    y0 = np.floor(py).astype(int)
    x1 = np.clip(x0 + 1, 0, W - 1)
    y1 = np.clip(y0 + 1, 0, H - 1)
    wx = (px - x0)[..., None]
    wy = (py - y0)[..., None]

    sample = (img[y0, x0] * (1 - wx) * (1 - wy) +
              img[y0, x1] *      wx  * (1 - wy) +
              img[y1, x0] * (1 - wx) *      wy  +
              img[y1, x1] *      wx  *      wy)

    sample = sample.astype(float)
    sample[~valid_mask] = np.nan
    return sample


def reconstruct(train_dir: pathlib.Path, out_path: pathlib.Path,
                gt_w: int = 1280, gt_h: int = 760):
    # Load camera metadata
    meta_path = train_dir / "camera_meta.json"
    if not meta_path.exists():
        sys.exit(f"camera_meta.json not found in {train_dir}. Run capture_views.py --poses first.")
    meta = json.loads(meta_path.read_text())
    views = meta["views"]

    print(f"  Loading {len(views)} training images ...")
    imgs = []
    for v in views:
        p = train_dir / v["filename"]
        if not p.exists():
            print(f"  Warning: {p} not found, skipping")
            imgs.append(None)
            continue
        imgs.append(np.array(Image.open(p).convert("RGB"), dtype=float))

    # Back-project GT top-down pixels → ground plane (y=0)
    print(f"  Back-projecting GT pixels to ground plane ...")
    wx, wz, gt_valid = backproject_to_ground(GT_AZ, GT_EL, GT_DIST, gt_w, gt_h)

    # For each training view: project ground points → training image → sample
    samples = []   # each entry: (H, W, 3) or None
    t0 = time.time()
    for i, (v, img) in enumerate(zip(views, imgs)):
        if img is None:
            continue
        tr_w, tr_h = img.shape[1], img.shape[0]
        px, py, in_frame = project_to_image(
            wx, wz, v["az_deg"], v["el_deg"], v["dist_m"], tr_w, tr_h)
        valid = gt_valid & in_frame
        sample = bilinear_sample(img, px, py, valid)
        samples.append(sample)
        if (i + 1) % 10 == 0:
            print(f"    {i+1}/{len(views)} views processed  ({time.time()-t0:.1f}s)")

    print(f"  Computing pixel-wise median across {len(samples)} views ...")
    stack = np.stack(samples, axis=0)   # (N, H, W, 3)

    # Median suppresses straw-stick outliers (they project to different
    # image locations from different view angles due to parallax).
    recon = np.nanmedian(stack, axis=0)  # (H, W, 3)

    # Fill any remaining NaN (pixels outside all training images) with grey
    nan_mask = np.isnan(recon).any(axis=-1)
    recon[nan_mask] = 180.0

    recon = np.clip(recon, 0, 255).astype(np.uint8)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(recon).save(out_path)
    print(f"  Reconstruction → {out_path}")
    print(f"  Total time: {time.time()-t0:.1f}s  |  "
          f"{nan_mask.sum()} pixels had no valid training view coverage")
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--train", required=True,
                    help="Directory with training images + camera_meta.json")
    ap.add_argument("--out",   required=True,
                    help="Output path for reconstructed top-down PNG")
    ap.add_argument("--width",  type=int, default=1280)
    ap.add_argument("--height", type=int, default=760)
    args = ap.parse_args()

    reconstruct(pathlib.Path(args.train), pathlib.Path(args.out),
                gt_w=args.width, gt_h=args.height)


if __name__ == "__main__":
    main()
