"""
Condensed 3-slide version of "Neurovascular Disease in Women" that keeps the
original visualisations from the 14-slide deck, shrunk into grouped panels.
Same 3Blue1Brown / manim style.
"""
import os
import numpy as np
import matplotlib
from matplotlib.patches import Wedge
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
from manimlike import (
    new_slide, glow_line, glow_dot, arrow, rbox, title, lightning,
    draw_brain, draw_circle_of_willis,
    W, H, BG, WHITE, GREY, GREY_D, BLUE_B, BLUE, BLUE_D, BLUE_E, TEAL,
    GREEN, YELLOW, GOLD, RED, MAROON, PURPLE, PINK,
)


# ----------------------------------------------------------------------------
# panel frame
# ----------------------------------------------------------------------------
def panel(ax, cx, cy, w, h, accent, head):
    rbox(ax, cx, cy, w, h, accent, fill=0.045, lw=1.5)
    ax.text(cx - w/2 + 0.4, cy + h/2 - 0.42, head, fontsize=14, color=accent,
            ha="left", va="center", weight="bold")
    return cx, cy + h/2 - 0.42  # header baseline


# ----------------------------------------------------------------------------
# mini visualisations (compact reworks of the full-deck figures)
# ----------------------------------------------------------------------------
def mini_balance(ax, px, py):
    tilt = -13 * np.pi / 180
    L = 3.2
    dx, dy = (L/2)*np.cos(tilt), (L/2)*np.sin(tilt)
    glow_line(ax, [px-0.45, px, px+0.45], [py-0.95, py, py-0.95], GREY, lw=1.6, glow=False)
    glow_line(ax, [px-dx, px+dx], [py-dy, py+dy], WHITE, lw=2.4)
    for sgn, col, lab in [(-1, BLUE_B, "Bleeding"), (1, RED, "Clotting")]:
        ex, ey = px + sgn*dx, py + sgn*dy
        glow_dot(ax, ex, ey, col, r=0.05)
        ax.add_patch(Wedge((ex, ey-0.6), 0.5, 200, 340, width=0.09, color=col, alpha=0.9))
        glow_line(ax, [ex, ex], [ey, ey-0.6], col, lw=1.1, glow=False)
        ax.text(ex, ey-1.32, lab, fontsize=11, color=col, ha="center", weight="bold")
    arrow(ax, (px+0.7, py+1.25), (px+1.35, py+0.62), RED, lw=2.0, mut=12)
    ax.text(px+1.05, py+1.5, "pregnancy", fontsize=10.5, color=RED, ha="center")


def mini_timeline(ax, px, py, w=5.6):
    # big stat
    ax.text(px-2.55, py+1.05, "16–41", fontsize=30, color=RED, ha="center",
            weight="bold")
    ax.text(px-2.55, py+0.35, "ischemic strokes", fontsize=10, color=WHITE, ha="center")
    ax.text(px-2.55, py+0.0, "per 100,000", fontsize=9.5, color=GREY, ha="center")
    # timeline
    x0, x1, y = px-1.1, px + w/2, py - 0.1
    glow_line(ax, [x0, x1], [y, y], GREY, lw=1.4, glow=False)
    xs = np.linspace(x0, x1, 160)
    f = (xs-x0)/(x1-x0)
    risk = 0.18 + 0.14*f + 0.85*np.exp(-((f-0.8)**2)/0.012)
    glow_line(ax, xs, y + risk, RED, lw=2.0)
    marks = [("T1", 0.12, BLUE_E), ("T2", 0.34, BLUE_E), ("T3", 0.54, GOLD),
             ("delivery", 0.7, RED), ("6 wk pp", 0.9, RED)]
    for lab, fp, col in marks:
        xx = x0 + fp*(x1-x0)
        glow_dot(ax, xx, y, col, r=0.04)
        ax.text(xx, y-0.34, lab, fontsize=9, color=col, ha="center")
    ax.text((x0+x1)/2, y+1.35, "relative stroke risk", fontsize=10, color=RED, ha="center")


