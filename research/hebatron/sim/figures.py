#!/usr/bin/env python3
"""Static figures for the Hebatron post. Dark 3b1b-ish palette.

These figures illustrate the story told in the ExplAInable episode about
training Hebatron (a Hebrew LLM, a continued-pretrain + SFT of NVIDIA's
Nemotron). Where a figure shows numbers, they are either taken from the
episode (tokenizer compression ratios, throughput/cost, the large-batch
formula) or are *illustrative reconstructions* of a qualitative claim the
speakers made (e.g. the MoE entropy collapse, the loss-vs-benchmark
disconnect). Reconstructions are flagged in the relevant docstring and in
the post text.

Hebrew words are written in transliteration on purpose: matplotlib's default
fonts do not shape right-to-left text correctly, so rendering real Hebrew
glyphs would come out reversed. The transliteration carries the morphology
point without the rendering bug.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle

BG   = "#0e1116"
FG   = "#ededed"
MUT  = "#8b95a5"
CYAN = "#3fc1ff"
GOLD = "#ffd166"
GREEN= "#7CFC8A"
RED  = "#ff5a5a"
PURP = "#b48cff"

OUT = os.path.normpath(os.path.join(os.path.dirname(__file__),
      "../../../public/img/hebatron"))
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial"],
    "text.color": FG, "axes.edgecolor": MUT, "axes.labelcolor": FG,
    "axes.titlecolor": FG,
    "xtick.color": MUT, "ytick.color": MUT, "figure.dpi": 130,
})


def newfig(w, h):
    fig = plt.figure(figsize=(w, h)); fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor(BG)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    for s in ax.spines.values(): s.set_visible(False)
    return fig, ax


def token_boxes(ax, x0, y, tokens, colors, h=0.075, pad=0.006, fs=12, scale=0.052):
    """Draw a row of token chips starting at x0, return the right edge."""
    x = x0
    for tok, c in zip(tokens, colors):
        w = max(0.07, len(tok) * scale + 0.03)
        ax.add_patch(FancyBboxPatch((x, y - h / 2), w, h,
                     boxstyle="round,pad=0.004,rounding_size=0.012",
                     linewidth=1.4, edgecolor=c, facecolor=c + "22"))
        ax.text(x + w / 2, y, tok, ha="center", va="center", fontsize=fs,
                color=c, fontweight="bold")
        x += w + pad
    return x


# ---------------------------------------------------------------------------
# Figure 1: why Hebrew is hard — morphology + tokenizer compression ratio
# ---------------------------------------------------------------------------
def fig_tokenization():
    fig = plt.figure(figsize=(12.4, 5.6)); fig.patch.set_facecolor(BG)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.25, 1.0], wspace=0.16,
                          left=0.03, right=0.97, top=0.84, bottom=0.12)

    # -- left: one root, many glued-on functions -------------------------
    axL = fig.add_subplot(gs[0]); axL.set_facecolor(BG)
    axL.set_xlim(0, 1); axL.set_ylim(0, 1); axL.axis("off")
    axL.set_title("One word does the work of three", fontsize=14,
                  fontweight="bold", color=FG, pad=10, loc="left")

    # English: clean, isolated function words
    axL.text(0.0, 0.90, "English — function words stand alone", fontsize=11.5,
             color=CYAN, fontweight="bold")
    token_boxes(axL, 0.0, 0.79, ["and", "to", "the", "computer"],
                [MUT, MUT, MUT, GREEN], fs=11)

    axL.text(0.0, 0.62, "Hebrew — article + preposition + conjunction glue\n"
             "onto the root, making one long word", fontsize=11.5,
             color=GOLD, fontweight="bold")
    # u-, la-, ha- prefixes fused to the root "mahshev" (computer)
    token_boxes(axL, 0.0, 0.46,
                ["mahshev", "ha·mahshev", "la·mahshev"],
                [GREEN, PURP, RED], fs=11, scale=0.040)
    axL.text(0.0, 0.355,
             "“computer” → “the computer” → “to the computer” — each is a\n"
             "single word to a reader, but a blind BPE split shatters each\n"
             "one differently.",
             fontsize=10.3, color=MUT, va="top")

    axL.text(0.0, 0.10,
             "Hebrew is a morphologically rich language: the grammatical\n"
             "role lives *inside* the word. Sub-word tokenizers built for\n"
             "English have to fight that.", fontsize=10.6, color=FG, va="top")

    # -- right: tokens-per-Hebrew-word (compression ratio) ---------------
    axR = fig.add_subplot(gs[1]); axR.set_facecolor(BG)
    names = ["Mistral /\nNemotron", "Qwen", "Gemma", "Llama", "Granite"]
    ratio = [2.5, 2.6, 2.6, 5.0, 5.0]
    cols  = [GREEN, GREEN, GREEN, RED, RED]
    ypos = np.arange(len(names))[::-1]
    axR.barh(ypos, ratio, color=[c + "cc" for c in cols], edgecolor=cols, height=0.62)
    for y, r in zip(ypos, ratio):
        axR.text(r + 0.12, y, f"{r:.1f}", va="center", color=FG, fontsize=11,
                 fontweight="bold")
    axR.axvline(2.6, color=CYAN, lw=1.4, ls="--")
    axR.text(2.55, 1.5, "good for Hebrew  ", color=CYAN, fontsize=9.5,
             ha="right", va="center", style="italic")
    axR.set_yticks(ypos); axR.set_yticklabels(names, color=FG, fontsize=10.5)
    axR.set_xlim(0, 6.2); axR.set_xlabel("tokens per Hebrew word", color=FG)
    axR.set_title("Tokenizer compression ratio", fontsize=13,
                  fontweight="bold", color=FG, pad=10, loc="left")
    axR.tick_params(colors=MUT)
    for s in ["top", "right"]: axR.spines[s].set_visible(False)
    for s in ["left", "bottom"]: axR.spines[s].set_color(MUT)

    fig.savefig(f"{OUT}/tokenization.png", facecolor=BG)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 2: choosing a base model — learnable beats "strongest on the board"
# ---------------------------------------------------------------------------
def fig_base_model():
    fig, ax = newfig(11.6, 6.4)
    ax.set_title("Don't fine-tune the strongest model. Fine-tune the most learnable one.",
                 fontsize=14, fontweight="bold", color=FG, loc="left",
                 x=0.04, y=0.93)

    # axes box
    bx0, by0, bx1, by1 = 0.12, 0.16, 0.93, 0.80
    ax.add_patch(Rectangle((bx0, by0), bx1 - bx0, by1 - by0, fill=False,
                 edgecolor=MUT, lw=1.2))
    # x = tokenizer compression (LEFT good), y = headroom to learn (up good)
    ax.annotate("", xy=(bx1 + 0.005, by0), xytext=(bx0, by0),
                arrowprops=dict(arrowstyle="-|>", color=MUT, lw=1.4))
    ax.annotate("", xy=(bx0, by1 + 0.02), xytext=(bx0, by0),
                arrowprops=dict(arrowstyle="-|>", color=MUT, lw=1.4))
    ax.text((bx0 + bx1) / 2, by0 - 0.06,
            "more tokens per Hebrew word  →   (a worse tokenizer)",
            ha="center", color=FG, fontsize=10.5)
    ax.text(bx0 - 0.04, (by0 + by1) / 2,
            "more headroom to learn  →\n(less over-cooked base)", rotation=90,
            ha="center", va="center", color=FG, fontsize=10.5)

    # sweet-spot shading (top-left): good tokenizer + learnable base
    ax.add_patch(Rectangle((bx0, by0 + 0.52 * (by1 - by0)), 0.40 * (bx1 - bx0),
                 0.48 * (by1 - by0), facecolor=GREEN + "16", edgecolor="none"))
    ax.text(bx0 + 0.015, by1 - 0.025, "sweet spot:\ngood tokenizer + learnable",
            color=GREEN, fontsize=9.8, fontweight="bold", va="top")

    # place points explicitly (axis-fraction within the box)
    def P(fx, fy):
        return bx0 + fx * (bx1 - bx0), by0 + fy * (by1 - by0)
    pts = [
        # name, fx, fy, color, note, note_below
        ("Nemotron",     0.15, 0.66, GREEN, "open base + recipe,\nMamba-MoE, 7× faster", True),
        ("Qwen",         0.08, 0.52, CYAN,  "tried — wouldn't improve", True),
        ("Gemma",        0.27, 0.47, CYAN,  "", True),
        ("Granite",      0.78, 0.72, RED,   "Mamba-MoE too,\nbut compression ≈ 5", True),
        ("Llama",        0.90, 0.55, RED,   "", True),
        ("Command-R",    0.20, 0.29, GOLD,  "less RLHF-baked, still no lift", True),
        ("Aya (Cohere)", 0.40, 0.13, GOLD,  "tops the Hebrew board, but over-cooked:\nloss fell, benchmarks never did", True),
    ]
    for name, fx, fy, c, note, below in pts:
        x, y = P(fx, fy)
        chosen = name == "Nemotron"
        ax.scatter([x], [y], s=360 if chosen else 150, color=c,
                   edgecolor=FG if chosen else c, lw=1.8 if chosen else 1.0,
                   zorder=5)
        ax.text(x, y + 0.05, name, ha="center", va="bottom", color=c,
                fontsize=11.5 if chosen else 10.5,
                fontweight="bold" if chosen else "normal", zorder=6)
        if note:
            ny, va = (y - 0.05, "top") if below else (y + 0.085, "bottom")
            ax.text(x, ny, note, ha="center", va=va, color=MUT,
                    fontsize=8.4, zorder=6)

    fig.savefig(f"{OUT}/base_model.png", facecolor=BG)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 3: data — mix by content, not by source; and the ordering wall
# ---------------------------------------------------------------------------
def fig_data():
    fig = plt.figure(figsize=(12.4, 5.4)); fig.patch.set_facecolor(BG)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.1, 1.0], wspace=0.18,
                          left=0.04, right=0.96, top=0.85, bottom=0.13)

    # -- left: source vs content -----------------------------------------
    axL = fig.add_subplot(gs[0]); axL.set_facecolor(BG)
    axL.set_xlim(0, 1); axL.set_ylim(0, 1); axL.axis("off")
    axL.set_title("It's not where the data is from. It's what it is.",
                  fontsize=13.5, fontweight="bold", color=FG, loc="left")

    # source bins (each mixes content types)
    src = [("National Library", 0.12), ("The web", 0.55)]
    kinds = [("poetry", GOLD), ("math", CYAN), ("news", GREEN), ("code", PURP)]
    rng = np.random.default_rng(3)
    for label, x0 in src:
        axL.add_patch(FancyBboxPatch((x0, 0.55), 0.33, 0.30,
                      boxstyle="round,pad=0.01,rounding_size=0.02",
                      edgecolor=MUT, facecolor="#161b22", lw=1.3))
        axL.text(x0 + 0.165, 0.885, label, ha="center", color=MUT, fontsize=10.5)
        for _ in range(14):
            kx = x0 + 0.04 + rng.uniform(0, 0.25)
            ky = 0.59 + rng.uniform(0, 0.21)
            c = kinds[rng.integers(0, 4)][1]
            axL.add_patch(Circle((kx, ky), 0.014, color=c))

    axL.annotate("", xy=(0.5, 0.40), xytext=(0.5, 0.52),
                 arrowprops=dict(arrowstyle="-|>", color=FG, lw=1.6))
    axL.text(0.52, 0.46, "re-cluster by content\n(TF-IDF / sparse vectors)",
             fontsize=9.5, color=FG, va="center")

    # content clusters
    for i, (label, c) in enumerate(kinds):
        cx = 0.10 + i * 0.225
        axL.add_patch(FancyBboxPatch((cx, 0.08), 0.18, 0.24,
                      boxstyle="round,pad=0.01,rounding_size=0.02",
                      edgecolor=c, facecolor=c + "18", lw=1.4))
        axL.text(cx + 0.09, 0.275, label, ha="center", color=c, fontsize=10,
                 fontweight="bold")
        for _ in range(7):
            axL.add_patch(Circle((cx + 0.03 + rng.uniform(0, 0.12),
                                  0.11 + rng.uniform(0, 0.11)), 0.013, color=c))

    # -- right: the ordering wall ----------------------------------------
    axR = fig.add_subplot(gs[1]); axR.set_facecolor(BG)
    n = np.arange(2, 21)
    # number of orderings of n datasets ~ n!  (the team quoted "20^19")
    from math import lgamma
    log_orderings = np.array([lgamma(k + 1) / np.log(10) for k in n])  # log10(n!)
    axR.plot(n, log_orderings, color=CYAN, lw=2.4)
    axR.fill_between(n, log_orderings, color=CYAN + "22")
    axR.scatter([20], [log_orderings[-1]], s=90, color=GOLD, zorder=5)
    axR.annotate("20 datasets ≈ 10$^{18}$ orderings\n— you can't grid-search this",
                 xy=(20, log_orderings[-1]), xytext=(11.4, log_orderings[-1] - 5.5),
                 color=GOLD, fontsize=9.6,
                 arrowprops=dict(arrowstyle="-|>", color=GOLD, lw=1.2))
    axR.set_xlabel("number of datasets in the mix", color=FG)
    axR.set_ylabel("log$_{10}$(possible training orders)", color=FG)
    axR.set_title("Order matters — and that's the problem",
                  fontsize=13, fontweight="bold", color=FG, loc="left")
    axR.tick_params(colors=MUT)
    for s in ["top", "right"]: axR.spines[s].set_visible(False)
    for s in ["left", "bottom"]: axR.spines[s].set_color(MUT)
    axR.text(0.97, 0.03,
             "Same datasets, different order → different model.\n"
             "So the elegant data-mixing equation got shelved\n"
             "in favour of intuition during the run.",
             transform=axR.transAxes, ha="right", va="bottom",
             fontsize=9.0, color=MUT)

    fig.savefig(f"{OUT}/data.png", facecolor=BG)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 4: MoE expert-routing entropy collapse (illustrative reconstruction)
# ---------------------------------------------------------------------------
def fig_moe_entropy():
    """Illustrative reconstruction. The speakers reported that, on Hebrew,
    expert-routing entropy *collapses* toward the deep layers (the model
    leans on a few experts), and that an auxiliary load-balancing loss
    spreads the load back out. The exact per-layer numbers here are made up
    to show the shape, not measured from Hebatron."""
# ---------------------------------------------------------------------------
# Figure 4: MoE expert-routing schematic — collapse vs. balanced (no numbers)
# ---------------------------------------------------------------------------
def fig_moe_schematic():
    """Schematic (not a data plot): how a Mixture-of-Experts router lights up
    experts layer by layer. On Hebrew, before the fix, the deep layers collapse
    onto a couple of experts; the auxiliary load-balancing loss spreads the load
    back out. Lit boxes = experts the router actually uses; no quantities are
    implied beyond 'few vs many'."""
    fig = plt.figure(figsize=(12.2, 6.0)); fig.patch.set_facecolor(BG)
    gs = fig.add_gridspec(1, 2, wspace=0.14, left=0.04, right=0.96,
                          top=0.82, bottom=0.10)

    NLAYERS, NEXP = 6, 8
    # which experts are "lit" per layer (bottom = shallow, top = deep)
    before = [6, 5, 4, 3, 2, 1]            # collapses with depth
    after  = [5, 4, 5, 4, 5, 4]            # stays spread

    def panel(ax, lit_counts, accent, title, caption, seed):
        ax.set_facecolor(BG); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.text(0.5, 1.06, title, color=accent, fontsize=13, fontweight="bold",
                ha="center")
        rng = np.random.default_rng(seed)
        ew, gap = 0.084, 0.014
        total = NEXP * ew + (NEXP - 1) * gap
        x_start = (1 - total) / 2
        ys = np.linspace(0.10, 0.88, NLAYERS)
        rh = 0.075
        for li, (y, k) in enumerate(zip(ys, lit_counts)):
            # router dot
            ax.add_patch(Circle((x_start - 0.05, y + rh / 2), 0.012, color=accent))
            lit = set(rng.choice(NEXP, size=k, replace=False).tolist())
            for e in range(NEXP):
                x = x_start + e * (ew + gap)
                on = e in lit
                face = accent + "cc" if on else "#1b212a"
                edge = accent if on else "#2a313b"
                ax.add_patch(FancyBboxPatch((x, y), ew, rh,
                             boxstyle="round,pad=0.002,rounding_size=0.008",
                             facecolor=face, edgecolor=edge, lw=1.2))
                if on:
                    ax.plot([x_start - 0.05, x + ew / 2], [y + rh / 2, y + rh / 2],
                            color=accent + "55", lw=0.8, zorder=0)
            depth_lbl = "deep" if li == NLAYERS - 1 else ("shallow" if li == 0 else "")
            if depth_lbl:
                ax.text(x_start - 0.10, y + rh / 2, depth_lbl, color=MUT,
                        fontsize=8.5, ha="right", va="center", rotation=90)
        ax.annotate("", xy=(x_start - 0.05, ys[-1] + 0.06),
                    xytext=(x_start - 0.05, ys[0] - 0.02),
                    arrowprops=dict(arrowstyle="-|>", color=MUT, lw=1.1))
        ax.text(0.5, -0.02, caption, color=MUT, fontsize=9.3, ha="center", va="top")

    axL = fig.add_subplot(gs[0])
    panel(axL, before, RED, "Hebrew, before",
          "Deep layers collapse onto a couple of experts —\nmost of the model sits idle.", 1)
    axR = fig.add_subplot(gs[1])
    panel(axR, after, GREEN, "Hebrew, + load-balancing loss",
          "The router is pushed to spread tokens, so far more\nparameters carry Hebrew knowledge.", 7)

    fig.suptitle("A Mixture-of-Experts wastes itself on a new language",
                 fontsize=14.5, fontweight="bold", color=FG, x=0.04, ha="left", y=0.96)
    fig.text(0.96, 0.95, "each box = one expert · lit = used by the router",
             color=MUT, fontsize=9.5, ha="right")
    fig.savefig(f"{OUT}/moe_schematic.png", facecolor=BG)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 4b: batch size vs training steps (real numbers from the run)
# ---------------------------------------------------------------------------
def fig_batch_size():
    """Real numbers: a fixed ~250B-token budget, so steps = 250B / batch. The
    20k-100k efficient window is the rule of thumb from the large-batch paper.
    The two marked points are the run's actual before/after global batch sizes."""
    fig, ax = plt.subplots(figsize=(10.8, 6.0))
    fig.patch.set_facecolor(BG); ax.set_facecolor(BG)

    TOTAL = 250e9
    b = np.geomspace(0.5e6, 16e6, 300)
    steps = TOTAL / b
    ax.plot(b, steps, color=CYAN, lw=2.6)

    # efficient window 20k-100k steps
    ax.axhspan(20e3, 100e3, color=GREEN + "16")
    ax.text(0.52e6, 45e3, "efficient window\n20k–100k steps", color=GREEN,
            fontsize=10, va="center")

    pts = [(2.0e6, "before: 2M tokens\n→ 125k steps (too noisy)", RED,
            (2.7e6, 2.8e5), "left"),
           (10.5e6, "after: 10.5M tokens\n→ 24k steps ✓", GREEN,
            (3.2e6, 5.2e4), "right")]
    for bb, lbl, c, xytext, ha in pts:
        s = TOTAL / bb
        ax.scatter([bb], [s], s=90, color=c, edgecolor=FG, lw=1.2, zorder=5)
        ax.annotate(lbl, xy=(bb, s), xytext=xytext, color=c, fontsize=10.5,
                    ha=ha, arrowprops=dict(arrowstyle="-|>", color=c, lw=1.2))

    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("global batch size (tokens)", color=FG, fontsize=11)
    ax.set_ylabel("training steps  (= 250B tokens / batch)", color=FG, fontsize=11)
    ax.set_title("The batch size that finally moved the benchmarks",
                 fontsize=14, fontweight="bold", color=FG, loc="left")
    ax.set_xlim(0.5e6, 16e6); ax.set_ylim(1.2e4, 6e5)
    ax.set_xticks([0.5e6, 1e6, 2e6, 4e6, 8e6, 16e6])
    ax.set_xticklabels(["0.5M", "1M", "2M", "4M", "8M", "16M"])
    ax.set_yticks([2e4, 5e4, 1e5, 2e5, 5e5])
    ax.set_yticklabels(["20k", "50k", "100k", "200k", "500k"])
    ax.tick_params(colors=MUT); ax.grid(alpha=0.12, which="both")
    for s in ["top", "right"]: ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]: ax.spines[s].set_color(MUT)
    ax.text(0.985, 0.97,
            "Moving up the curve into the window let the gradient\n"
            "average out the noise. Learning rate scaled with √(batch):\n"
            "≈ 8× the batch wanted ≈ 3× the learning rate.",
            transform=ax.transAxes, ha="right", va="top", fontsize=9.2, color=MUT)
    fig.tight_layout()
    fig.savefig(f"{OUT}/batch_size.png", facecolor=BG)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 5: SFT — packing + loss masking
