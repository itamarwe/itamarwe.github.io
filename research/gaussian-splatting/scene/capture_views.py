"""
Capture training views + ground truth for the USAF 1951 3DGS benchmark.

Pipeline
--------
1. Capture N training views (all veg=1, with straw at --cov occlusion)
2. Capture ONE ground-truth view (topdown, veg=0) for MTF reference
3. Export COLMAP-format camera poses so 3DGS can be trained without COLMAP SfM
4. After 3DGS training, put rendered top-down as topdown_recon.png and run benchmark.py

Usage
-----
    # 50% occlusion experiment (default)
    python capture_views.py --port 7895 --out training_50 --cov 0.50

    # Control: 0% occlusion
    python capture_views.py --port 7896 --out training_00 --cov 0.00

    # Also export COLMAP poses
    python capture_views.py --out training_50 --poses

How many views?
---------------
For a flat target under 50% straw coverage, each view sees ~50% of the
surface. To achieve 99% surface visibility from N independent views:
    1 - 0.5^N ≥ 0.99  →  N ≥ 7 (minimum)

3DGS additionally needs dense angular overlap for reliable triangulation
of the straw geometry. 40 views (4–8 azimuths × 5 elevation tiers) is
the empirical sweet spot before diminishing returns on flat-target scenes.

Requires: Python ≥ 3.9; Chrome binary auto-detected.
"""

import argparse
import glob
import http.server
import json
import math
import os
import pathlib
import shutil
import subprocess
import sys
import threading
import time

# ─── Paths ───────────────────────────────────────────────────────────────────
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PUBLIC    = REPO_ROOT / "public"
OUT_DIR   = pathlib.Path(__file__).parent / "sample_images"

def find_chrome():
    candidates = [
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ]
    candidates += glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    sys.exit("Chrome/Chromium not found. Install or set CHROME env var.")

CHROME = os.environ.get("CHROME") or find_chrome()

# ─── Camera parameters ───────────────────────────────────────────────────────
# Three.js scene FOV (vertical, degrees)
CAM_FOV_V = 52.0

# ─── Training view grid ──────────────────────────────────────────────────────
# 40 views: denser azimuths at lower elevations where the straw roof subtends
# a larger solid angle and more views are needed to peek through gaps.
#
# el=82°: nadir ring — 4 azimuths (N/E/S/W)         d=11 m
# el=70°: high ring  — 4 azimuths                    d=12 m
# el=57°: mid-high   — 8 azimuths (every 45°)        d=13 m
# el=44°: mid-low    — 8 azimuths                    d=14 m
# el=30°: low ring   — 8 azimuths                    d=15 m
# el=20°: grazing    — 8 azimuths                    d=16 m
#
# Total: 4 + 4 + 8×4 = 40 training views (all captured with veg=1)

def _ring(el, n_az, d, label_prefix):
    step = 360 // n_az
    return [(f"{label_prefix}_{i*step:03d}", i * step, el, d)
            for i in range(n_az)]

TRAINING_VIEWS = (
    _ring(82,  4, 11, "el82") +
    _ring(70,  4, 12, "el70") +
    _ring(57,  8, 13, "el57") +
    _ring(44,  8, 14, "el44") +
    _ring(30,  8, 15, "el30") +
    _ring(20,  8, 16, "el20")
)
assert len(TRAINING_VIEWS) == 40, len(TRAINING_VIEWS)

# Ground truth: top-down, no vegetation.  This is the MTF reference image.
GT_VIEW = ("topdown_gt", 0, 88, 11)

# ─── HTTP Server ──────────────────────────────────────────────────────────────
class SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_): pass

