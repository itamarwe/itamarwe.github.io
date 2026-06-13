#!/usr/bin/env python3
"""Training-loop video for the Gaussian-splatting post — REAL 2D splatting.

This is an honest, scaled-down version of 3D Gaussian Splatting in 2D:
  * each Gaussian has an optimizable mean, scale, rotation, opacity and color,
    plus a fixed depth for the compositing order;
  * the renderer is the true front-to-back alpha-compositing splat,
    C(p) = sum_i c_i * alpha_i * prod_{j<i}(1 - alpha_j),  with
    alpha_i = o_i * exp(-1/2 (p-mu_i)^T Sigma_i^{-1} (p-mu_i));
  * the loss is the 3DGS objective L = (1-lambda)*L1 + lambda*(1 - SSIM);
  * parameters are optimized by real gradient descent (autograd + Adam);
  * adaptive density control runs off the accumulated view-space position
    gradient: clone under-reconstructed Gaussians, split over-large ones, and
    prune the near-transparent — exactly the operations the post describes.

It fits a synthetic but Gaussian-friendly "sunset" target. Everything in the
embedded clip comes out of this optimization. Needs numpy + torch (CPU is fine)
and ffmpeg on PATH."""
import os
import numpy as np
import torch
import torch.nn.functional as F
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import animation

torch.manual_seed(0)
np.random.seed(0)
DEV = "cpu"
H = W = 110
OUT = os.path.normpath(os.path.join(os.path.dirname(__file__),
      "../../../public/img/gaussian-splatting"))

# ---- target "scene": sky gradient + sun + hill ----------------------------
def build_target():
    img = np.zeros((H, W, 3), np.float32)
    yy = np.linspace(0, 1, H)[:, None]
    top = np.array([0.04, 0.10, 0.28]); horizon = np.array([1.0, 0.55, 0.20])
    grad = top[None, None, :] * (1 - yy[..., None]) + horizon[None, None, :] * yy[..., None]
    img = np.broadcast_to(grad, (H, W, 3)).copy()
    Y, X = np.mgrid[0:H, 0:W]
    sx, sy, sr = W * 0.66, H * 0.40, 11
    d = np.hypot(X - sx, Y - sy)
    sun = np.clip(1 - (d / sr), 0, 1)[..., None]
    img = img * (1 - sun) + np.array([1.0, 0.93, 0.6])[None, None, :] * sun
    glow = np.exp(-(d / (sr * 2.2)) ** 2)[..., None] * 0.5
    img = np.clip(img + np.array([1.0, 0.7, 0.3])[None, None, :] * glow, 0, 1)
    hill_y = H * 0.72 + 7 * np.sin(X / W * 4 * np.pi) + 4 * np.sin(X / W * 9 * np.pi + 1)
    mask = (Y > hill_y)[..., None]
    img = np.where(mask, np.array([0.05, 0.20, 0.16])[None, None, :], img)
    return np.clip(img, 0, 1).astype(np.float32)

target = torch.from_numpy(build_target()).to(DEV)            # (H,W,3)
target_chw = target.permute(2, 0, 1).unsqueeze(0)            # (1,3,H,W)

ys = torch.linspace(0, 1, H, device=DEV)
xs = torch.linspace(0, 1, W, device=DEV)
gy, gx = torch.meshgrid(ys, xs, indexing="ij")               # (H,W)

# ---- parameter state -------------------------------------------------------
def init_gaussians(n):
    mean = torch.rand(n, 2, device=DEV)                      # (x,y) in [0,1]
    log_s = torch.log(torch.full((n, 2), 0.06, device=DEV) * (0.6 + 0.8 * torch.rand(n, 2, device=DEV)))
    rot = torch.rand(n, device=DEV) * np.pi
    px = (mean[:, 0] * (W - 1)).long().clamp(0, W - 1)
    py = (mean[:, 1] * (H - 1)).long().clamp(0, H - 1)
    col = target[py, px].clamp(1e-3, 1 - 1e-3)               # (n,3)
    color_raw = torch.log(col / (1 - col))                   # logit
    op_raw = torch.full((n,), -1.0, device=DEV)             # sigmoid(-1) ~ 0.27
    z = torch.rand(n, device=DEV)                            # fixed compositing depth
    return dict(mean=mean, log_s=log_s, rot=rot, color=color_raw, op=op_raw, z=z)

