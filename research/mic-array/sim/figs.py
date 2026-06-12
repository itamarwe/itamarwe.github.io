"""Generate response-curve figures for the medium and large arrays."""
import os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import arrays as A

plt.rcParams.update({
    "figure.facecolor": "white", "axes.grid": True, "grid.alpha": 0.25,
    "font.size": 11, "axes.titlesize": 12, "axes.titleweight": "bold",
})
OUT = os.path.join(os.path.dirname(__file__), "..", "out", "figs")
os.makedirs(OUT, exist_ok=True)

COLORS = dict(zip(A.GEOMETRIES, plt.cm.turbo(np.linspace(0.05, 0.95, len(A.GEOMETRIES)))))
FREQS = [300, 1000, 2000, 4000]
APERTURES = {"medium": 0.40, "large": 1.20}


def fig_layouts(aperture, tag):
    fig, axs = plt.subplots(2, 3, figsize=(12, 8))
    for ax, (name, fn) in zip(axs.ravel(), A.GEOMETRIES.items()):
        p = fn(aperture)
        if name.startswith("Hemis"):
            ax.scatter(p[:, 0] * 100, p[:, 1] * 100, c=p[:, 2] * 100,
                       cmap="viridis", s=70, edgecolor="k", zorder=3)
            ax.set_title(f"{name}\n(color = height, dome)")
        else:
            ax.scatter(p[:, 0] * 100, p[:, 1] * 100, c=[COLORS[name]],
                       s=70, edgecolor="k", zorder=3)
            ax.set_title(name)
        lim = aperture * 55
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_aspect("equal")
        ax.set_xlabel("x (cm)"); ax.set_ylabel("y (cm)")
    fig.suptitle(f"16-mic array geometries — {tag} aperture = {aperture*100:.0f} cm",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{OUT}/layouts_{tag}.png", dpi=130); plt.close(fig)


def fig_beampatterns(aperture, tag):
    az = np.linspace(-np.pi, np.pi, 1440)
    fig, axs = plt.subplots(2, 3, figsize=(13, 9),
                            subplot_kw={"projection": "polar"})
    for ax, (name, fn) in zip(axs.ravel(), A.GEOMETRIES.items()):
        p = fn(aperture)
        for f in FREQS:
            P = A.beampattern_az(p, f, az, az0=0.0)
            PdB = 10 * np.log10(P / P.max() + 1e-12)
            PdB = np.clip(PdB, -30, 0)
            ax.plot(az, PdB + 30, lw=1.6, label=f"{f} Hz")
        ax.set_title(name, pad=18)
        ax.set_ylim(0, 30); ax.set_yticks([0, 10, 20, 30])
        ax.set_yticklabels(["-30", "-20", "-10", "0 dB"])
        ax.set_theta_zero_location("N")
    axs[0, 0].legend(loc="upper right", bbox_to_anchor=(1.35, 1.15), fontsize=9)
    fig.suptitle(f"Delay-and-sum beam patterns (steered to 0°, horizontal plane)\n"
                 f"{tag} aperture = {aperture*100:.0f} cm — watch grating lobes appear at high f",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{OUT}/beampatterns_{tag}.png", dpi=130); plt.close(fig)


def fig_curves(aperture, tag):
    fbins = np.linspace(300, 4000, 40)
    psl, bw, di = {}, {}, {}
    for name, fn in A.GEOMETRIES.items():
        p = fn(aperture)
        psl[name] = [A.main_and_sidelobe(p, f)[1] for f in fbins]
        bw[name] = [A.main_and_sidelobe(p, f)[0] for f in fbins]
        di[name] = [A.directivity_index(p, f) for f in fbins]
    fig, axs = plt.subplots(1, 3, figsize=(16, 5))
    for name in A.GEOMETRIES:
        c = COLORS[name]
        axs[0].plot(fbins, psl[name], color=c, lw=2, label=name)
        axs[1].plot(fbins, bw[name], color=c, lw=2, label=name)
        axs[2].plot(fbins, di[name], color=c, lw=2, label=name)
    axs[0].axhline(-3, ls="--", c="r", alpha=.6)
    axs[0].annotate("ambiguity (sidelobe ≈ main)", (3000, -3.6), color="r", fontsize=9)
    axs[0].set_title("Peak sidelobe / grating-lobe level")
    axs[0].set_ylabel("dB below main lobe"); axs[0].set_ylim(-30, 0)
    axs[1].set_title("Main-lobe -3 dB beamwidth"); axs[1].set_ylabel("degrees")
    axs[1].set_yscale("log")
    axs[2].set_title("Directivity index (DS beamformer)"); axs[2].set_ylabel("dB")
    for ax in axs:
        ax.set_xlabel("frequency (Hz)")
    axs[1].legend(fontsize=8, loc="upper right")
    fig.suptitle(f"Broadband response vs frequency — {tag} aperture = {aperture*100:.0f} cm",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{OUT}/curves_{tag}.png", dpi=130); plt.close(fig)


def fig_coarray(aperture, tag):
    sel = ["ULA (line)", "UCA (single ring)", "Spiral (sunflower)", "Random planar"]
    fig, axs = plt.subplots(2, len(sel), figsize=(16, 8))
    for j, name in enumerate(sel):
        p = A.GEOMETRIES[name](aperture)
        ca = A.coarray(p)
        axs[0, j].scatter(ca[:, 0] * 100, ca[:, 1] * 100, s=12,
                          c=[COLORS[name]], alpha=0.6)
        axs[0, j].set_title(f"{name}\nco-array (pairwise baselines)")
        axs[0, j].set_aspect("equal"); axs[0, j].set_xlabel("Δx (cm)")
        axs[0, j].set_ylabel("Δy (cm)")
        L = A.baseline_lengths(p) * 100
        axs[1, j].hist(L, bins=24, color=COLORS[name], alpha=0.8)
        axs[1, j].set_title(f"baseline-length spread\n({len(np.unique(np.round(L,1)))} distinct)")
        axs[1, j].set_xlabel("baseline length (cm)")
    fig.suptitle(f"Spatial-sampling diversity (what a multichannel net sees) — "
                 f"{tag} aperture = {aperture*100:.0f} cm",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{OUT}/coarray_{tag}.png", dpi=130); plt.close(fig)


def fig_tradeoff():
    f = np.linspace(300, 4000, 200)
    lam = A.C_SOUND / f
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(f, lam * 50, "b", lw=2.5, label="λ/2 spacing for NO aliasing (cm)")
    ax.fill_between(f, 0, lam * 50, alpha=0.12, color="b")
    for tag, ap in APERTURES.items():
        ax.axhline(ap * 100 / 15, ls="--",
                   label=f"{tag} array: uniform spacing if 16-in-line ({ap*100/15:.1f} cm)")
    ax.set_xlabel("frequency (Hz)"); ax.set_ylabel("microphone spacing (cm)")
    ax.set_title("The core tradeoff: spacing must shrink with frequency",
                 fontweight="bold")
    ax.annotate("4 kHz needs ≤4.3 cm spacing", (4000, 4.3),
                xytext=(2600, 12), color="#ededed",
                arrowprops=dict(arrowstyle="->", color="#ededed"))
    ax.set_ylim(0, 30); ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{OUT}/tradeoff.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    fig_tradeoff()
    for tag, ap in APERTURES.items():
        print("rendering", tag)
        fig_layouts(ap, tag)
        fig_beampatterns(ap, tag)
        fig_curves(ap, tag)
        fig_coarray(ap, tag)
    print("done ->", OUT)


def fig_recommend(aperture, tag):
    """Compare baseline geometries vs the recommended nested designs."""
    cand = {
        "ULA (line)": A.ula, "UCA (ring)": A.uca,
        "Circular aperiodic": A.circular_aperiodic, "Spiral": A.spiral,
        "Nested aperiodic ★": A.nested_aperiodic, "Nested dome ★3D": A.nested_dome,
    }
    cols = dict(zip(cand, ["#888", "#d95f02", "#a78bfa", "#1b9e77", "#e7298a", "#3fa9f5"]))
    fbins = np.linspace(300, 4000, 36)
    fig = plt.figure(figsize=(16, 9))
    gs = fig.add_gridspec(2, 3)
    axL = fig.add_subplot(gs[0, 0])           # layouts (planar)
    ax3 = fig.add_subplot(gs[1, 0], projection="3d")
    axP = fig.add_subplot(gs[0, 1:])          # PSL
    axB = fig.add_subplot(gs[1, 1:])          # beamwidth
    for name, fn in cand.items():
        p = fn(aperture); c = cols[name]
        if not name.endswith("3D"):
            axL.scatter(p[:, 0]*100, p[:, 1]*100, s=45, color=c,
                        edgecolor="k", label=name, alpha=.8)
        psl = [A.main_and_sidelobe(p, f)[1] for f in fbins]
        bw = [A.main_and_sidelobe(p, f)[0] for f in fbins]
        # The dome shares the planar array's (x,y), so its azimuth-plane response
        # is identical to the nested-aperiodic one — draw it dashed so the line
        # underneath stays visible instead of being painted over.
        is3d = name.endswith("3D")
        style = dict(lw=2.6, ls=(0, (4, 3))) if is3d else dict(lw=2.2)
        axP.plot(fbins, psl, color=c, label=name, **style)
        axB.plot(fbins, bw, color=c, label=name, **style)
    pr = A.nested_dome(aperture)
    ax3.scatter(pr[:, 0]*100, pr[:, 1]*100, pr[:, 2]*100, s=45,
                c=pr[:, 2], cmap="plasma", edgecolor="k")
    ax3.set_title("Recommended nested dome (3D)", fontsize=11)
    ax3.set_xlabel("x cm"); ax3.set_ylabel("y cm"); ax3.set_zlabel("z cm")
    axL.set_aspect("equal"); axL.set_title("Planar layouts (cm)")
    axL.legend(fontsize=8, loc="upper right")
    axP.axhline(-3, ls="--", c="r", alpha=.5)
    axP.set_title("Peak sidelobe vs frequency (higher = better, fewer ambiguities)")
    axP.set_ylabel("dB below main"); axP.set_ylim(-30, 0); axP.set_xlabel("Hz")
    axP.legend(fontsize=9)
    axP.annotate("dome (dashed) traces the nested-aperiodic line exactly:\n"
                 "in the azimuth plane height adds no phase — the dome's\n"
                 "real edge is elevation, which this cut can't show",
                 xy=(0.5, 0.04), xycoords="axes fraction", ha="center",
                 fontsize=8.5, color="#9aa4b2")
    axB.set_title("Main-lobe beamwidth vs frequency (lower = sharper bearing)")
    axB.set_ylabel("degrees"); axB.set_yscale("log"); axB.set_xlabel("Hz")
    for ax in (axP, axB):
        ax.grid(alpha=.25)
    fig.suptitle(f"Recommendation backing — {tag} aperture = {aperture*100:.0f} cm",
                 fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{OUT}/recommend_{tag}.png", dpi=130); plt.close(fig)


if __name__ == "__main__" and "RECO" in os.environ:
    for tag, ap in APERTURES.items():
        fig_recommend(ap, tag)
    print("recommend figs done")
