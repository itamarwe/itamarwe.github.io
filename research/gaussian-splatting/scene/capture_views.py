"""
Capture multi-view images of the forest scene (with and without vegetation)
for Gaussian Splatting benchmark generation.

Usage:
    python capture_views.py [--port PORT] [--out DIR] [--width W] [--height H]

Requires: Python ≥ 3.9, a running local server (starts one automatically).
Chrome binary: /opt/pw-browsers/chromium-*/chrome-linux/chrome
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
# Each entry: (label, azimuth_deg, elevation_deg, distance, wind_time)
VIEWS = [
    # Top-down — hardest for reconstruction (soldier almost hidden by canopy)
    ("topdown",      0,  82, 18, 0.0),
    # High oblique — partial canopy visibility
    ("high_oblique_N",   0,  62, 20, 1.0),
    ("high_oblique_E",  90,  62, 20, 1.0),
    ("high_oblique_S", 180,  62, 20, 2.0),
    ("high_oblique_W", 270,  62, 20, 2.0),
    # Medium oblique — typical drone survey angle
    ("oblique_NE",   45,  42, 18, 3.0),
    ("oblique_SE",  135,  42, 18, 3.5),
    ("oblique_SW",  225,  42, 18, 4.0),
    ("oblique_NW",  315,  42, 18, 4.5),
    # Low angle — side views, soldier mostly visible through trunks
    ("low_N",    0,  18, 16, 5.0),
    ("low_E",   90,  18, 16, 5.5),
    ("low_S",  180,  18, 16, 6.0),
    ("low_W",  270,  18, 16, 6.5),
    # Extra high: near vertical at different times (wind variation)
    ("topdown_t1",  45,  78, 18, 2.5),
    ("topdown_t2", 135,  78, 18, 5.0),
    ("topdown_t3", 225,  78, 18, 7.5),
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
    ap.add_argument("--port",   type=int, default=7890)
    ap.add_argument("--out",    type=str, default=str(OUT_DIR))
    ap.add_argument("--width",  type=int, default=1280)
    ap.add_argument("--height", type=int, default=760)
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Starting HTTP server on port {args.port} (serving {PUBLIC}) ...")
    start_server(args.port)
    time.sleep(0.5)

    base = f"http://127.0.0.1:{args.port}/forest-scene/index.html"
    total = len(VIEWS) * 2  # with + without vegetation
    done  = 0

    for label, az, el, dist, t in VIEWS:
        for veg in (1, 0):
            veg_tag = "veg" if veg else "noveg"
            fname   = f"{label}_{veg_tag}.png"
            url = (f"{base}?az={az}&el={el}&d={dist}&t={t}"
                   f"&veg={veg}&ui=0&interactive=0")
            out_path = out / fname
            ok = capture(url, out_path, args.width, args.height)
            done += 1
            status = "OK" if ok else "FAIL"
            print(f"  [{done:2d}/{total}] {fname:40s} {status}")

    print(f"\nDone. {done} images → {out}/")

if __name__ == "__main__":
    main()
