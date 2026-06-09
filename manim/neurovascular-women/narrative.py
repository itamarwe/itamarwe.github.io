"""
A narrative pitch deck — the motivation for founding a Center for Women's
Neurovascular Disease — built from the same data, in the 3Blue1Brown / manim
style.
"""
import os
import numpy as np
import matplotlib
from matplotlib.patches import Wedge, Circle as MCircle
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
from manimlike import (
    new_slide, glow_line, glow_dot, arrow, rbox, title, lightning,
    draw_brain, draw_circle_of_willis,
    W, H, BG, WHITE, GREY, GREY_D, BLUE_B, BLUE, BLUE_D, BLUE_E, TEAL,
    GREEN, YELLOW, GOLD, RED, MAROON, PURPLE, PINK,
)

SECTION = "A CENTER FOR WOMEN'S NEUROVASCULAR DISEASE"


def footer(ax, n, total):
    ax.text(W - 0.5, 0.42, f"{n:02d} / {total:02d}", fontsize=10.5, color=GREY_D,
            ha="right", va="center")
    ax.text(0.5, 0.42, SECTION, fontsize=9.0, color=GREY_D, ha="left", va="center")
    glow_line(ax, [0.5, W - 0.5], [0.72, 0.72], GREY_D, lw=0.8, glow=False, alpha=0.5)


def kicker(ax, text, color):
    ax.text(1.0, 8.55, text.upper(), fontsize=12.5, color=color, ha="left",
            va="center", weight="bold")


def venus(ax, cx, cy, s, color):
    ax.add_patch(MCircle((cx, cy + 0.5*s), 0.5*s, fill=False, edgecolor=color, lw=2.2))
    for g, a in [(3.0, 0.10), (1.8, 0.16)]:
        ax.add_patch(MCircle((cx, cy + 0.5*s), 0.5*s, fill=False, edgecolor=color,
                             lw=2.2*g, alpha=a))
    glow_line(ax, [cx, cx], [cy, cy - 0.7*s], color, lw=2.2)
    glow_line(ax, [cx - 0.28*s, cx + 0.28*s], [cy - 0.4*s, cy - 0.4*s], color, lw=2.2)


def chip(ax, cx, cy, w, h, col, text, fs=9.8, fill=0.16, tcol=None, weight="normal"):
    rbox(ax, cx, cy, w, h, col, fill=fill, lw=1.3, round_pad=0.045)
    ax.text(cx, cy, text, fontsize=fs, color=tcol or WHITE, ha="center", va="center",
            weight=weight)


# ============================================================ 01 TITLE
def s01(ax):
    rng = np.random.default_rng(11)
    for _ in range(22):
        x0, y0 = rng.uniform(0, W), rng.uniform(0, H)
        ang, L = rng.uniform(0, 2*np.pi), rng.uniform(0.5, 1.6)
        glow_line(ax, [x0, x0+L*np.cos(ang)], [y0, y0+L*np.sin(ang)], BLUE_E,
                  lw=1.0, glow=False, alpha=0.16)
    draw_circle_of_willis(ax, 12.8, 4.8, 1.1, color=RED)
    draw_brain(ax, 12.8, 4.8, 0.95, color=BLUE_B, sulci=False, lw=1.3)
    venus(ax, 12.8, 2.0, 0.9, PINK)

    ax.text(1.1, 6.35, "The Center for", fontsize=30, color=GREY, ha="left", va="center")
    ax.text(1.1, 5.3, "Women's Neurovascular", fontsize=44, color=WHITE, ha="left",
            va="center", weight="bold")
    ax.text(1.1, 4.25, "Disease", fontsize=44, color=BLUE, ha="left", va="center",
            weight="bold")
    glow_line(ax, [1.15, 8.2], [3.5, 3.5], TEAL, lw=2.6)
    ax.text(1.15, 2.8, "Closing the sex gap in how we prevent, diagnose",
            fontsize=16, color=GREY, ha="left", va="center", style="italic")
    ax.text(1.15, 2.3, "and treat stroke across a woman's life.",
            fontsize=16, color=GREY, ha="left", va="center", style="italic")


