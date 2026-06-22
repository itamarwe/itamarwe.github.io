"""
Build an OpenSplat (nerfstudio-format) project from a capture_views.py output dir.

OpenSplat (https://github.com/pierotofy/OpenSplat) is a Metal/MPS-capable 3DGS
trainer that runs on Apple Silicon — unlike stock nerfstudio/gsplat, whose CUDA
kernels need nvcc. This script turns the synthetic captures + known camera poses
into the `transforms.json` + seed point cloud OpenSplat's nerfstudio loader wants.

What it writes into <train_dir>:
  - transforms.json   : 40 training frames (veg) + 1 withheld top-down frame
                        (topdown_gt.png), intrinsics, and ply_file_path.
  - sparse_pc.ply     : ascii point cloud seeded on the y=0 ground plane.
                        OpenSplat does NOT support random init, and the USAF
                        target is a flat plane, so a ground-plane seed is the
                        principled initialisation here.

Camera convention
-----------------
OpenSplat's loader expects transform_matrix as camera->world in OpenGL
convention (x right, y up, z pointing back, away from the scene). That is
exactly the (right, up, z_axis, pos) basis capture_views.py already computes,
so the c2w columns are [right, up, z_axis, pos].

Then:
  ./opensplat <train_dir> -n N --val --val-image topdown_gt.png \
              --val-render <dir>
  # final render in <dir> is the novel top-down -> topdown_recon.png
"""

import argparse
import json
import math
import pathlib
import random

# Top-down ground-truth view (must match GT_VIEW in capture_views.py)
GT_VIEW = ("topdown_gt", 0, 88, 11)
TARGET_SIZE_M = 5.0


def camera_basis(az_deg, el_deg, dist):
    az = math.radians(az_deg)
    el = math.radians(el_deg)
    pos = [
        dist * math.cos(el) * math.sin(az),
        dist * math.sin(el),
        dist * math.cos(el) * math.cos(az),
    ]
    n = math.sqrt(sum(x * x for x in pos))
    z = [x / n for x in pos]                      # away from scene (OpenGL +z)
    wu = [0.0, 1.0, 0.0]
    right = [wu[1] * z[2] - wu[2] * z[1],
             wu[2] * z[0] - wu[0] * z[2],
             wu[0] * z[1] - wu[1] * z[0]]
    rn = math.sqrt(sum(x * x for x in right))
    right = [x / rn for x in right]
    up = [z[1] * right[2] - z[2] * right[1],
          z[2] * right[0] - z[0] * right[2],
          z[0] * right[1] - z[1] * right[0]]
    return pos, right, up, z


def c2w(az, el, dist):
    pos, right, up, z = camera_basis(az, el, dist)
    return [
        [right[0], up[0], z[0], pos[0]],
        [right[1], up[1], z[1], pos[1]],
        [right[2], up[2], z[2], pos[2]],
        [0.0, 0.0, 0.0, 1.0],
    ]


def write_ply(path, n_points, half, color=(160, 160, 160), y_jitter=0.02):
    rng = random.Random(42)
    lines = ["ply", "format ascii 1.0", f"element vertex {n_points}",
             "property float x", "property float y", "property float z",
             "property uchar red", "property uchar green", "property uchar blue",
             "end_header"]
    r, g, b = color
    for _ in range(n_points):
        x = rng.uniform(-half, half)
        z = rng.uniform(-half, half)
        y = rng.uniform(-y_jitter, y_jitter)
        lines.append(f"{x:.5f} {y:.5f} {z:.5f} {r} {g} {b}")
    path.write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True, help="capture_views.py output dir")
    ap.add_argument("--points", type=int, default=30000)
    args = ap.parse_args()

    train = pathlib.Path(args.train)
    meta = json.loads((train / "camera_meta.json").read_text())
    cam = meta["camera"]

    frames = []
    for v in meta["views"]:
        frames.append({
            "file_path": v["filename"],
            "transform_matrix": c2w(v["az_deg"], v["el_deg"], v["dist_m"]),
        })
    # Withheld novel view: clean top-down (used only for validation/render).
    gl, ga, ge, gd = GT_VIEW
    frames.append({
        "file_path": f"{gl}.png",
        "transform_matrix": c2w(ga, ge, gd),
    })

    transforms = {
        "camera_model": "OPENCV",
        "w": cam["width"], "h": cam["height"],
        "fl_x": cam["f"], "fl_y": cam["f"],
        "cx": cam["cx"], "cy": cam["cy"],
        "k1": 0.0, "k2": 0.0, "p1": 0.0, "p2": 0.0,
        "ply_file_path": "sparse_pc.ply",
        "frames": frames,
    }
    (train / "transforms.json").write_text(json.dumps(transforms, indent=2))

    write_ply(train / "sparse_pc.ply", args.points, half=TARGET_SIZE_M / 2 + 0.2)

    print(f"  transforms.json -> {len(frames)} frames "
          f"(40 training + 1 withheld top-down)")
    print(f"  sparse_pc.ply   -> {args.points} ground-plane seed points")
    print(f"  f={cam['f']}px  {cam['width']}x{cam['height']}")


if __name__ == "__main__":
    main()
