"""
3blue1brown-style manim scenes for the mic-array study.
Render e.g.:  manim -qh anim.py Aliasing
No LaTeX dependency: all labels use Text / Unicode.
"""
import sys, os
import numpy as np
from manim import *

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sim"))
import arrays as A

# 3b1b-ish palette
BG = "#0e1116"
ACC = "#3fc1ff"      # cyan
WARN = "#ff5a5a"     # red
GOOD = "#7CFC8A"     # green
GOLD = "#ffd166"
config.background_color = BG

C = A.C_SOUND


def mic_dots(xs, ys, color=GOLD, r=0.07):
    g = VGroup()
    for x, y in zip(xs, ys):
        g.add(Dot([x, y, 0], radius=r, color=color).set_z_index(5))
    return g


# --------------------------------------------------------------------------
class Aliasing(Scene):
    """Two incidence angles produce identical phase samples when mics are
    spaced wider than lambda/2 -> spatial aliasing / grating lobe."""
    def construct(self):
        title = Text("Spatial aliasing: why mic spacing must shrink with frequency",
                     font_size=30).to_edge(UP)
        self.play(Write(title))

        # microphone row
        N = 6
        d = 1.4                     # on-screen spacing
        xs = (np.arange(N) - (N - 1) / 2) * d
        mics = mic_dots(xs, np.zeros(N) - 1.8)
        base = Line([xs[0] - .6, -1.8, 0], [xs[-1] + .6, -1.8, 0], color=GREY)
        self.play(Create(base), FadeIn(mics))
        lab = Text("6-mic line, spacing d", font_size=24, color=GOLD).next_to(base, DOWN)
        self.play(FadeIn(lab))

        t = ValueTracker(0.0)
        lam = 2.2                   # on-screen wavelength
        k = 2 * np.pi / lam
        omega = 2.0

        def wavefronts(theta, color):
            """parallel moving lines perpendicular to propagation dir theta."""
            def mk():
                grp = VGroup()
                # propagation direction
                dirx, diry = np.sin(theta), -np.cos(theta)
                px, py = -diry, dirx     # wavefront line direction
                for n in range(-4, 5):
                    phase = (n * lam + (omega / k) * t.get_value())
                    cx = dirx * phase
                    cy = diry * phase - 0.2
                    p1 = np.array([cx - px * 5, cy - py * 5, 0])
                    p2 = np.array([cx + px * 5, cy + py * 5, 0])
                    grp.add(Line(p1, p2, color=color, stroke_width=2, stroke_opacity=0.5))
                return grp
            return always_redraw(mk)

        theta1 = np.deg2rad(20)
        wf1 = wavefronts(theta1, ACC)
        self.add(wf1)
        ang1 = Text("wave from 20°", font_size=24, color=ACC).to_corner(UL).shift(DOWN*0.7)
        self.play(FadeIn(ang1))
        self.play(t.animate.set_value(3), run_time=3, rate_func=linear)

        # sampled phasors under each mic
        def phasor_group(theta):
            def mk():
                grp = VGroup()
                for x in xs:
                    ph = k * x * np.sin(theta) + omega * t.get_value() * 0  # frozen sample
                    ph = k * x * np.sin(theta)
                    c = Circle(radius=0.30, color=GREY, stroke_width=2).move_to([x, -2.5, 0])
                    arr = Arrow(c.get_center(),
                                c.get_center() + 0.30 * np.array([np.cos(ph), np.sin(ph), 0]),
                                buff=0, color=WARN, stroke_width=4, max_tip_length_to_length_ratio=0.4)
                    grp.add(c, arr)
                return grp
            return mk()

        ph1 = phasor_group(theta1)
        self.play(FadeIn(ph1))
        plab = Text("phase sampled at each mic", font_size=22).next_to(ph1, DOWN, buff=0.15)
        self.play(FadeIn(plab))
        self.wait(0.5)

        # alias angle: k d sin(theta2) = k d sin(theta1) + 2 pi  -> ambiguous
        # use the *physical* relation with real spacing for the message
        self.play(FadeOut(wf1), FadeOut(ang1))
        # compute alias angle for on-screen geometry
        sin2 = np.sin(theta1) + 2 * np.pi / (k * d)
        if abs(sin2) <= 1:
            theta2 = np.arcsin(sin2)
        else:
            theta2 = np.deg2rad(-55)   # fallback
        wf2 = wavefronts(theta2, GOOD)
        ang2 = Text(f"wave from {np.rad2deg(theta2):.0f}°  (different direction!)",
                    font_size=24, color=GOOD).to_corner(UL).shift(DOWN*0.7)
        self.add(wf2); self.play(FadeIn(ang2))
        self.play(t.animate.set_value(6), run_time=3, rate_func=linear)
        ph2 = phasor_group(theta2)
        self.play(Transform(ph1, ph2))
        same = Text("…but the mics see the SAME phases — the array can't tell them apart",
                    font_size=26, color=WARN).to_edge(DOWN)
        self.play(Write(same))
        self.wait(1.5)
        self.play(FadeOut(same), FadeOut(ph1), FadeOut(plab), FadeOut(wf2),
                  FadeOut(ang2), FadeOut(base), FadeOut(mics), FadeOut(lab))
        rule = Text("Fix: keep the smallest spacing ≤ λ/2  →  ≤ 4.3 cm at 4 kHz",
                    font_size=30, color=ACC).move_to([0, -0.5, 0])
        self.play(Write(rule))
        self.wait(2)


