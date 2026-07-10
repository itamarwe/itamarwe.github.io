"""Render frames [start,end) and pipe raw RGB to an ffmpeg subprocess -> segment mp4."""
import sys, subprocess
import render

start, end, outpath = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
ff = subprocess.Popen(
    ["ffmpeg", "-y", "-loglevel", "error",
     "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{render.W}x{render.H}",
     "-r", str(render.FPS), "-i", "-",
     "-c:v", "libx264", "-preset", "medium", "-crf", "18",
     "-pix_fmt", "yuv420p", outpath],
    stdin=subprocess.PIPE)
for fi in range(start, end):
    ff.stdin.write(render.render_frame(fi).tobytes())
    if (fi - start) % 200 == 0:
        print(f"[{start}-{end}] {fi}", file=sys.stderr)
ff.stdin.close()
ff.wait()
print(f"segment {outpath} done ({start}-{end})", file=sys.stderr)