# ============================================================ 02 HOOK
def s02(ax):
    kicker(ax, "The premise", RED)
    ax.text(1.0, 6.9, "Stroke is not sex-neutral.", fontsize=34, color=WHITE,
            ha="left", va="center", weight="bold")
    ax.text(1.0, 5.95,
            "Yet the way we predict it, recognise it and treat it was built around",
            fontsize=16, color=GREY, ha="left")
    ax.text(1.0, 5.5,
            "the average patient — and the average patient is a man.",
            fontsize=16, color=GREY, ha="left")

    facts = [
        ("3$\\times$", "migraine — a stroke risk\nmultiplier — in women", MAROON),
        ("7$\\times$", "lupus, a vascular brain\ndisease, in women", PURPLE),
        ("78%", "of autoimmune disease\nis in women", TEAL),
        ("$>$", "atrial fibrillation hits\nwomen harder than men", BLUE),
    ]
    xs = [2.7, 6.5, 10.3, 14.1]
    for (big, sub, col), x in zip(facts, xs):
        ax.text(x, 3.7, big, fontsize=40, color=col, ha="center", va="center",
                weight="bold")
        ax.text(x, 2.55, sub, fontsize=12.5, color=WHITE, ha="center", va="center")
    ax.text(W/2, 1.35,
            "A whole population whose cerebrovascular risk runs on a different set of rules.",
            fontsize=14.5, color=GOLD, ha="center", style="italic")


# ============================================================ 03 BIOLOGY
def s03(ax):
    kicker(ax, "Why women differ — 1 · the biology", BLUE)
    ax.text(1.0, 7.05, "The same vessels, a different operating system",
            fontsize=27, color=WHITE, ha="left", va="center", weight="bold")

    # balance
    px, py = 4.0, 4.0
    tilt = -13*np.pi/180; L = 3.0
    dx, dy = (L/2)*np.cos(tilt), (L/2)*np.sin(tilt)
    glow_line(ax, [px-0.45, px, px+0.45], [py-0.9, py, py-0.9], GREY, lw=1.6, glow=False)
    glow_line(ax, [px-dx, px+dx], [py-dy, py+dy], WHITE, lw=2.4)
    for sgn, col, lab in [(-1, BLUE_B, "Bleeding"), (1, RED, "Clotting")]:
        ex, ey = px+sgn*dx, py+sgn*dy
        glow_dot(ax, ex, ey, col, r=0.05)
        ax.add_patch(Wedge((ex, ey-0.58), 0.48, 200, 340, width=0.09, color=col, alpha=0.9))
        glow_line(ax, [ex, ex], [ey, ey-0.58], col, lw=1.1, glow=False)
        ax.text(ex, ey-1.28, lab, fontsize=11, color=col, ha="center", weight="bold")
    arrow(ax, (px+0.7, py+1.2), (px+1.3, py+0.6), RED, lw=2.0, mut=12)
    ax.text(px+1.0, py+1.45, "pregnancy", fontsize=10.5, color=RED, ha="center")
    ax.text(px, 1.5, "Pregnancy re-tunes hemostasis\ntoward clotting.",
            fontsize=12.5, color=GREY, ha="center", va="top", style="italic")

    glow_line(ax, [8.0, 8.0], [1.4, 6.2], GREY_D, lw=1.0, glow=False, alpha=0.5)

    pts = [
        ("Hormones set the dial", "Estrogen tunes vascular tone, clotting and\nmigraine — and shifts the stroke risk with it.", PURPLE),
        ("Pregnancy is a vascular event", "A months-long pro-thrombotic, high-pressure\nstate every man is spared.", GOLD),
        ("Autoimmunity targets vessels", "Female-predominant disease (lupus, APS)\nattacks the brain through its blood supply.", TEAL),
    ]
    for i, (h, b, col) in enumerate(pts):
        y = 5.7 - i*1.5
        glow_dot(ax, 8.7, y, col, r=0.09)
        ax.text(9.1, y+0.22, h, fontsize=15.5, color=col, ha="left", va="center",
                weight="bold")
        ax.text(9.1, y-0.42, b, fontsize=12.5, color=WHITE, ha="left", va="center")