def start_server(port: int):
    os.chdir(PUBLIC)
    server = http.server.HTTPServer(("127.0.0.1", port), SilentHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server

# ─── Headless capture ────────────────────────────────────────────────────────
def capture(url: str, out_path: pathlib.Path, width: int, height: int) -> bool:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp.png")
    cmd = [
        CHROME,
        "--headless=new",
        "--no-sandbox",
        "--use-gl=angle",
        "--use-angle=swiftshader",
        "--enable-unsafe-swiftshader",
        f"--window-size={width},{height}",
        "--virtual-time-budget=4000",
        f"--screenshot={tmp}",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"  Chrome stderr: {result.stderr[:300]}")
        return False
    if tmp.exists():
        shutil.move(str(tmp), str(out_path))
        return True
    return False

# ─── COLMAP pose export ───────────────────────────────────────────────────────
def _camera_basis(az_deg, el_deg, dist):
    """Return (cam_pos, right, up, z_axis) matching Three.js lookAt(0,0,0)."""
    az = math.radians(az_deg)
    el = math.radians(el_deg)
    pos = [
        dist * math.cos(el) * math.sin(az),
        dist * math.sin(el),
        dist * math.cos(el) * math.cos(az),
    ]
    # forward = normalize(origin - pos)
    norm = math.sqrt(sum(x**2 for x in pos))
    fwd = [-x / norm for x in pos]
    wu = [0, 1, 0]
    # right = cross(world_up, z_axis)  where z_axis = -fwd
    z = [x / norm for x in pos]   # z_axis (away from scene)
    right = [
        wu[1]*z[2] - wu[2]*z[1],
        wu[2]*z[0] - wu[0]*z[2],
        wu[0]*z[1] - wu[1]*z[0],
    ]
    rn = math.sqrt(sum(x**2 for x in right))
    right = [x / rn for x in right]
    up = [                         # cam up = cross(z_axis, right)
        z[1]*right[2] - z[2]*right[1],
        z[2]*right[0] - z[0]*right[2],
        z[0]*right[1] - z[1]*right[0],
    ]
    return pos, right, up, z


def _rot_to_quat(R):
    """3×3 row-major rotation matrix → (qw, qx, qy, qz)."""
    r00,r01,r02 = R[0]
    r10,r11,r12 = R[1]
    r20,r21,r22 = R[2]
    tr = r00 + r11 + r22
    if tr > 0:
        s = 0.5 / math.sqrt(tr + 1.0)
        w = 0.25 / s
        x = (r21 - r12) * s
        y = (r02 - r20) * s
        z = (r10 - r01) * s
    elif r00 > r11 and r00 > r22:
        s = 2.0 * math.sqrt(1.0 + r00 - r11 - r22)
        w = (r21 - r12) / s
        x = 0.25 * s
        y = (r01 + r10) / s
        z = (r02 + r20) / s
    elif r11 > r22:
        s = 2.0 * math.sqrt(1.0 + r11 - r00 - r22)
        w = (r02 - r20) / s
        x = (r01 + r10) / s
        y = 0.25 * s
        z = (r12 + r21) / s
    else:
        s = 2.0 * math.sqrt(1.0 + r22 - r00 - r11)
        w = (r10 - r01) / s
        x = (r02 + r20) / s
        y = (r12 + r21) / s
        z = 0.25 * s
    return w, x, y, z


def export_colmap_poses(views, out_dir: pathlib.Path, img_w: int, img_h: int,
                        prefix: str = ""):
    """
    Write sparse/0/{cameras,images,points3D}.txt in COLMAP format.
    All views share one PINHOLE camera (same intrinsics).
    points3D.txt is empty — 3DGS can start from a random initialisation
    or a synthetic ground-plane point cloud.
    """
    sparse = out_dir / "sparse" / "0"
    sparse.mkdir(parents=True, exist_ok=True)

    # Intrinsics: PINHOLE  f_x f_y c_x c_y
    f = (img_h / 2) / math.tan(math.radians(CAM_FOV_V / 2))
    cx, cy = img_w / 2, img_h / 2

    with open(sparse / "cameras.txt", "w") as fp:
        fp.write("# Camera list\n")
        fp.write(f"1 PINHOLE {img_w} {img_h} {f:.4f} {f:.4f} {cx:.4f} {cy:.4f}\n")

    with open(sparse / "images.txt", "w") as fp:
        fp.write("# Image list\n")
        for img_id, (label, az, el, dist) in enumerate(views, 1):
            pos, right, up, z_axis = _camera_basis(az, el, dist)
            # Rotation matrix R (world→camera): rows are right, up, z_axis
            R = [right, up, z_axis]
            qw, qx, qy, qz = _rot_to_quat(R)
            # Translation: t = -R @ pos
            tx = -(R[0][0]*pos[0] + R[0][1]*pos[1] + R[0][2]*pos[2])
            ty = -(R[1][0]*pos[0] + R[1][1]*pos[1] + R[1][2]*pos[2])
            tz = -(R[2][0]*pos[0] + R[2][1]*pos[1] + R[2][2]*pos[2])
            fname = f"{prefix}{label}.png"
            fp.write(f"{img_id} {qw:.8f} {qx:.8f} {qy:.8f} {qz:.8f} "
                     f"{tx:.6f} {ty:.6f} {tz:.6f} 1 {fname}\n\n")

    with open(sparse / "points3D.txt", "w") as fp:
        fp.write("# Empty — use random or ground-plane initialisation in 3DGS\n")

    # Also write a JSON summary for convenience
    meta = {
        "camera": {
            "model": "PINHOLE",
            "width": img_w, "height": img_h,
            "f": round(f, 4), "cx": cx, "cy": cy,
            "fov_v_deg": CAM_FOV_V,
        },
        "views": [
            {"label": lbl, "az_deg": az, "el_deg": el, "dist_m": d,
             "filename": f"{prefix}{lbl}.png"}
            for lbl, az, el, d in views
        ],
    }
    (out_dir / "camera_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"  COLMAP poses → {sparse}/  ({len(views)} images, f={f:.1f}px)")

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--port",   type=int,   default=7895)
    ap.add_argument("--out",    type=str,   default=str(OUT_DIR))
    ap.add_argument("--cov",    type=float, default=0.50,
                    help="Straw coverage 0–1 (default 0.50; use 0.00 for control)")
    ap.add_argument("--width",  type=int,   default=1280)
    ap.add_argument("--height", type=int,   default=760)
    ap.add_argument("--poses",  action="store_true",
                    help="Export COLMAP-format camera poses alongside images")
    ap.add_argument("--gt-only", action="store_true",
                    help="Only capture the ground-truth top-down image (no training views)")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Starting HTTP server on port {args.port} (serving {PUBLIC}) ...")
    start_server(args.port)
    time.sleep(0.8)

    base = f"http://127.0.0.1:{args.port}/forest-scene/index.html"

    views_to_capture = [] if args.gt_only else list(TRAINING_VIEWS)

    total = len(views_to_capture) + 1   # +1 for ground truth
    done  = 0

    # ── Capture training views (veg=1) ────────────────────────────────────────
    for label, az, el, dist in views_to_capture:
        url  = (f"{base}?az={az}&el={el}&d={dist}"
                f"&cov={args.cov}&veg=1&ui=0&interactive=0")
        ok = capture(url, out / f"{label}.png", args.width, args.height)
        done += 1
        print(f"  [{done:2d}/{total}] {label:25s} cov={args.cov:.0%}  {'OK' if ok else 'FAIL'}")

    # ── Capture ground truth (veg=0, top-down) ────────────────────────────────
    gt_label, gt_az, gt_el, gt_dist = GT_VIEW
    gt_url = (f"{base}?az={gt_az}&el={gt_el}&d={gt_dist}"
              f"&cov=0&veg=0&ui=0&interactive=0")
    ok = capture(gt_url, out / f"{gt_label}.png", args.width, args.height)
    done += 1
    print(f"  [{done:2d}/{total}] {gt_label:25s} GT (no veg)  {'OK' if ok else 'FAIL'}")

    # ── Export COLMAP poses ───────────────────────────────────────────────────
    if args.poses and not args.gt_only:
        export_colmap_poses(views_to_capture, out, args.width, args.height)

    cov_pct = int(args.cov * 100)
    print(f"\nDone. {done} images → {out}/")
    print(f"\nNext steps:")
    print(f"  1. Run 3DGS on {out}/*.png (training views) using poses in {out}/sparse/")
    print(f"  2. Render the top-down view → {out}/topdown_recon.png")
    print(f"  3. python benchmark.py --recon {out}/topdown_recon.png \\")
    print(f"                         --gt    {out}/{gt_label}.png")


if __name__ == "__main__":
    main()
