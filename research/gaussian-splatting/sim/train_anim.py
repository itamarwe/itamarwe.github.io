#!/usr/bin/env python3
"""Animation illustrating the training LOOP of Gaussian splatting.

IMPORTANT — this is a didactic stand-in, not real 3DGS training. There is no
gradient descent, no photometric+D-SSIM loss, and no backprop. Instead:
  * the renderer is a normalized alpha-weighted blend (partition of unity),
    pixel = sum_i w_i * color_i / sum_i w_i,   w_i = a_i * exp(-1/2 * mahalanobis),
    NOT the true front-to-back "over" compositing of projected 3D covariances;
  * "densification" greedily drops a new Gaussian at the highest-error pixels,
    colored by sampling the TARGET (not learned);
  * "pruning" removes the lowest-contribution Gaussians and globally shrinks
    everything so detail sharpens.
It reproduces the *shape* of the loop (init -> render -> measure error ->
densify where blurry -> prune) and the look of blobs resolving into a scene,
which is all the embedded video is meant to convey."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import animation
import os

H = W = 160
rng = np.random.default_rng(4)
OUT = os.path.normpath(os.path.join(os.path.dirname(__file__),
      "../../../public/img/gaussian-splatting"))

# ---- target "scene": sky gradient + sun + hill -----------------------------
def build_target():
    img = np.zeros((H, W, 3))
    yy = np.linspace(0, 1, H)[:, None]
    top = np.array([0.04, 0.10, 0.28]); horizon = np.array([1.0, 0.55, 0.20])
    grad = top[None,None,:]*(1-yy[...,None]) + horizon[None,None,:]*yy[...,None]
    img = np.broadcast_to(grad, (H, W, 3)).copy()
    Y, X = np.mgrid[0:H, 0:W]
    # sun
    sx, sy, sr = W*0.66, H*0.40, 16
    d = np.hypot(X-sx, Y-sy)
    sun = np.clip(1 - (d/sr), 0, 1)[...,None]
    img = img*(1-sun) + np.array([1.0, 0.93, 0.6])[None,None,:]*sun
    glow = np.exp(-(d/(sr*2.2))**2)[...,None]*0.5
    img = np.clip(img + np.array([1.0,0.7,0.3])[None,None,:]*glow, 0, 1)
    # hill
    hill_y = H*0.72 + 10*np.sin(X/W*4*np.pi) + 6*np.sin(X/W*9*np.pi+1)
    mask = (Y > hill_y)[...,None]
    hill_col = np.array([0.05, 0.20, 0.16])
    img = np.where(mask, hill_col[None,None,:], img)
    return np.clip(img, 0, 1)

target = build_target()
Y, X = np.mgrid[0:H, 0:W]

# ---- Gaussian set -----------------------------------------------------------
class Gaussians:
    def __init__(self):
        self.cx=[]; self.cy=[]; self.sx=[]; self.sy=[]; self.th=[]
        self.col=[]; self.a=[]
    def add(self, cx, cy, s, col, a=0.85, aniso=1.0, th=0.0):
        self.cx.append(cx); self.cy.append(cy)
        self.sx.append(s*aniso); self.sy.append(s/aniso); self.th.append(th)
        self.col.append(col); self.a.append(a)
    def n(self): return len(self.cx)

def render(g):
    num = np.zeros((H, W, 3)); den = np.zeros((H, W))
    for i in range(g.n()):
        ct, st = np.cos(g.th[i]), np.sin(g.th[i])
        dx = X-g.cx[i]; dy = Y-g.cy[i]
        u =  ct*dx + st*dy; v = -st*dx + ct*dy
        q = (u/g.sx[i])**2 + (v/g.sy[i])**2
        w = g.a[i]*np.exp(-0.5*q)
        c = g.col[i]
        num += w[...,None]*np.array(c)[None,None,:]
        den += w
    img = num / np.maximum(den, 1.0)[...,None]
    return img, den

g = Gaussians()
# init: a sparse scattering (the "sparse SfM points")
for _ in range(14):
    cx, cy = rng.uniform(8, W-8), rng.uniform(8, H-8)
    col = target[int(cy), int(cx)]
    g.add(cx, cy, rng.uniform(14, 22), col, a=0.8)

frames = 150

def densify_step(g):
    img, den = render(g)
    err = np.sqrt(((img-target)**2).sum(-1))      # per-pixel error
    err_blur = err.copy()
    # add several Gaussians at the highest-error spots, sized by local coverage
    flat = err.ravel().argsort()[::-1]
    added = 0
    used = np.zeros((H, W), bool)
    for idx in flat:
        if added >= 9: break
        py, px = divmod(idx, W)
        if used[max(0,py-4):py+4, max(0,px-4):px+4].any(): continue
        used[max(0,py-5):py+5, max(0,px-5):px+5] = True
        col = target[max(0,py-1):py+2, max(0,px-1):px+2].reshape(-1,3).mean(0)
        s = rng.uniform(4, 9)
        g.add(px+rng.normal(0,1), py+rng.normal(0,1), s, col,
              a=0.9, aniso=rng.uniform(0.8,1.6), th=rng.uniform(0,np.pi))
        added += 1
    # prune: drop Gaussians that barely contribute (low coverage footprint)
    if g.n() > 40:
        keep_idx = list(range(g.n()))
        # contribution proxy: alpha * area
        contrib = [g.a[i]*g.sx[i]*g.sy[i] for i in range(g.n())]
        order = np.argsort(contrib)
        ndrop = 6 if g.n() > 650 else (3 if g.n() > 60 else 0)
        drop = set(order[:ndrop].tolist())
        for k in sorted(drop, reverse=True):
            for arr in (g.cx,g.cy,g.sx,g.sy,g.th,g.col,g.a): arr.pop(k)
    # gently shrink everything so detail sharpens over time
    for i in range(g.n()):
        g.sx[i] *= 0.987; g.sy[i] *= 0.987
        g.sx[i] = max(g.sx[i], 1.7); g.sy[i] = max(g.sy[i], 1.7)

fig = plt.figure(figsize=(8.6, 4.7), dpi=120)
fig.patch.set_facecolor("#0e1116")
axL = fig.add_axes([0.02, 0.06, 0.46, 0.82]); axR = fig.add_axes([0.52, 0.06, 0.46, 0.82])
for a in (axL, axR): a.set_xticks([]); a.set_yticks([])
imL = axL.imshow(np.zeros((H,W,3)), interpolation="bilinear")
axR.imshow(target, interpolation="bilinear")
axL.set_title("rendered from Gaussians", color="#ededed", fontsize=12, pad=8)
axR.set_title("target photo", color="#8b95a5", fontsize=12, pad=8)
cnt = fig.text(0.5, 0.95, "", color="#ffd166", ha="center", fontsize=13, fontweight="bold")
sub = fig.text(0.5, 0.015, "init → render → measure error → densify where blurry → prune the useless",
               color="#8b95a5", ha="center", fontsize=9.5, style="italic")

state = {"img": None}
def animate(f):
    densify_step(g)
    img, _ = render(g)
    imL.set_data(np.clip(img,0,1))
    cnt.set_text(f"step {f*200:>5d}      {g.n():>4d} Gaussians")
    return [imL, cnt]

anim = animation.FuncAnimation(fig, animate, frames=frames, interval=66, blit=False)
mp4 = f"{OUT}/training.mp4"
anim.save(mp4, writer=animation.FFMpegWriter(fps=18, bitrate=2400,
          extra_args=["-pix_fmt","yuv420p"]))
plt.close(fig)
print("wrote", mp4, "final Gaussians:", g.n())