# ============================================================ 04 RISK FACTORS
def stack(ax, cx, base_y, blocks, w=3.0, bh=0.44, gap=0.085):
    y = base_y
    tops = []
    for lab, col, fill in blocks:
        rbox(ax, cx, y + bh/2, w, bh, col, fill=fill, lw=1.2, round_pad=0.04)
        ax.text(cx, y + bh/2, lab, fontsize=9.6, color=WHITE, ha="center", va="center")
        y += bh + gap
        tops.append(y)
    return y


def s04(ax):
    kicker(ax, "Why women differ — 2 · the risk factors", GOLD)
    ax.text(1.0, 7.05, "Every risk factor men have — plus a layer of their own",
            fontsize=25, color=WHITE, ha="left", va="center", weight="bold")

    shared = [("Atrial fibrillation", BLUE_E, 0.10), ("Hypertension", BLUE_E, 0.10),
              ("Diabetes", BLUE_E, 0.10), ("Smoking", BLUE_E, 0.10), ("Age", BLUE_E, 0.10)]
    extra = [("Autoimmune disease / APS", PURPLE, 0.16),
             ("Migraine with aura", MAROON, 0.16),
             ("Hormonal contraception", PINK, 0.16),
             ("Pre-eclampsia / eclampsia", GOLD, 0.16),
             ("Pregnancy complications", RED, 0.16)]

    base = 1.3
    # Men
    top_m = stack(ax, 3.4, base, shared)
    ax.text(3.4, base-0.45, "MEN", fontsize=13, color=BLUE_B, ha="center", weight="bold")
    ax.text(3.4, top_m+0.3, "shared\nrisk factors", fontsize=10.5, color=GREY,
            ha="center", va="bottom")
    # Women
    top_w = stack(ax, 7.5, base, shared + extra)
    ax.text(7.5, base-0.45, "WOMEN", fontsize=13, color=PINK, ha="center", weight="bold")
    # divider between shared and sex-specific
    yline = base + 5*(0.44+0.085)
    glow_line(ax, [5.8, 9.2], [yline, yline], WHITE, lw=1.0, glow=False, alpha=0.4)
    ax.text(9.35, (yline+top_w)/2, "sex-specific\nlayer", fontsize=10.5, color=GOLD,
            ha="left", va="center")

    ax.text(12.3, 5.6, "Women carry the entire", fontsize=15, color=WHITE, ha="left")
    ax.text(12.3, 5.1, "male risk profile —", fontsize=15, color=WHITE, ha="left")
    ax.text(12.3, 4.6, "and then a second one", fontsize=15, color=GOLD, ha="left",
            weight="bold")
    ax.text(12.3, 4.1, "no man ever faces.", fontsize=15, color=GOLD, ha="left",
            weight="bold")
    ax.text(12.3, 3.1, "Even shared factors aren't\nequal: in atrial fibrillation,",
            fontsize=12.5, color=GREY, ha="left", va="top")
    ax.text(12.3, 2.15, "women's stroke risk is", fontsize=12.5, color=GREY, ha="left")
    ax.text(12.3, 1.7, "6.2%  vs  4.2%  in men.", fontsize=14, color=BLUE, ha="left",
            weight="bold")