# ---------------------------------------------------------------------------
def fig_sft_packing():
    fig = plt.figure(figsize=(12.2, 5.6)); fig.patch.set_facecolor(BG)
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1], hspace=0.55,
                          left=0.06, right=0.97, top=0.86, bottom=0.10)

    ctxw = 0.86  # drawn width of an 8K context window
    x0 = 0.06

    def window(ax, segs, title, sub):
        ax.set_facecolor(BG); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.text(x0, 0.95, title, color=FG, fontsize=12.5, fontweight="bold")
        ax.text(x0, 0.80, sub, color=MUT, fontsize=9.8, va="top")
        y, h = 0.16, 0.26
        x = x0
        for w, c, lit, lbl in segs:
            ww = w * ctxw
            face = c + ("66" if lit else "18")
            ax.add_patch(Rectangle((x, y), ww, h, facecolor=face,
                         edgecolor=c, lw=1.3))
            if lbl:
                ax.text(x + ww / 2, y + h / 2, lbl, ha="center", va="center",
                        color=FG if lit else MUT, fontsize=8.6)
            x += ww
        # full window frame
        ax.add_patch(Rectangle((x0, y), ctxw, h, fill=False, edgecolor=MUT,
                     lw=1.4))
        ax.annotate("", xy=(x0 + ctxw, 0.15), xytext=(x0, 0.15),
                    arrowprops=dict(arrowstyle="<->", color=MUT, lw=1.0))
        ax.text(x0 + ctxw / 2, 0.085, "one 8K context window", ha="center",
                color=MUT, fontsize=9)

    # top: naive — one short example, the rest is wasted padding
    axA = fig.add_subplot(gs[0])
    window(axA,
           [(0.42, CYAN, True, "example"),
            (0.58, MUT, False, "padding (wasted compute)")],
           "Naïve: one example per window",
           "A 4K answer in an 8K window leaves half the GPU doing nothing.")

    # bottom: packed — several examples, loss only on the responses
    axB = fig.add_subplot(gs[1])
    window(axB,
           [(0.16, MUT,  False, "prompt"), (0.20, GOLD, True, "response"),
            (0.12, MUT,  False, "prompt"), (0.10, GOLD, True, "resp"),
            (0.18, MUT,  False, "prompt"), (0.18, GOLD, True, "response"),
            (0.06, PURP, False, "pad")],
           "Packed + loss-masked: many examples, score only the answers",
           "Pack several conversations end-to-end, then mask the loss so it's\n"
           "computed only on the assistant tokens (gold) — which Megatron-Bridge\n"
           "didn't do for SFT, so the team had to build the packer.")
    # legend chips
    axB.text(0.06, -0.02, "■", color=GOLD, fontsize=13)
    axB.text(0.085, -0.02, "loss is computed here", color=FG, fontsize=9, va="center")
    axB.text(0.42, -0.02, "■", color=MUT, fontsize=13)
    axB.text(0.445, -0.02, "masked (prompt / padding)", color=FG, fontsize=9, va="center")

    fig.suptitle("Supervised fine-tuning: the bookkeeping is the hard part",
                 fontsize=14, fontweight="bold", color=FG, x=0.06, ha="left", y=0.97)
    fig.savefig(f"{OUT}/sft_packing.png", facecolor=BG)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 6: infrastructure — throughput up, cost down
