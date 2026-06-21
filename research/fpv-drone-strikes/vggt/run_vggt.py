"""
Run the real VGGT (Visual Geometry Grounded Transformer) reconstruction on an
FPV-drone clip via the public facebook/vggt-omega Hugging Face Space (ZeroGPU).

Pipeline:
  1. Upload the FPV-only video segment -> /update_gallery_on_upload, which samples
     frames at `video_sample_fps` and returns a server-side `target_dir`.
  2. /gradio_demo runs VGGT feed-forward on those frames and returns a .glb holding
     the predicted point cloud + per-frame camera frustums (show_cam=True).
  3. We download the .glb locally; extract_path.py then pulls the camera centers
     (the drone's 3-D flight path) and the point cloud out of it.

This is the REAL model output, not an illustration.
"""
import os, sys, shutil, time
from gradio_client import Client, handle_file

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VIDEO = os.path.join(HERE, "..", "clips", "fpv_segment.mp4")
OUT_GLB = os.path.join(HERE, "vggt_scene.glb")

def main():
    video = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VIDEO)
    fps = float(os.environ.get("VGGT_FPS", "1.0"))
    print(f"[vggt] connecting to facebook/vggt-omega ...")
    c = Client("facebook/vggt-omega", verbose=False)

    print(f"[vggt] uploading {video} (sample_fps={fps}) ...")
    val14, target_dir, preview, log = c.predict(
        input_video={"video": handle_file(video), "subtitles": None},
        input_images=None,
        video_sample_fps=fps,
        api_name="/update_gallery_on_upload",
    )
    n = len(preview) if preview else 0
    print(f"[vggt] target_dir={target_dir}  sampled_frames={n}")

    print("[vggt] running VGGT reconstruction (/gradio_demo) ...")
    t0 = time.time()
    glb_path, vis_log = c.predict(
        target_dir=target_dir,
        conf_thres=50.0,
        mask_black_bg=False,
        mask_white_bg=False,
        show_cam=True,
        mask_sky=True,
        max_points_k=1000.0,
        api_name="/gradio_demo",
    )
    print(f"[vggt] done in {time.time()-t0:.0f}s -> {glb_path}")
    print("[vggt] log:\n", (vis_log or "")[:1500])

    shutil.copy(glb_path, OUT_GLB)
    print(f"[vggt] saved -> {OUT_GLB}  ({os.path.getsize(OUT_GLB)} bytes)")

if __name__ == "__main__":
    main()