def mini_cascade(ax, px, py):
    steps = [("Placental\nischemia", MAROON), ("Hypertension", GOLD),
             ("Endothelial\ninjury", RED)]
    xs = [px-2.05, px-0.05, px+1.95]
    by = py + 0.7
    for (txt, col), x in zip(steps, xs):
        rbox(ax, x, by, 1.55, 0.8, col, fill=0.12, lw=1.3, round_pad=0.05)
        ax.text(x, by, txt, fontsize=9.8, color=WHITE, ha="center", va="center")
    for a, b in zip(xs[:-1], xs[1:]):
        arrow(ax, (a+0.82, by), (b-0.82, by), WHITE, lw=1.6, mut=11)
    arrow(ax, (px+1.95, by-0.45), (px+1.95, by-0.95), RED, lw=1.8, mut=12)
    ax.text(px+0.1, by-1.15, "Brain:  seizures · stroke · hemorrhage · PRES",
            fontsize=10.3, color=RED, ha="center", weight="bold")


def mini_pres(ax, px, py):
    s = 0.92
    draw_brain(ax, px, py, s, color=BLUE_B, sulci=True, lw=1.5)
    ax.add_patch(matplotlib.patches.Circle((px - s*0.95, py), s*0.5, color=PURPLE, alpha=0.16))
    ax.add_patch(matplotlib.patches.Circle((px - s*0.85, py), s*0.3, color=PURPLE, alpha=0.22))
    ax.text(px - s*1.0, py - s*1.05, "posterior\nwhite-matter edema",
            fontsize=9.5, color=PURPLE, ha="center", va="top")
    for i, (t, c) in enumerate([("visual loss", PURPLE), ("seizures", RED),
                                ("headache", BLUE_B)]):
        ax.text(px + s*1.5, py + 0.55 - i*0.5, t, fontsize=10.5, color=c, ha="left",
                va="center")
        glow_dot(ax, px + s*1.35, py + 0.55 - i*0.5, c, r=0.05)


def mini_rcvs(ax, px, py):
    x0, x1, y = px-2.7, px+1.5, py+0.15
    xs = np.linspace(x0, x1, 240)
    f = (xs-x0)/(x1-x0)
    wth = 0.12*(1 + 0.8*np.cos(2*np.pi*4.5*f))
    glow_line(ax, xs, y+wth, RED, lw=1.3, glow=False)
    glow_line(ax, xs, y-wth, RED, lw=1.3, glow=False)
    ax.fill_between(xs, y-wth, y+wth, color=RED, alpha=0.12)
    ax.text((x0+x1)/2, y+0.7, "segmental 'string-of-beads'", fontsize=10,
            color=YELLOW, ha="center")
    lightning(ax, px+2.3, py+0.2, 0.5, color=YELLOW)
    ax.text(px+2.3, py-0.75, "thunderclap\nheadache", fontsize=9.5, color=YELLOW,
            ha="center", va="top")
    ax.text(px-0.6, py-0.95, "monophasic · resolves in weeks", fontsize=9.5,
            color=GREY, ha="center", style="italic")


def mini_cvt(ax, px, py):
    s = 0.82
    draw_brain(ax, px, py, s, color=BLUE_B, sulci=True, lw=1.4)
    th = np.linspace(0.15, np.pi-0.15, 70)
    sx = px + s*1.35*1.02*np.cos(th)
    sy = py + s*1.0*1.02*np.sin(th)
    glow_line(ax, sx, sy, BLUE, lw=2.4)
    cx_, cy_ = px + s*0.2, py + s*1.0*1.02
    glow_dot(ax, cx_, cy_, RED, r=0.1)
    ax.text(cx_-0.95, cy_+0.05, "thrombus", fontsize=9.5, color=RED, ha="right")
    arrow(ax, (cx_-0.85, cy_+0.05), (cx_-0.18, cy_), RED, lw=1.3, mut=9)
    ax.text(px + s*1.55, py+0.2, "sinuses clot in\nthe peripartum\nwindow",
            fontsize=10, color=WHITE, ha="left", va="center")
    ax.text(px, py - s*1.45, "Treat: anticoagulation (LMWH)", fontsize=10,
            color=GREEN, ha="center")