# ============================================================ 05 PERIPARTUM (overlooked)
def s05(ax):
    kicker(ax, "What's overlooked — 1 · the peripartum brain", PURPLE)
    ax.text(1.0, 7.05, "A cluster of strokes hiding behind a headache",
            fontsize=26, color=WHITE, ha="left", va="center", weight="bold")

    # timeline pregnancy -> postpartum with risk hump + syndromes
    x0, x1, y = 1.6, 11.0, 4.6
    glow_line(ax, [x0, x1], [y, y], GREY, lw=1.5, glow=False)
    xs = np.linspace(x0, x1, 200)
    f = (xs-x0)/(x1-x0)
    risk = 0.2 + 0.16*f + 1.0*np.exp(-((f-0.8)**2)/0.013)
    glow_line(ax, xs, y+risk, RED, lw=2.2)
    for lab, fp in [("T1", 0.12), ("T2", 0.34), ("T3", 0.55), ("delivery", 0.7),
                    ("6 wk postpartum", 0.93)]:
        xx = x0+fp*(x1-x0)
        glow_dot(ax, xx, y, GREY_D, r=0.045)
        ax.text(xx, y-0.4, lab, fontsize=10, color=GREY, ha="center")
    # shaded danger window
    xw0, xw1 = x0+0.6*(x1-x0), x1
    ax.fill_between(np.linspace(xw0, xw1, 50), y, y+1.7, color=RED, alpha=0.06)
    ax.text((xw0+xw1)/2, y+1.95, "the danger window", fontsize=11.5, color=RED, ha="center")

    for lab, col, fp, loff in [("CVT", BLUE, 0.72, 1.05), ("RCVS", RED, 0.82, 1.62),
                               ("PRES", PURPLE, 0.93, 1.05)]:
        xx = x0+fp*(x1-x0)
        yc = y+np.interp(fp, f, risk)
        glow_dot(ax, xx, yc, col, r=0.06)
        ax.plot([xx, xx], [yc+0.08, y+loff-0.16], color=col, lw=0.8, alpha=0.5)
        ax.text(xx, y+loff, lab, fontsize=11, color=col, ha="center", weight="bold")

    chip(ax, 13.4, 5.6, 4.4, 1.0, YELLOW, "Thunderclap headache\nmisread as 'just a headache'",
         fs=11.5, tcol=YELLOW)
    chip(ax, 13.4, 4.3, 4.4, 1.0, PURPLE, "Postpartum seizures, visual\nloss, focal deficits — missed",
         fs=11.5, tcol=PURPLE)

    ax.text(W/2, 2.4,
            "PRES, RCVS and cerebral venous thrombosis overlap, peak in the same weeks,",
            fontsize=14, color=WHITE, ha="center")
    ax.text(W/2, 1.9,
            "and present through symptoms that are easy to dismiss — when minutes matter.",
            fontsize=14, color=WHITE, ha="center")


# ============================================================ 06 DIAGNOSTIC GAP
def s06(ax):
    kicker(ax, "What's overlooked — 2 · the unread history", TEAL)
    ax.text(1.0, 7.05, "Pregnancy is a stress test we forget to read",
            fontsize=26, color=WHITE, ha="left", va="center", weight="bold")

    rows = [("Gestational diabetes", "~50% develop diabetes within 5 years", GOLD),
            ("Gestational hypertension", "2–4$\\times$ the risk of later hypertension", MAROON),
            ("Pre-eclampsia / eclampsia", "$\\geq$2$\\times$ the risk of stroke decades later", RED)]
    for i, (a, b, col) in enumerate(rows):
        yy = 5.7 - i*1.15
        rbox(ax, 4.3, yy, 5.6, 0.92, col, fill=0.1, lw=1.4, round_pad=0.06)
        ax.text(4.3, yy, a, fontsize=14.5, color=col, ha="center", va="center",
                weight="bold")
        arrow(ax, (7.2, yy), (8.4, yy), WHITE, lw=1.7)
        ax.text(8.7, yy, b, fontsize=13.5, color=WHITE, ha="left", va="center")

    ax.text(W/2, 1.75,
            "These outcomes forecast cerebrovascular disease decades early — yet a",
            fontsize=14, color=GREY, ha="center")
    ax.text(W/2, 1.3,
            "reproductive history rarely makes it into a stroke-risk assessment.",
            fontsize=14, color=GOLD, ha="center", weight="bold")