# ---------------------------------------------------------------------------
def fig_infra():
    fig = plt.figure(figsize=(12.2, 5.4)); fig.patch.set_facecolor(BG)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1], wspace=0.26,
                          left=0.07, right=0.96, top=0.84, bottom=0.16)

    # throughput
    ax1 = fig.add_subplot(gs[0]); ax1.set_facecolor(BG)
    stages = ["DeepSpeed\nH200", "Megatron-Bridge\nH200", "Megatron-Bridge\nB300 (Blackwell)"]
    tput = [2000, 4000, 14000]
    cols = [MUT, CYAN, GREEN]
    bars = ax1.bar(range(3), tput, color=[c + "cc" for c in cols], edgecolor=cols, width=0.6)
    for i, t in enumerate(tput):
        ax1.text(i, t + 300, f"{t:,}", ha="center", color=FG, fontsize=11,
                 fontweight="bold")
    ax1.set_xticks(range(3)); ax1.set_xticklabels(stages, fontsize=9.5, color=FG)
    ax1.set_ylabel("tokens / second", color=FG)
    ax1.set_ylim(0, 16000)
    ax1.set_title("Throughput: 7× faster, end to end", fontsize=12.5,
                  fontweight="bold", color=FG, loc="left")
    ax1.tick_params(colors=MUT)
    for s in ["top", "right"]: ax1.spines[s].set_visible(False)
    for s in ["left", "bottom"]: ax1.spines[s].set_color(MUT)
    ax1.annotate("framework", xy=(0.5, 4000), xytext=(0.5, 8200), color=CYAN,
                 fontsize=9, ha="center",
                 arrowprops=dict(arrowstyle="-|>", color=CYAN, lw=1.1))
    ax1.annotate("hardware", xy=(1.5, 9000), xytext=(1.4, 12500), color=GREEN,
                 fontsize=9, ha="center",
                 arrowprops=dict(arrowstyle="-|>", color=GREEN, lw=1.1))

    # cost
    ax2 = fig.add_subplot(gs[1]); ax2.set_facecolor(BG)
    labels = ["first estimate", "after framework\nswitch (½)", "after Blackwell\n(7× faster)"]
    cost = [200, 100, 25]  # $k for a full CPT run
    cols2 = [RED, GOLD, GREEN]
    ax2.bar(range(3), cost, color=[c + "cc" for c in cols2], edgecolor=cols2, width=0.6)
    for i, c in enumerate(cost):
        tag = f"~${c}k" if c >= 100 else "tens of\n$thousands"
        ax2.text(i, c + 6, tag, ha="center", color=FG, fontsize=10.5,
                 fontweight="bold")
    ax2.set_xticks(range(3)); ax2.set_xticklabels(labels, fontsize=9.5, color=FG)
    ax2.set_ylabel("cost of one full CPT run (USD)", color=FG)
    ax2.set_ylim(0, 240)
    ax2.set_yticks([0, 50, 100, 150, 200]); ax2.set_yticklabels(["0", "50k", "100k", "150k", "200k"])
    ax2.set_title("Cost: an order of magnitude cheaper", fontsize=12.5,
                  fontweight="bold", color=FG, loc="left")
    ax2.tick_params(colors=MUT)
    for s in ["top", "right"]: ax2.spines[s].set_visible(False)
    for s in ["left", "bottom"]: ax2.spines[s].set_color(MUT)

    fig.suptitle("64 GPUs on AWS HyperPod — the same run, re-priced twice",
                 fontsize=14, fontweight="bold", color=FG, x=0.07, ha="left", y=0.95)
    fig.savefig(f"{OUT}/infra.png", facecolor=BG)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Social-share card (1200x630)