def mini_migraine(ax, px, py):
    items = [("baseline", 1.0, GREY), ("aura", 1.9, GOLD), ("+ estrogen", 3.4, RED)]
    bx = [px-2.0, px-0.1, px+1.9]
    base_y = py - 0.85
    for (lab, h, col), x in zip(items, bx):
        H_ = 0.27*h
        rbox(ax, x, base_y + H_/2, 1.2, H_, col, fill=0.16, lw=1.2, round_pad=0.04)
        ax.text(x, base_y - 0.3, lab, fontsize=10, color=col, ha="center", va="top")
    for a, b in zip(bx[:-1], bx[1:]):
        ax.text((a+b)/2, base_y + 0.2, "$\\times$", fontsize=16, color=WHITE,
                ha="center", va="center")
    ax.text(px, py+1.0, "aura $\\times$ estrogen-containing contraception",
            fontsize=10.3, color=RED, ha="center", weight="bold")
    ax.text(px, py+0.66, "= absolute contraindication to CHC", fontsize=10.3,
            color=RED, ha="center", weight="bold")


def mini_stress(ax, px, py):
    rows = [("Gest. diabetes", "$\\to$ ~50% diabetes / 5 yr", GOLD),
            ("Gest. hypertension", "$\\to$ 2–4$\\times$ later HTN", MAROON),
            ("Pre-eclampsia", "$\\to$ $\\geq$2$\\times$ stroke later", RED)]
    for i, (a, b, col) in enumerate(rows):
        y = py + 0.75 - i*0.78
        rbox(ax, px-1.55, y, 2.5, 0.5, col, fill=0.1, lw=1.1, round_pad=0.04)
        ax.text(px-1.55, y, a, fontsize=10.3, color=col, ha="center", va="center",
                weight="bold")
        ax.text(px+0.05, y, b, fontsize=10.3, color=WHITE, ha="left", va="center")


def mini_af(ax, px, py):
    ax.text(px, py+1.05, "annual stroke risk, nonvalvular AF", fontsize=9.8,
            color=GREY, ha="center")
    # small irregular ECG strip
    x = np.linspace(px-2.6, px+2.6, 500)
    base = py + 0.55
    rng = np.random.default_rng(3)
    yv = np.zeros_like(x) + base
    for sp in np.sort(rng.uniform(px-2.4, px+2.4, 9)):
        yv += 0.22*np.exp(-((x-sp)**2)/0.0009)
    glow_line(ax, x, yv, TEAL, lw=1.3)
    base_y = py - 1.05
    for lab, val, col, bx in [("Women", 6.2, RED, px-1.2), ("Men", 4.2, BLUE, px+1.2)]:
        h = 0.16*val
        rbox(ax, bx, base_y + h/2, 1.0, h, col, fill=0.18, lw=1.2, round_pad=0.04)
        ax.text(bx, base_y + h + 0.2, f"{val:.1f}%", fontsize=12, color=col,
                ha="center", weight="bold")
        ax.text(bx, base_y - 0.25, lab, fontsize=10, color=WHITE, ha="center")


def mini_lupus(ax, px, py):
    ax.text(px-1.9, py+0.2, "78%", fontsize=30, color=PURPLE, ha="center", weight="bold")
    ax.text(px-1.9, py-0.5, "of autoimmune\ndisease is in women", fontsize=9.5,
            color=WHITE, ha="center", va="top")
    routes = [("Antiphospholipid syndrome", RED),
              ("Libman–Sacks endocarditis", GOLD),
              ("Hypertension / coagulopathy", TEAL)]
    for i, (t, c) in enumerate(routes):
        y = py + 0.85 - i*0.6
        glow_dot(ax, px+0.05, y, c, r=0.05)
        ax.text(px+0.3, y, t, fontsize=10.3, color=c, ha="left", va="center")
    ax.text(px+1.55, py-1.15, "$\\to$  stroke", fontsize=12, color=RED, ha="center",
            weight="bold")


