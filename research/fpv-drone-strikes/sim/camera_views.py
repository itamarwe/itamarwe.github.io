"""
Sanity-check the VGGT reconstruction by re-projecting the recovered point cloud
through the recovered camera poses, and compare each synthetic view to the real
FPV frame it came from.

If the geometry is right, projecting the whole point cloud through camera i should
roughly reproduce FPV frame i (right-side up). This both (a) confirms the scene is
not flipped and (b) makes the point cloud legible: you see what the drone "saw".

Pinhole projection is exact; the only free parameter is focal length (VGGT's
intrinsics aren't carried in the .glb), which we auto-fit so the points fill the
frame. Output: public/img/fpv-drone-strikes/camera_views.png
"""
import os, numpy as np, trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.image import imread

HERE = os.path.dirname(os.path.abspath(__file__))
VGGT = os.path.join(HERE, "..", "vggt")
OUT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "public", "img", "fpv-drone-strikes"))
BG = "#000000"; TXT = "#ededed"; MUTED = "#8b95a5"

def load_glb():
    s = trimesh.load(os.path.join(VGGT, "vggt_scene.glb"))
    name2T = {}
    for node in s.graph.nodes:
        try:
            T, geom = s.graph[node]
        except Exception:
            continue
        if geom is not None:
            name2T[geom] = np.asarray(T)
    cams = sorted([n for n in s.geometry if n != "geometry_0"],
                  key=lambda n: int(n.split("_")[1]))
    poses = [name2T[n] for n in cams]
    pc = s.geometry["geometry_0"]
    pts = trimesh.transformations.transform_points(pc.vertices, name2T.get("geometry_0", np.eye(4)))
    cols = np.asarray(pc.colors)[:, :3] / 255.0 if getattr(pc, "colors", None) is not None else None
    ok = np.isfinite(pts).all(1)
    pts, cols = pts[ok], (cols[ok] if cols is not None else None)
    return pts, cols, poses

def project(pts, cols, T, aspect=848 / 478):
    """Pinhole-project world points into camera T's image plane (y-up)."""
    R, C = T[:3, :3], T[:3, 3]
    right, up, fwd = R[:, 0], R[:, 1], R[:, 2]
    d = pts - C
    z = d @ fwd
    front = z > 1e-6
    d, z, c = d[front], z[front], (cols[front] if cols is not None else None)
    x = (d @ right) / z
    y = (d @ up) / z
    # auto-fit focal so the bulk of points fill the frame
    fx = 0.9 / (np.percentile(np.abs(x), 96) + 1e-6)
    fy = fx                                   # square pixels
    u, v = fx * x, fy * y
    keep = (np.abs(u) < aspect) & (np.abs(v) < 1.0)
    # nearer points drawn last (on top)
    order = np.argsort(-z[keep])
    u, v = u[keep][order], v[keep][order]
    c = c[keep][order] if c is not None else None
    return u, v, c, aspect

def main():
    pts, cols, poses = load_glb()
    idxs = [3, 13, 25, 35]                     # spread across the flight
    fig, axes = plt.subplots(2, len(idxs), figsize=(14, 4.6), facecolor=BG)
    for col, i in enumerate(idxs):
        # real frame
        axT = axes[0, col]; axT.set_facecolor(BG); axT.axis("off")
        frame = imread(os.path.join(VGGT, "frames", f"f_{i+1:03d}.jpg"))
        axT.imshow(frame)
        if col == 0:
            axT.set_ylabel("")
        axT.set_title(f"real FPV frame {i+1}", color=TXT, fontsize=11)

        # synthetic view = point cloud projected through pose i
        axB = axes[1, col]; axB.set_facecolor(BG)
        u, v, c, aspect = project(pts, cols, poses[i])
        axB.scatter(u, v, s=1.2, c=(c if c is not None else MUTED), linewidths=0, alpha=0.8)
        axB.set_xlim(-aspect, aspect); axB.set_ylim(-1, 1)
        axB.set_aspect("equal"); axB.set_xticks([]); axB.set_yticks([])
        for sp in axB.spines.values():
            sp.set_color("#333a45")
        axB.set_title("point cloud, same viewpoint", color=MUTED, fontsize=11)

    fig.suptitle("The reconstruction, seen from the drone's own recovered camera poses "
                 "(sky stays up — the scene is not flipped)", color=TXT, fontsize=12.5)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(os.path.join(OUT, "camera_views.png"), dpi=150, facecolor=BG)
    print("saved camera_views.png")

if __name__ == "__main__":
    main()