# ============================================================ 07 OPPORTUNITY
def s07(ax):
    kicker(ax, "The opportunity", GREEN)
    ax.text(1.0, 7.05, "The earliest warning in medicine — currently ignored",
            fontsize=25, color=WHITE, ha="left", va="center", weight="bold")

    x0, x1, y = 1.8, 14.4, 4.2
    glow_line(ax, [x0, x1], [y, y], GREY, lw=1.6, glow=False)
    for age in [25, 30, 40, 50, 60, 70]:
        xx = x0 + (age-25)/45*(x1-x0)
        glow_dot(ax, xx, y, GREY_D, r=0.04)
        ax.text(xx, y-0.4, f"{age}", fontsize=10.5, color=GREY, ha="center")
    ax.text(x1+0.25, y, "age", fontsize=10.5, color=GREY, ha="left", va="center")

    # event flags
    xp = x0 + (32-25)/45*(x1-x0)
    glow_line(ax, [xp, xp], [y, y+1.6], GOLD, lw=2.0)
    glow_dot(ax, xp, y+1.6, GOLD, r=0.08)
    ax.text(xp, y+2.0, "Pregnancy signal", fontsize=13, color=GOLD, ha="center",
            weight="bold")
    ax.text(xp, y+1.05, "pre-eclampsia · GDM\ngestational HTN", fontsize=10.5,
            color=WHITE, ha="center", va="center")

    xs_ = x0 + (60-25)/45*(x1-x0)
    glow_line(ax, [xs_, xs_], [y, y+1.2], RED, lw=2.0)
    glow_dot(ax, xs_, y+1.2, RED, r=0.08)
    ax.text(xs_, y+1.55, "Stroke", fontsize=13, color=RED, ha="center", weight="bold")

    # window
    ax.fill_between(np.linspace(xp, xs_, 50), y-0.95, y-0.2, color=GREEN, alpha=0.10)
    arrow(ax, (xp+0.1, y-0.6), (xs_-0.1, y-0.6), GREEN, lw=1.8)
    ax.text((xp+xs_)/2, y-1.25, "a ~30-year window to intervene",
            fontsize=14, color=GREEN, ha="center", weight="bold")

    ax.text(W/2, 1.55,
            "Most prevention begins far too late. The female-specific signal arrives",
            fontsize=14, color=GREY, ha="center")
    ax.text(W/2, 1.1,
            "decades earlier — if someone is set up to act on it.",
            fontsize=14, color=WHITE, ha="center")