# ---------------------------------------------------------------------------
def fig_social():
    fig = plt.figure(figsize=(12, 6.3), dpi=100); fig.patch.set_facecolor("#000")
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor("#000")
    ax.set_xlim(0, 12); ax.set_ylim(0, 6.3); ax.axis("off")

    # text block (left)
    ax.text(0.6, 5.35, "Training a Hebrew LLM", fontsize=33, fontweight="bold",
            color=FG, va="center")
    ax.text(0.62, 4.55, "Behind the scenes of Hebatron", fontsize=20,
            color=CYAN, va="center")
    ax.text(0.62, 3.75,
            "Tokenizers, a Mixture-of-Experts that\n"
            "wouldn't learn, and the batch size that\n"
            "finally broke the benchmarks free.",
            fontsize=14.5, color=MUT, va="top", linespacing=1.5)

    # mini benchmark-breakthrough curve (right)
    bx0, by0, bw, bh = 6.7, 0.95, 4.9, 4.6
    steps = np.linspace(0, 1, 240)
    base = 0.5
    bench = np.where(steps < 0.5,
                     base - 0.10 + 0.04 * np.sin(steps * 22) - steps * 0.12,
                     (base - 0.13) + 0.42 * (1 - np.exp(-(steps - 0.5) / 0.16)))
    # baseline
    ax.plot([bx0, bx0 + bw], [by0 + base * bh] * 2, color=MUT, ls="--", lw=1.4)
    ax.text(bx0 + 0.05, by0 + base * bh + 0.12, "baseline", color=MUT, fontsize=11)
    ax.plot(bx0 + steps * bw, by0 + bench * bh, color=GOLD, lw=3.2)
    # change marker
    ax.axvline  # noop
    ax.plot([bx0 + 0.5 * bw] * 2, [by0, by0 + bh], color=RED, ls="--", lw=1.3)
    ax.text(bx0 + 0.5 * bw, by0 + bh + 0.04, "batch ×8", color=RED, fontsize=11,
            ha="center")
    ax.scatter([bx0 + bw], [by0 + bench[-1] * bh], s=70, color=GOLD,
               edgecolor=FG, zorder=5)
    ax.text(bx0 + bw, by0 + bench[-1] * bh + 0.18, "shipped", color=GOLD,
            fontsize=11, ha="right")
    ax.text(bx0, by0 - 0.28, "Hebrew benchmark score vs training step",
            color=MUT, fontsize=10.5)

    fig.savefig(f"{OUT}/social.png", facecolor="#000")
    plt.close(fig)


if __name__ == "__main__":
    fig_social()
    fig_tokenization()
    fig_base_model()
    fig_data()
    fig_moe_schematic()
    fig_batch_size()
    fig_sft_packing()
    fig_infra()
    print("figures written to", OUT)