def to_params(state):
    return {k: state[k].clone().detach().requires_grad_(True)
            for k in ("mean", "log_s", "rot", "color", "op")}

def render(p, z):
    s = torch.exp(p["log_s"]).clamp(1e-3, 0.5)
    sx2 = s[:, 0] ** 2; sy2 = s[:, 1] ** 2
    c = torch.cos(p["rot"]); sn = torch.sin(p["rot"])
    a = c * c / sx2 + sn * sn / sy2                          # Sigma^{-1}_00
    b = c * sn * (1.0 / sx2 - 1.0 / sy2)                     # Sigma^{-1}_01
    d = sn * sn / sx2 + c * c / sy2                          # Sigma^{-1}_11
    dx = gx[None] - p["mean"][:, 0][:, None, None]           # (n,H,W)
    dy = gy[None] - p["mean"][:, 1][:, None, None]
    q = a[:, None, None] * dx * dx + 2 * b[:, None, None] * dx * dy + d[:, None, None] * dy * dy
    g = torch.exp(-0.5 * q)
    alpha = (torch.sigmoid(p["op"])[:, None, None] * g).clamp(0, 0.999)
    cols = torch.sigmoid(p["color"])
    order = torch.argsort(z)                                # front (small z) first
    alpha = alpha[order]; cols = cols[order]
    T = torch.cumprod(1 - alpha + 1e-7, dim=0)
    T_excl = torch.cat([torch.ones(1, H, W, device=DEV), T[:-1]], dim=0)
    weight = alpha * T_excl
    return torch.einsum("nhw,nc->hwc", weight, cols)        # (H,W,3)

# ---- SSIM ------------------------------------------------------------------
def _win(ws=11, sigma=1.5):
    co = torch.arange(ws, device=DEV) - ws // 2
    g = torch.exp(-(co ** 2) / (2 * sigma ** 2)); g = g / g.sum()
    return (g[:, None] * g[None, :]).expand(3, 1, ws, ws).contiguous()

WIN = _win(); PAD = 5
def ssim(x, y):
    mx = F.conv2d(x, WIN, padding=PAD, groups=3); my = F.conv2d(y, WIN, padding=PAD, groups=3)
    mx2, my2, mxy = mx * mx, my * my, mx * my
    sx = F.conv2d(x * x, WIN, padding=PAD, groups=3) - mx2
    sy = F.conv2d(y * y, WIN, padding=PAD, groups=3) - my2
    sxy = F.conv2d(x * y, WIN, padding=PAD, groups=3) - mxy
    C1, C2 = 0.01 ** 2, 0.03 ** 2
    m = ((2 * mxy + C1) * (2 * sxy + C2)) / ((mx2 + my2 + C1) * (sx + sy + C2))
    return m.mean()

def loss_fn(img):
    l1 = (img - target).abs().mean()
    chw = img.permute(2, 0, 1).unsqueeze(0).clamp(0, 1)
    return 0.8 * l1 + 0.2 * (1 - ssim(chw, target_chw))

# ---- training loop with adaptive density control ---------------------------
state = init_gaussians(220)
p = to_params(state)
LR = dict(mean=4e-3, log_s=1e-2, rot=1e-2, color=2e-2, op=3e-2)
def make_opt(p):
    return torch.optim.Adam([{"params": [p[k]], "lr": LR[k]} for k in LR], eps=1e-8)
opt = make_opt(p)

TOTAL = 900
DENSIFY_EVERY = 50
CAP = 2200
CAP_EVERY = 6
grad_accum = torch.zeros(state["mean"].shape[0])
grad_cnt = 0
frames = []

def gather(src, idx):
    return ({k: src[k].detach()[idx].clone() for k in ("mean", "log_s", "rot", "color", "op")}
            | {"z": state["z"][idx].clone()})

