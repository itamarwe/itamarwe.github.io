"""
Sanity-check the VGGT reconstruction by re-projecting the recovered point cloud
through the recovered camera poses, and compare each synthetic view to the real
FPV frame it came from.

Two things matter for this to be correct:
  - Per-camera orientation. In the VGGT-omega .glb the node transform is the SAME
    for every camera; the per-frame pose lives in the frustum geometry. So for each
    camera we read the apex (camera center) and the far-plane centre from its frustum
    vertices and recover that camera's forward direction. (Using the node rotation
    alone would give every frame the same view — which is the bug this fixes.)
  - Gravity. The recovered gravity is -y (cameras sit above the terrain along +y and
    the terminal poses pitch toward -y, diving to the ground). The camera is roughly
    horizontal, so we lock image-up to the sky (+y) projected perpendicular to each
    camera's forward. That keeps every synthetic view right-side up.

A single fixed focal length is used for all frames (VGGT's intrinsics aren't carried
in the .glb), so the views are comparable: as the drone closes in, the scene scales
up and shifts. Output: public/img/fpv-drone-strikes/camera_views.png
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
UP_WORLD = np.array([0.0, 1.0, 0.0])   # sky (anti-gravity); gravity is -y
ASPECT = 848 / 478
FLIP_RIGHT = False                     # right = cross(fwd, up) (X-right/Y-down/Z-fwd); not mirrored

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
    centers, fwds = [], []
    for n in cams:
        g = s.geometry[n]
        V = np.asarray(g.vertices)
        F = np.asarray(g.faces)
        T = name2T[n]
        apex = V[int(np.argmax(np.bincount(F.reshape(-1), minlength=len(V))))]
        far = V[np.abs(V[:, 2] - V[:, 2].max()) < 1e-6].mean(0)   # far-plane centre
        centers.append((T @ np.array([*apex, 1.0]))[:3])
        fwds.append(T[:3, :3] @ (far - apex))
    centers = np.array(centers)
    fwds = np.array(fwds) / np.linalg.norm(fwds, axis=1, keepdims=True)

    pc = s.geometry["geometry_0"]
    pts = trimesh.transformations.transform_points(pc.vertices, name2T.get("geometry_0", np.eye(4)))
    cols = np.asarray(pc.colors)[:, :3] / 255.0 if getattr(pc, "colors", None) is not None else None
    ok = np.isfinite(pts).all(1)
    pts, cols = pts[ok], (cols[ok] if cols is not None else None)
    return pts, cols, centers, fwds

def basis(fwd):
    """Right/up image axes with up locked to the sky (gravity-correct)."""
    up = UP_WORLD - np.dot(UP_WORLD, fwd) * fwd
    up /= np.linalg.norm(up)
    right = np.cross(fwd, up); right /= np.linalg.norm(right)
    if FLIP_RIGHT:
        right = -right
    return right, up

def project(pts, cols, center, fwd, focal):
    right, up = basis(fwd)
    d = pts - center
    z = d @ fwd
    front = z > 1e-4
    d, z = d[front], z[front]
    c = cols[front] if cols is not None else None
    u = focal * (d @ right) / z
    v = focal * (d @ up) / z
    keep = (np.abs(u) < ASPECT) & (np.abs(v) < 1.0)
    u, v, z = u[keep], v[keep], z[keep]
    c = c[keep] if c is not None else None
    order = np.argsort(-z)                       # far first, near on top
    return u[order], v[order], (c[order] if c is not None else None), z[order]

def fit_focal(pts, centers, fwds):
    """One focal for all frames: median of the per-frame fill-the-frame focal."""
    fs = []
    for ctr, fwd in zip(centers, fwds):
        right, up = basis(fwd)
        d = pts - ctr
        z = d @ fwd
        m = z > 1e-4
        if m.sum() < 100:
            continue
        x = np.abs((d[m] @ right) / z[m])
        fs.append(0.9 / (np.percentile(x, 92) + 1e-6))
    return float(np.median(fs))

def main():
    import glob
    pts, cols, centers, fwds = load_glb()
    focal = fit_focal(pts, centers, fwds)
    fdir = os.path.join(VGGT, "frames2")
    if not os.path.isdir(fdir):
        fdir = os.path.join(VGGT, "frames")
    frame_files = sorted(glob.glob(os.path.join(fdir, "f_*.jpg")))
    N = len(centers)
    idxs = [int(f * (N - 1)) for f in (0.05, 0.4, 0.72, 0.97)]

    fig, axes = plt.subplots(2, len(idxs), figsize=(14, 4.8), facecolor=BG)
    for col, i in enumerate(idxs):
        axT = axes[0, col]; axT.set_facecolor(BG); axT.axis("off")
        axT.imshow(imread(frame_files[i]))
        axT.set_title(f"real FPV frame {i+1}", color=TXT, fontsize=11)

        axB = axes[1, col]; axB.set_facecolor(BG)
        u, v, c, z = project(pts, cols, centers[i], fwds[i], focal)
        sizes = np.clip(2.2 * (np.median(z) / np.maximum(z, 1e-3)), 0.5, 6.0)
        axB.scatter(u, v, s=sizes, c=(c if c is not None else MUTED), linewidths=0, alpha=0.9)
        axB.set_xlim(-ASPECT, ASPECT); axB.set_ylim(-1, 1)
        axB.set_aspect("equal"); axB.set_xticks([]); axB.set_yticks([])
        for sp in axB.spines.values():
            sp.set_color("#333a45")
        axB.set_title("point cloud, same viewpoint", color=MUTED, fontsize=11)

    fig.suptitle("The reconstruction, seen from the drone's own recovered camera poses "
                 "(gravity down — sky at top, target growing as it closes in)",
                 color=TXT, fontsize=12.5)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(os.path.join(OUT, "camera_views.png"), dpi=150, facecolor=BG)
    print("saved camera_views.png  focal=%.2f" % focal)

if __name__ == "__main__":
    main()