# --------------------------------------------------------------------------
def polar_curve(pos, f, center, rscale=2.1, floor=-30, az0=0.0, n=720):
    az = np.linspace(-np.pi, np.pi, n)
    P = A.beampattern_az(pos, f, az, az0=az0)
    PdB = np.clip(10 * np.log10(P / P.max() + 1e-12), floor, 0)
    rr = rscale * (PdB - floor) / (-floor)
    pts = [center + np.array([r * np.cos(a), r * np.sin(a), 0]) for a, r in zip(az, rr)]
    vm = VMobject().set_points_as_corners(pts)
    return vm, az, PdB


def mini_array(pos, center, fit=0.9, color=GOLD):
    p = pos.copy()
    s = fit / (np.abs(p[:, :2]).max() + 1e-9)
    g = VGroup()
    for x, y, _ in p:
        g.add(Dot(center + np.array([x * s, y * s, 0]), radius=0.05, color=color))
    return g


class BeamForming(Scene):
    """How geometry shapes the beam pattern: uniform ring grows grating lobes,
    aperiodic spiral smears them into a low floor."""
    def construct(self):
        title = Text("Geometry shapes the beam pattern (medium 40 cm, f = 3 kHz)",
                     font_size=30).to_edge(UP)
        self.play(Write(title))
        f = 3000
        ap = 0.40
        specs = [("UCA (single ring)", A.uca(ap), LEFT * 3.4, WARN),
                 ("Spiral (sunflower)", A.spiral(ap), RIGHT * 3.4, GOOD)]
        for name, pos, shift, col in specs:
            center = shift + DOWN * 0.4
            ringgrid = VGroup(*[Circle(radius=2.1 * frac, color=GREY,
                                       stroke_width=1, stroke_opacity=0.25).move_to(center)
                                for frac in (0.33, 0.66, 1.0)])
            arr = mini_array(pos, center, color=col)
            nm = Text(name, font_size=24, color=col).next_to(ringgrid, UP, buff=0.1)
            self.play(FadeIn(ringgrid), FadeIn(arr), FadeIn(nm), run_time=0.6)
            curve, az, PdB = polar_curve(pos, f, center, az0=0.0)
            curve.set_stroke(col, width=3)
            self.play(Create(curve), run_time=2.2)
            # flag secondary lobes within 6 dB of main
            mask = (np.abs(np.rad2deg(az)) > 25) & (PdB > -6)
            if mask.any():
                a = az[mask][np.argmax(PdB[mask])]
                r = 2.1 * (PdB[mask].max() + 30) / 30
                gl = center + np.array([r * np.cos(a), r * np.sin(a), 0])
                self.play(Flash(gl, color=WARN, flash_radius=0.4))
        cap = Text("Same 16 mics, same aperture — aperiodic spacing trades\n"
                   "discrete grating lobes for a diffuse sidelobe floor",
                   font_size=24, color=ACC, line_spacing=0.6).to_edge(DOWN)
        self.play(Write(cap))
        self.wait(2)


