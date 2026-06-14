"""
Capture multi-view images of the USAF 1951 target scene (with/without straw
occlusion) for the Gaussian Splatting benchmark.

Usage:
    python capture_views.py [--port PORT] [--out DIR] [--cov COV]
                            [--width W] [--height H]

Requires: Python ≥ 3.9; Chrome binary auto-detected.
"""

import argparse
import glob
import http.server
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

# Locate headless Chrome
def find_chrome():
    candidates = [
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ]
    # Playwright-installed Chromium
    candidates += glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    sys.exit("Chrome/Chromium not found. Install or set CHROME env var.")

CHROME = os.environ.get("CHROME") or find_chrome()

# ─── Camera views ─────────────────────────────────────────────────────────────
# Each entry: (label, azimuth_deg, elevation_deg, distance_m)
# Elevation tiers:
#   88° = near-vertical (canonical MTF measurement)
#   72° = high oblique  (accurate for most drones)
#   55° = mid oblique   (typical survey pass)
#   38° = low oblique   (steep look-down, heavy perspective)
#
# 4 azimuths per oblique tier (N/E/S/W) → even angular coverage for 3DGS
VIEWS = [
    # Near top-down — primary MTF measurement view
    ("topdown",         0,  88, 11),

    # High oblique  (el 72°)
    ("hi_N",            0,  72, 13),
    ("hi_E",           90,  72, 13),
    ("hi_S",          180,  72, 13),
    ("hi_W",          270,  72, 13),

    # Mid oblique  (el 55°) — typical drone survey
    ("mid_N",           0,  55, 14),
    ("mid_E",          90,  55, 14),
    ("mid_S",         180,  55, 14),
    ("mid_W",         270,  55, 14),

    # Low oblique  (el 38°) — steep angle, heavy foreshortening
    ("low_NE",         45,  38, 14),
    ("low_SE",        135,  38, 14),
    ("low_SW",        225,  38, 14),
    ("low_NW",        315,  38, 14),
]

# ─── HTTP Server ──────────────────────────────────────────────────────────────
class SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_): pass

def start_server(port: int):
    os.chdir(PUBLIC)
    server = http.server.HTTPServer(("127.0.0.1", port), SilentHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server

# ─── Capture ─────────────────────────────────────────────────────────────────
def capture(url: str, out_path: pathlib.Path, width: int, height: int):
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

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port",   type=int,   default=7895)
    ap.add_argument("--out",    type=str,   default=str(OUT_DIR))
    ap.add_argument("--cov",    type=float, default=0.50,
                    help="Straw coverage fraction 0–1 (default 0.50)")
    ap.add_argument("--width",  type=int,   default=1280)
    ap.add_argument("--height", type=int,   default=760)
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Starting HTTP server on port {args.port} (serving {PUBLIC}) ...")
    start_server(args.port)
    time.sleep(0.8)

    base  = f"http://127.0.0.1:{args.port}/forest-scene/index.html"
    total = len(VIEWS) * 2   # veg + noveg
    done  = 0

    for label, az, el, dist in VIEWS:
        for veg in (1, 0):
            tag      = "veg" if veg else "noveg"
            fname    = f"{label}_{tag}.png"
            url      = (f"{base}?az={az}&el={el}&d={dist}"
                        f"&cov={args.cov}&veg={veg}&ui=0&interactive=0")
            ok = capture(url, out / fname, args.width, args.height)
            done += 1
            print(f"  [{done:2d}/{total}] {fname:35s} {'OK' if ok else 'FAIL'}")

    print(f"\nDone. {done} images → {out}/")

if __name__ == "__main__":
    main()
