"""
Parse the VGGT .glb (produced by run_vggt.py) into:
  - camera_path.npy : (N,3) world-space camera centers, in frame order = the
                      drone's reconstructed 3-D flight path.
  - point_cloud.npz : subsampled scene point cloud (xyz + rgb).

In the VGGT-omega .glb, geometry_0 is the dense point cloud and geometry_1..N are
per-frame camera frustums. Each frustum's apex (the highest-incidence vertex, at the
mesh's local origin) is the camera center; applying that node's world transform gives
the camera position for that frame. These are the REAL predicted poses.
"""
import os, numpy as np, trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
GLB = os.path.join(HERE, "vggt_scene.glb")

def main():
    s = trimesh.load(GLB)

    # map geometry name -> world transform from the scene graph
    name2T = {}
    for node in s.graph.nodes:
        try:
            T, geom = s.graph[node]
        except Exception:
            continue
        if geom is not None:
            name2T[geom] = np.asarray(T)

    # camera frustums: every geometry except the point cloud (geometry_0)
    cam_names = sorted(
        [n for n in s.geometry if n != "geometry_0"],
        key=lambda n: int(n.split("_")[1]),
    )
    centers = []
    for n in cam_names:
        g = s.geometry[n]
        # apex = vertex touched by the most faces (camera center, at local origin)
        counts = np.bincount(g.faces.reshape(-1), minlength=len(g.vertices))
        apex = g.vertices[int(np.argmax(counts))]
        T = name2T.get(n, np.eye(4))
        world = (T @ np.array([*apex, 1.0]))[:3]
        centers.append(world)
    centers = np.array(centers)
    np.save(os.path.join(HERE, "camera_path.npy"), centers)
    print(f"[path] {len(centers)} camera centers")
    seg = np.linalg.norm(np.diff(centers, axis=0), axis=1)
    print(f"[path] total path length = {seg.sum():.3f} (scene units)")
    print(f"[path] bbox min {np.round(centers.min(0),3)}  max {np.round(centers.max(0),3)}")

    # point cloud (geometry_0), transformed to world, subsampled
    pc = s.geometry["geometry_0"]
    Tpc = name2T.get("geometry_0", np.eye(4))
    pts = trimesh.transformations.transform_points(pc.vertices, Tpc)
    cols = None
    if hasattr(pc, "colors") and pc.colors is not None and len(pc.colors):
        cols = np.asarray(pc.colors)[:, :3]
    # drop NaNs / infinities
    ok = np.isfinite(pts).all(1)
    pts = pts[ok]
    if cols is not None:
        cols = cols[ok]
    # subsample to keep files light
    N = 220_000
    if len(pts) > N:
        idx = np.random.default_rng(0).choice(len(pts), N, replace=False)
        pts = pts[idx]
        if cols is not None:
            cols = cols[idx]
    np.savez(os.path.join(HERE, "point_cloud.npz"),
             pts=pts.astype(np.float32),
             cols=(cols.astype(np.uint8) if cols is not None else np.zeros((len(pts), 3), np.uint8)))
    print(f"[pc] saved {len(pts)} points (colors={cols is not None})")

if __name__ == "__main__":
    main()
