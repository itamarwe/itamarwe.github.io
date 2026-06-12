"""Static explanatory figures for the literature-review section (dark 3b1b style)."""
import os, sys, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
sys.path.insert(0, os.path.dirname(__file__))
import arrays as A

BG, FG, GREY = "#0e1116", "#ededed", "#9aa4b2"
CYAN, GOLD, GREEN, RED = "#3fc1ff", "#ffd166", "#7CFC8A", "#ff5a5a"
plt.rcParams.update({"figure.facecolor": BG, "savefig.facecolor": BG,
                     "text.color": FG, "font.size": 11})
OUT = os.path.join(os.path.dirname(__file__), "..", "out", "figs")
os.makedirs(OUT, exist_ok=True)


def _box(ax, x, y, w, h, text, ec, fc="#161b22", tc=FG, fs=11, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle="round,pad=0.006,rounding_size=0.02",
                 linewidth=1.8, edgecolor=ec, facecolor=fc, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            color=tc, fontsize=fs, zorder=3, weight=weight)


def _arrow(ax, x1, y1, x2, y2, color=GREY):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                 mutation_scale=15, color=color, lw=1.7, zorder=1))


def fig_pipeline():
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.5, 0.95, "Two ways to turn 16 channels into a detection",
            ha="center", fontsize=16, weight="bold")

    xs = [0.045, 0.255, 0.465, 0.675, 0.85]   # box left edges
    w = 0.145
    # ---- multi-step row ----
    y, h = 0.60, 0.17
    ax.text(0.045, 0.82, "MULTI-STEP  ·  cascaded", color=RED, fontsize=13, weight="bold")
    ax.text(0.045, 0.785, "each stage trained / tuned separately", color=GREY, fontsize=10)
    _box(ax, xs[0], y, w, h, "16-ch\naudio", CYAN, fs=11)
    _box(ax, xs[1], y, w, h, "features\nspectrogram /\nGCC-PHAT", GREY, fs=10)
    _box(ax, xs[2], y, w, h, "detect\n(SED)", GOLD, fs=11)
    _box(ax, xs[3], y, w, h, "localize\nMUSIC / SRP-PHAT", GOLD, fs=9.5)
    _box(ax, xs[4]-0.0, y, w, h, "drone?\n+ bearing", GREEN, fs=10)
    for a, b in zip(xs[:-1], xs[1:]):
        _arrow(ax, a + w, y + h / 2, b, y + h / 2)
    ax.text((xs[2]+xs[3])/2 + w/2, y - 0.05, "errors propagate →",
            ha="center", color=RED, fontsize=9.5, style="italic")

    # ---- one-step row ----
    y2, h2 = 0.20, 0.17
    ax.text(0.045, 0.45, "ONE-STEP  ·  joint network", color=GREEN, fontsize=13, weight="bold")
    ax.text(0.045, 0.415, "a single multichannel model — CRNN / ACCDOA", color=GREY, fontsize=10)
    _box(ax, xs[0], y2, w, h2, "16-ch\naudio", CYAN, fs=11)
    _box(ax, xs[1], y2, w, h2, "features\nraw / GCC-PHAT", GREY, fs=10)
    _box(ax, xs[2], y2, (xs[3]+w) - xs[2], h2,
         "one multichannel network\n(learns the spatial cues)", CYAN, fc="#10212e",
         fs=11, weight="bold")
    _box(ax, xs[4], y2, w, h2, "drone?\n+ bearing\n(together)", GREEN, fs=10)
    _arrow(ax, xs[0]+w, y2+h2/2, xs[1], y2+h2/2)
    _arrow(ax, xs[1]+w, y2+h2/2, xs[2], y2+h2/2)
    _arrow(ax, xs[3]+w, y2+h2/2, xs[4], y2+h2/2)
    ax.text((xs[2]+xs[3]+w)/2, y2 - 0.05, "one model, one objective",
            ha="center", color=GREEN, fontsize=9.5, style="italic")

    fig.savefig(f"{OUT}/algorithms_pipeline.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def coprime_linear(span, M=4, N=3):
    """A coprime linear array (two interleaved ULAs) for illustration."""
    d = span / (M * N)
    s = sorted(set(list(np.arange(N) * M * d) + list(np.arange(M) * N * d)))
    s = np.array(s) - np.mean(s)
    return np.column_stack([s, np.zeros(len(s)), np.zeros(len(s))])


def fig_topologies():
    panels = [
        ("Uniform line (ULA)", A.ula(0.4), "uniform"),
        ("Uniform ring (UCA)", A.uca(0.4), "uniform"),
        ("Aperiodic planar (spiral)", A.spiral(0.4), "aperiodic"),
        ("Sparse · coprime", coprime_linear(0.4), "sparse"),
        ("Sparse · nested multi-scale", A.nested_aperiodic(0.4), "sparse"),
        ("3-D volumetric (dome)", A.nested_dome(0.4), "3d"),
    ]
    fam = {"uniform": GOLD, "aperiodic": GREEN, "sparse": CYAN, "3d": RED}
    fig, axs = plt.subplots(2, 3, figsize=(13, 7.2))
    for ax, (name, p, f) in zip(axs.ravel(), panels):
        ax.set_facecolor(BG)
        if f == "3d":
            sc = ax.scatter(p[:, 0]*100, p[:, 1]*100, c=p[:, 2]*100, cmap="plasma",
                            s=70, edgecolor="k", linewidth=0.5, zorder=3)
        else:
            ax.scatter(p[:, 0]*100, p[:, 1]*100, c=fam[f], s=70,
                       edgecolor="k", linewidth=0.5, zorder=3)
        ax.set_title(name, color=fam[f], fontsize=12, weight="bold", pad=8)
        ax.set_xlim(-24, 24); ax.set_ylim(-24, 24); ax.set_aspect("equal")
        for s in ax.spines.values():
            s.set_color("#2a323c")
        ax.tick_params(colors=GREY, labelsize=8)
        ax.set_xlabel("cm  ·  colour = height" if f == "3d" else "cm",
                      color=GREY, fontsize=8)
        ax.grid(alpha=0.12)
    fig.suptitle("The microphone-array topology families", color=FG,
                 fontsize=16, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(f"{OUT}/topology_families.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    fig_pipeline()
    fig_topologies()
    print("wrote algorithms_pipeline.png and topology_families.png")


def circular_aperiodic(aperture, M=16, seed=3):
    R = aperture/2
    rng = np.random.RandomState(seed)
    i = np.arange(M)
    ang = (i + 0.5*rng.uniform(-1, 1, M)) * 2*np.pi/M
    return np.column_stack([R*np.cos(ang), R*np.sin(ang), np.zeros(M)])


def fig_baseline_hist(aperture=1.20, tag="large"):
    configs = [("ULA (line)", A.ula, GOLD),
               ("UCA (uniform ring)", A.uca, GOLD),
               ("Circular aperiodic", circular_aperiodic, CYAN),
               ("Spiral (disk)", A.spiral, GREEN),
               ("Nested aperiodic ★", A.nested_aperiodic, "#e7298a")]
    maxL = aperture*100
    bins = np.linspace(0, maxL*1.02, 26)
    fig, axs = plt.subplots(1, 5, figsize=(16, 3.7))
    for k, (ax, (name, fn, c)) in enumerate(zip(axs, configs)):
        p = fn(aperture); L = A.baseline_lengths(p)*100
        ax.hist(L, bins=bins, color=c, alpha=0.85, zorder=2)
        nd = len(np.unique(np.round(A.baseline_lengths(p), 3)))
        ax.axvline(4.3, ls="--", color="#ededed", lw=1.2, alpha=0.7, zorder=3)
        ax.set_title(f"{name}\n{nd} distinct · {120/nd:.0f}× redundant",
                     color=c, fontsize=11, weight="bold")
        ax.set_xlabel("baseline length (cm)", color=GREY, fontsize=9)
        ax.set_xlim(0, maxL*1.02)
        ax.set_facecolor(BG)
        for s in ax.spines.values():
            s.set_color("#2a323c")
        ax.tick_params(colors=GREY, labelsize=8)
        ax.grid(alpha=0.12)
        if k == 4:
            ax.annotate("← baselines here\nserve 4 kHz\n(λ/2 = 4.3 cm)",
                        xy=(4.3, 0), xytext=(0.42, 0.7), textcoords="axes fraction",
                        color="#ededed", fontsize=8.5,
                        arrowprops=dict(arrowstyle="->", color="#ededed"))
    axs[0].set_ylabel("number of mic pairs", color=GREY, fontsize=9)
    fig.suptitle(f"Where each array puts its 120 baselines  —  {tag} aperture {aperture*100:.0f} cm",
                 color=FG, fontsize=15, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(f"{OUT}/baseline_histograms_{tag}.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__" and os.environ.get("HIST"):
    fig_baseline_hist(1.20, "large")
    fig_baseline_hist(0.40, "medium")
    print("baseline histograms done")


def fig_directionality(aperture=1.20, tag="large", f=2000):
    """A beam pattern is not one number — it depends on *where you look*.
    Steer each array endfire (along the array axis) vs broadside (perpendicular)
    and plot the azimuth-plane response. The ULA flips between a fat, low-res
    lobe (endfire) and a sharp but mirror-ambiguous one (broadside); a 2-D array
    barely changes."""
    geoms = [("ULA (line)", A.ula, GOLD),
             ("UCA (uniform ring)", A.uca, CYAN),
             ("Nested aperiodic ★", A.nested_aperiodic, "#e7298a")]
    steers = [("endfire — steered ALONG the array (0°)", 0.0),
              ("broadside — steered PERPENDICULAR (90°)", np.pi / 2)]
    az = np.linspace(-np.pi, np.pi, 1600)
    fig, axs = plt.subplots(2, 3, figsize=(14, 9.4),
                            subplot_kw={"projection": "polar"})
    for r, (slabel, az0) in enumerate(steers):
        for c, (name, fn, col) in enumerate(geoms):
            ax = axs[r, c]
            p = fn(aperture)
            P = A.beampattern_az(p, f, az, az0=az0)
            PdB = np.clip(10 * np.log10(P / P.max() + 1e-12), -30, 0)
            ax.plot(az, PdB + 30, color=col, lw=2.0, zorder=3)
            ax.fill(az, PdB + 30, color=col, alpha=0.18, zorder=2)
            # the intended look direction
            ax.plot([az0, az0], [0, 30], color="#3fc1ff", lw=1.6,
                    ls=(0, (3, 2)), zorder=4)
            bw, psl = A.main_and_sidelobe(p, f, az0=az0)
            ax.set_theta_zero_location("E")     # 0° = +x = the array axis
            ax.set_ylim(0, 30); ax.set_yticks([10, 20, 30])
            ax.set_yticklabels(["-20", "-10", "0 dB"], color=GREY, fontsize=7)
            ax.tick_params(colors=GREY, labelsize=8)
            ax.set_facecolor(BG)
            ax.grid(color="#2a323c", alpha=0.6)
            tag_amb = "  ·  ⚠ ±mirror" if psl > -3 else ""
            ax.set_title(f"{name}\nbeamwidth ≈ {bw:.0f}°{tag_amb}",
                         color=col, fontsize=11, weight="bold", pad=12)
        axs[r, 0].text(-0.32, 0.5, slabel.split(" — ")[0].upper(),
                       transform=axs[r, 0].transAxes, rotation=90,
                       va="center", ha="center", color="#3fc1ff",
                       fontsize=12, weight="bold")
    # explanatory captions under each row
    axs[0, 0].annotate("steered along the array → fat, low-resolution lobe",
                       xy=(0.5, -0.16), xycoords="axes fraction", ha="center",
                       color=GREY, fontsize=9)
    axs[1, 0].annotate("sharp — but a twin lobe at −90° it can't rule out",
                       xy=(0.5, -0.16), xycoords="axes fraction", ha="center",
                       color="#ff5a5a", fontsize=9)
    axs[0, 2].annotate("2-D array: nearly the same beam in every direction",
                       xy=(0.5, -0.16), xycoords="axes fraction", ha="center",
                       color=GREY, fontsize=9)
    axs[1, 2].annotate("steer-invariant — no preferred axis, no mirror",
                       xy=(0.5, -0.16), xycoords="axes fraction", ha="center",
                       color=GREY, fontsize=9)
    fig.suptitle(f"The same array, two look directions  —  {tag} aperture "
                 f"{aperture*100:.0f} cm @ {f} Hz\n"
                 "blue dashes = where we steer; the lobe is where the array "
                 "actually listens",
                 color=FG, fontsize=15, weight="bold")
    fig.tight_layout(rect=[0.02, 0, 1, 0.93])
    fig.savefig(f"{OUT}/directionality_{tag}.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__" and os.environ.get("DIR"):
    fig_directionality(1.20, "large")
    print("directionality figure done")