# ============================================================ SLIDE 1
def slide1(ax):
    title(ax, "Pregnancy turns the circulation pro-thrombotic",
          sub="Clotting is dialled up to limit blood loss — the same shift clots the brain",
          accent=BLUE)
    draw_circle_of_willis(ax, 14.3, 7.6, 0.5, color=RED)

    panel(ax, 4.35, 3.7, 6.6, 4.7, BLUE, "Hemostatic balance")
    mini_balance(ax, 4.35, 3.6)
    ax.text(4.35, 1.65, "hypercoagulability · volume shifts · venous stasis",
            fontsize=10.5, color=GREY, ha="center", style="italic")

    panel(ax, 11.65, 3.7, 6.6, 4.7, RED, "Stroke in pregnancy")
    mini_timeline(ax, 11.9, 3.9)
    ax.text(11.65, 1.65, "Highest risk: late 3rd trimester $\\to$ first 6 weeks postpartum",
            fontsize=10.5, color=GOLD, ha="center")


# ============================================================ SLIDE 2
def slide2(ax):
    title(ax, "Peripartum neurovascular syndromes", accent=GOLD)

    panel(ax, 4.35, 5.5, 6.9, 2.95, GOLD, "Pre-eclampsia / eclampsia")
    mini_cascade(ax, 4.45, 5.35)

    panel(ax, 11.65, 5.5, 6.9, 2.95, PURPLE, "PRES")
    mini_pres(ax, 10.6, 5.25)

    panel(ax, 4.35, 2.35, 6.9, 2.95, RED, "RCVS")
    mini_rcvs(ax, 4.5, 2.2)

    panel(ax, 11.65, 2.35, 6.9, 2.95, BLUE, "Cerebral venous thrombosis")
    mini_cvt(ax, 10.5, 2.25)


# ============================================================ SLIDE 3
def slide3(ax):
    title(ax, "Hormones & lifelong risk", accent=MAROON)

    panel(ax, 4.35, 5.5, 6.9, 2.95, MAROON, "Migraine with aura")
    mini_migraine(ax, 4.35, 5.25)

    panel(ax, 11.65, 5.5, 6.9, 2.95, GOLD, "Pregnancy = stress test")
    mini_stress(ax, 11.65, 5.35)

    panel(ax, 4.35, 2.35, 6.9, 2.95, BLUE, "Atrial fibrillation")
    mini_af(ax, 4.35, 2.2)

    panel(ax, 11.65, 2.35, 6.9, 2.95, PURPLE, "Lupus & antiphospholipid antibodies")
    mini_lupus(ax, 11.5, 2.2)

    glow_line(ax, [1.0, W-1.0], [0.92, 0.92], GREY_D, lw=0.9, glow=False, alpha=0.6)
    ax.text(W/2, 0.6,
            "O'Neal MA. A Review of Women's Neurology. Am J Med. 2018;131(7):735–744.  ·  "
            "doi.org/10.1016/j.amjmed.2017.11.053",
            fontsize=10, color=GREY, ha="center", va="center")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "Neurovascular_Disease_in_Women_Condensed.pdf")
    slides = [slide1, slide2, slide3]
    with PdfPages(out) as pdf:
        for i, fn in enumerate(slides, 1):
            fig, ax = new_slide()
            fn(ax)
            ax.text(W-0.5, 0.42, f"{i} / {len(slides)}", fontsize=10.5,
                    color=GREY_D, ha="right", va="center")
            pdf.savefig(fig, facecolor=BG)
            plt.close(fig)
    print("WROTE", out)


if __name__ == "__main__":
    main()