def densify_and_prune():
    global p, opt, grad_accum, grad_cnt, state
    with torch.no_grad():
        gnorm = grad_accum / max(grad_cnt, 1)               # avg |dL/dmean|
        maxs = torch.exp(p["log_s"]).max(dim=1).values
        op = torch.sigmoid(p["op"])
        keep = op > 0.02                                    # prune transparent
        keep_idx = torch.where(keep)[0]

        thresh = torch.quantile(gnorm, 0.75)
        hi = gnorm > thresh
        big = maxs > 0.10
        clone_m = keep & hi & ~big                          # under-reconstructed -> clone
        split_m = keep & hi & big                           # over-large -> split

        base = gather(p, keep_idx)
        # drop the to-be-split originals from base
        split_idx = torch.where(split_m)[0]
        if split_idx.numel():
            drop = torch.isin(keep_idx, split_idx)
            base = {k: base[k][~drop] for k in base}
        chunks = [base]

        if clone_m.any():
            idx = torch.where(clone_m)[0]
            cl = gather(p, idx)
            g = p["mean"].grad
            if g is not None:
                dirn = g[idx] / (g[idx].norm(dim=1, keepdim=True) + 1e-8)
                cl["mean"] = (cl["mean"] - 0.5 * dirn * torch.exp(p["log_s"]).detach()[idx]).clamp(0, 1)
            chunks.append(cl)

        if split_idx.numel():
            for _ in range(2):
                sp = gather(p, split_idx)
                s_i = torch.exp(sp["log_s"])
                sp["mean"] = (sp["mean"] + torch.randn_like(sp["mean"]) * s_i * 0.6).clamp(0, 1)
                sp["log_s"] = sp["log_s"] - float(np.log(1.6))
                sp["z"] = torch.rand_like(sp["z"])
                chunks.append(sp)

        merged = {k: torch.cat([ch[k] for ch in chunks], dim=0)
                  for k in ("mean", "log_s", "rot", "color", "op", "z")}
        if merged["mean"].shape[0] > CAP:
            top = torch.argsort(torch.sigmoid(merged["op"]), descending=True)[:CAP]
            merged = {k: merged[k][top] for k in merged}

    state = {k: merged[k] for k in merged}
    p = to_params(state)
    opt = make_opt(p)
    grad_accum = torch.zeros(state["mean"].shape[0])
    grad_cnt = 0

for it in range(TOTAL):
    img = render(p, state["z"])
    loss = loss_fn(img)
    opt.zero_grad(set_to_none=True)
    loss.backward()
    with torch.no_grad():
        if p["mean"].grad is not None:
            grad_accum += p["mean"].grad.norm(dim=1).cpu()
            grad_cnt += 1
    opt.step()

    if it % CAP_EVERY == 0 or it == TOTAL - 1:
        with torch.no_grad():
            frames.append((render(p, state["z"]).clamp(0, 1).cpu().numpy(),
                           state["mean"].shape[0], it))

    if it > 0 and it % DENSIFY_EVERY == 0 and it < TOTAL - 120:
        densify_and_prune()

print(f"training done · final Gaussians: {state['mean'].shape[0]} · loss: {loss.item():.4f}")

# ---- encode the video ------------------------------------------------------
tgt_np = target.cpu().numpy()
fig = plt.figure(figsize=(8.6, 4.7), dpi=120); fig.patch.set_facecolor("#0e1116")
axL = fig.add_axes([0.02, 0.06, 0.46, 0.82]); axR = fig.add_axes([0.52, 0.06, 0.46, 0.82])
for a in (axL, axR): a.set_xticks([]); a.set_yticks([])
imL = axL.imshow(frames[0][0], interpolation="bilinear")
axR.imshow(tgt_np, interpolation="bilinear")
axL.set_title("rendered from Gaussians", color="#ededed", fontsize=12, pad=8)
axR.set_title("target photo", color="#8b95a5", fontsize=12, pad=8)
cnt = fig.text(0.5, 0.95, "", color="#ffd166", ha="center", fontsize=13, fontweight="bold")
fig.text(0.5, 0.015, "real 2D Gaussian splatting · Adam on L1 + D-SSIM · gradient-driven densify & prune",
         color="#8b95a5", ha="center", fontsize=9.5, style="italic")

def animate(i):
    rendered, n, it = frames[i]
    imL.set_data(rendered)
    cnt.set_text(f"step {it:>4d}      {n:>4d} Gaussians")
    return [imL, cnt]

anim = animation.FuncAnimation(fig, animate, frames=len(frames), interval=66, blit=False)
mp4 = f"{OUT}/training.mp4"
anim.save(mp4, writer=animation.FFMpegWriter(fps=18, bitrate=2400, extra_args=["-pix_fmt", "yuv420p"]))
plt.close(fig)
print("wrote", mp4, "frames:", len(frames))