# ============================================================ 08 FRAGMENTATION -> HUB
def s08(ax):
    kicker(ax, "Why a dedicated center", RED)
    ax.text(1.0, 7.05, "No one owns the whole woman",
            fontsize=27, color=WHITE, ha="left", va="center", weight="bold")

    specialties = ["Obstetrics", "Neurology", "Cardiology", "Rheumatology", "Hematology"]
    # left: fragmented
    ax.text(4.0, 6.0, "Today: fragmented", fontsize=14, color=GREY, ha="center",
            style="italic")
    rng = np.random.default_rng(5)
    pos = [(2.3, 4.9), (5.6, 5.2), (2.0, 2.9), (5.9, 3.0), (3.9, 4.0)]
    for (lab), (px, py) in zip(specialties, pos):
        chip(ax, px, py, 2.2, 0.6, GREY, lab, fs=10.5, fill=0.05, tcol=GREY)
    ax.text(4.0, 1.6, "Each sees a slice.\nThe woman falls through the gaps.",
            fontsize=12, color=GREY, ha="center", va="top")

    arrow(ax, (7.0, 3.9), (8.8, 3.9), WHITE, lw=2.2, mut=18)

    # right: hub
    hx, hy = 12.2, 3.9
    for ang in np.linspace(0, 2*np.pi, len(specialties), endpoint=False):
        ex, ey = hx+2.5*np.cos(ang), hy+2.0*np.sin(ang)
        glow_line(ax, [hx, ex], [hy, ey], BLUE_E, lw=1.4, alpha=0.6)
    for (lab), ang in zip(specialties, np.linspace(0, 2*np.pi, len(specialties), endpoint=False)):
        ex, ey = hx+2.5*np.cos(ang), hy+2.0*np.sin(ang)
        chip(ax, ex, ey, 2.1, 0.56, BLUE, lab, fs=10, fill=0.12, tcol=BLUE_B)
    for g, a in [(3.0, 0.10), (1.8, 0.18)]:
        ax.add_patch(MCircle((hx, hy), 0.95*g*0.5, color=TEAL, alpha=a))
    ax.add_patch(MCircle((hx, hy), 0.95, color=BG, zorder=4))
    ax.add_patch(MCircle((hx, hy), 0.95, fill=False, edgecolor=TEAL, lw=2.2, zorder=5))
    ax.text(hx, hy, "One\ncenter", fontsize=12.5, color=TEAL, ha="center", va="center",
            weight="bold", zorder=6)
    ax.text(hx, 1.6, "One team, one record,\none woman — across her life.",
            fontsize=12, color=TEAL, ha="center", va="top")


# ============================================================ 09 VISION
def s09(ax):
    kicker(ax, "The vision", BLUE)
    ax.text(1.0, 7.05, "What the center will do",
            fontsize=28, color=WHITE, ha="left", va="center", weight="bold")

    pillars = [
        ("Peripartum\nstroke care", BLUE,
         "Rapid recognition and\ntreatment of PRES, RCVS\nand venous thrombosis."),
        ("Lifelong risk\nstratification", GOLD,
         "Turn every reproductive\nhistory into an early\nstroke-prevention plan."),
        ("Sex-specific\nresearch", PURPLE,
         "Study the mechanisms and\ntrials that the average-\npatient model ignored."),
        ("Education &\nadvocacy", TEAL,
         "Train clinicians to see the\nrisk — and the woman —\nthat others overlook."),
    ]
    xs = [2.3, 6.1, 9.9, 13.7]
    for (head, col, body), x in zip(pillars, xs):
        rbox(ax, x, 4.2, 3.35, 3.4, col, fill=0.08, lw=1.6)
        ax.text(x, 5.25, head, fontsize=15.5, color=col, ha="center", va="center",
                weight="bold")
        glow_line(ax, [x-1.0, x+1.0], [4.55, 4.55], col, lw=1.6, glow=False, alpha=0.6)
        ax.text(x, 3.6, body, fontsize=11.8, color=WHITE, ha="center", va="center")

    ax.text(W/2, 1.85, "Half the population. A different disease. A center built for it.",
            fontsize=16, color=WHITE, ha="center", weight="bold")
    glow_line(ax, [1.0, W-1.0], [1.25, 1.25], GREY_D, lw=0.8, glow=False, alpha=0.5)
    ax.text(W/2, 0.95,
            "Data: O'Neal MA. A Review of Women's Neurology. Am J Med. 2018;131(7):735–744.  ·  "
            "doi.org/10.1016/j.amjmed.2017.11.053",
            fontsize=9.5, color=GREY, ha="center", va="center")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "Women_Neurovascular_Center_Narrative.pdf")
    slides = [s01, s02, s03, s04, s05, s06, s07, s08, s09]
    with PdfPages(out) as pdf:
        for i, fn in enumerate(slides, 1):
            fig, ax = new_slide()
            fn(ax)
            footer(ax, i, len(slides))
            pdf.savefig(fig, facecolor=BG)
            plt.close(fig)
    print("WROTE", out, len(slides), "slides")


if __name__ == "__main__":
    main()