class CoArray(Scene):
    """The co-array: every mic PAIR is one spatial-coherence measurement a
    multichannel network can use. Aperiodic geometry => richer, less redundant."""
    def construct(self):
        title = Text("What a 16-channel network really sees: the co-array",
                     font_size=30).to_edge(UP)
        sub = Text("each line = one microphone pair = one independent baseline (TDOA/coherence cue)",
                   font_size=22, color=GREY).next_to(title, DOWN, buff=0.12)
        self.play(Write(title), FadeIn(sub))
        ap = 0.40
        specs = [("UCA — redundant", A.uca(ap), LEFT * 3.6, WARN),
                 ("Spiral — rich", A.spiral(ap), RIGHT * 3.6, GOOD)]
        for name, pos, shift, col in specs:
            center = shift + DOWN * 0.5
            arr = mini_array(pos, center, fit=1.4, color=GOLD)
            arr_dots = [d.get_center() for d in arr]
            nm = Text(name, font_size=24, color=col).next_to(arr, UP, buff=0.35)
            self.play(FadeIn(arr), FadeIn(nm), run_time=0.5)
            lines = VGroup()
            M = len(arr_dots)
            for i in range(M):
                for j in range(i + 1, M):
                    lines.add(Line(arr_dots[i], arr_dots[j], stroke_width=1.2,
                                   color=col, stroke_opacity=0.35))
            self.play(LaggedStartMap(Create, lines, lag_ratio=0.004, run_time=2.2))
            cnt = len(A.baseline_lengths(pos)) // 2
            uniq = len(np.unique(np.round(A.baseline_lengths(pos), 3)))
            t = Text(f"{cnt} pairs · {uniq} distinct lengths",
                     font_size=20, color=col).next_to(arr, DOWN, buff=0.3)
            self.play(FadeIn(t))
        cap = Text("More distinct baselines ⇒ more independent spatial features ⇒\n"
                   "easier detection & coarse bearing without textbook beamforming",
                   font_size=23, color=ACC, line_spacing=0.6).to_edge(DOWN)
        self.play(Write(cap))
        self.wait(2)


class Recommended(ThreeDScene):
    """Capstone: the recommended nested-aperiodic dome in 3D."""
    def construct(self):
        ap = 0.40
        pos = A.nested_dome(ap)
        scale = 5.0 / ap
        title = Text("Recommended: nested-aperiodic dome (16 mics)",
                     font_size=30)
        self.add_fixed_in_frame_mobjects(title)
        title.to_edge(UP)
        self.set_camera_orientation(phi=68 * DEGREES, theta=-50 * DEGREES)
        # ground disk
        disk = Circle(radius=ap / 2 * scale, color=GREY, stroke_opacity=0.5)
        dots = VGroup()
        for x, y, z in pos:
            col = interpolate_color(ManimColor(GOLD), ManimColor(ACC),
                                    min(z / (0.25 * ap), 1))
            d = Dot3D([x * scale, y * scale, z * scale], radius=0.10, color=col)
            stem = Line([x*scale, y*scale, 0], [x*scale, y*scale, z*scale],
                        color=GREY, stroke_width=1, stroke_opacity=0.4)
            dots.add(stem, d)
        self.play(Create(disk))
        self.play(LaggedStartMap(FadeIn, dots, lag_ratio=0.05, run_time=2))
        notes = VGroup(
            Text("• tight centre cluster → clean cues up to 4 kHz", font_size=22, color=GOLD),
            Text("• wide outriggers → 300 Hz resolution", font_size=22, color=GOOD),
            Text("• out-of-plane height → elevation / overhead FPV", font_size=22, color=ACC),
            Text("• aperiodic → no grating lobes, ideal for a 16-ch net", font_size=22, color=WHITE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.18).to_corner(DL)
        self.add_fixed_in_frame_mobjects(notes)
        self.play(LaggedStartMap(FadeIn, notes, lag_ratio=0.3, run_time=2))
        self.begin_ambient_camera_rotation(rate=0.5)
        self.wait(6)
        self.stop_ambient_camera_rotation()
