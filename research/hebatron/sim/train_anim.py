#!/usr/bin/env python3
"""Animated 'training arc' for the Hebatron post.

The central story from the episode: across ~200 runs the training loss and the
validation loss kept falling, yet the Hebrew benchmarks stayed *below* the
model they started from — until the team multiplied the global batch size
(and scaled the learning rate up with it), after which the benchmarks finally
broke above the baseline.

This is an *illustrative reconstruction* of that qualitative arc, not Hebatron's
logged curves. The shapes (loss down throughout; benchmark flat-then-jump at the
batch-size change) match what the speakers described.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import imageio_ffmpeg
plt.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()

BG, FG, MUT = "#0e1116", "#ededed", "#8b95a5"
CYAN, GOLD, GREEN, RED = "#3fc1ff", "#ffd166", "#7CFC8A", "#ff5a5a"

OUT = os.path.normpath(os.path.join(os.path.dirname(__file__),
      "../../../public/img/hebatron"))
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans", "Arial"],
    "text.color": FG, "axes.edgecolor": MUT, "axes.labelcolor": FG,
    "axes.titlecolor": FG, "xtick.color": MUT, "ytick.color": MUT,
})

N = 420
steps = np.linspace(0, 4000, N)
CHANGE = 2000.0                       # step where global batch x8, LR x3

# losses: both fall smoothly across the whole run
train_loss = 1.18 + 1.45 * np.exp(-steps / 1300)
val_loss   = 1.30 + 1.40 * np.exp(-steps / 1450)
rng = np.random.default_rng(0)
train_loss += rng.normal(0, 0.012, N)
val_loss   += rng.normal(0, 0.012, N)

# benchmark: baseline = the score of the model we started from
BASE = 50.0
bench = np.empty(N)
p1 = steps < CHANGE
# phase 1: drifts below baseline, refusing to move
bench[p1] = BASE - 3.5 + 1.6 * np.sin(steps[p1] / 280) - steps[p1] / 1400
# phase 2: climbs after the batch-size change
s2 = steps[~p1] - CHANGE
bench[~p1] = (BASE - 4.9) + 18.0 * (1 - np.exp(-s2 / 650))
bench += rng.normal(0, 0.35, N)

fig = plt.figure(figsize=(11.2, 6.4)); fig.patch.set_facecolor(BG)
gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.15], hspace=0.28,
                      left=0.10, right=0.95, top=0.88, bottom=0.11)
axL = fig.add_subplot(gs[0]); axB = fig.add_subplot(gs[1])
for ax in (axL, axB):
    ax.set_facecolor(BG); ax.grid(alpha=0.12)
    for s in ["top", "right"]: ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]: ax.spines[s].set_color(MUT)
    ax.set_xlim(0, 4000); ax.tick_params(colors=MUT)

axL.set_ylim(1.0, 2.8); axL.set_ylabel("loss")
axL.set_title("Training & validation loss — falling the whole time",
              fontsize=12, fontweight="bold", color=FG, loc="left")
axB.set_ylim(40, 70); axB.set_ylabel("Hebrew benchmark score")
axB.set_xlabel("training step")
axB.set_title("Benchmarks — flat below baseline, then they break free",
              fontsize=12, fontweight="bold", color=FG, loc="left")
axB.axhline(BASE, color=MUT, ls="--", lw=1.3)
axB.text(60, BASE + 0.5, "baseline: the model we started from", color=MUT,
         fontsize=9.5, va="bottom")

(ltr,) = axL.plot([], [], color=CYAN, lw=2.3, label="training loss")
(lva,) = axL.plot([], [], color=GREEN, lw=2.3, label="validation loss")
(lbe,) = axB.plot([], [], color=GOLD, lw=2.6)
head = axB.scatter([], [], s=60, color=GOLD, zorder=5,
                   edgecolor=FG, lw=1.0)
axL.legend(loc="upper right", fontsize=9.5, facecolor="#161b22",
           edgecolor=MUT, labelcolor=FG)

change_line_L = axL.axvline(CHANGE, color=RED, lw=0, ls="--")
change_line_B = axB.axvline(CHANGE, color=RED, lw=0, ls="--")
change_txt = axB.text(CHANGE, 67.5, "", color=RED, fontsize=10.5,
                      ha="center", fontweight="bold")
verdict = axB.text(3950, 41.5, "", color=GREEN, fontsize=12,
                   ha="right", fontweight="bold")

fig.suptitle("Loss said “I'm learning.” The benchmarks said “no, you're not.”",
             fontsize=14.5, fontweight="bold", color=FG, x=0.10, ha="left", y=0.965)

HOLD = 45   # frames to hold on the final frame before looping


def update(f):
    i = min(int(f / (N + HOLD) * N) + 1, N) if f < N else N
    i = min(f + 1, N)
    ltr.set_data(steps[:i], train_loss[:i])
    lva.set_data(steps[:i], val_loss[:i])
    lbe.set_data(steps[:i], bench[:i])
    head.set_offsets([[steps[i - 1], bench[i - 1]]])
    if steps[i - 1] >= CHANGE:
        change_line_L.set_linewidth(1.6)
        change_line_B.set_linewidth(1.6)
        change_txt.set_text("global batch ×8,  learning rate ×3")
    if i >= N:
        verdict.set_text("+12 over baseline → shipped")
    return ltr, lva, lbe, head, change_txt, verdict


frames = list(range(N)) + [N - 1] * HOLD
ani = animation.FuncAnimation(fig, update, frames=frames, interval=33, blit=False)
writer = animation.FFMpegWriter(fps=30, bitrate=2800)
path = f"{OUT}/training_arc.mp4"
ani.save(path, writer=writer, savefig_kwargs={"facecolor": BG})
plt.close(fig)
print("wrote", path)
