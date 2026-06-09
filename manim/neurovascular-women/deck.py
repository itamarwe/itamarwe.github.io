"""
Neurovascular Disease in Women — a 3Blue1Brown / manim-style slide deck,
rendered to a vector PDF.
"""
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, Wedge, Rectangle, FancyBboxPatch
from manimlike import (
    new_slide, glow_line, glow_dot, arrow, rbox, title, page_tag, bullet,
    draw_brain, draw_circle_of_willis, lightning,
    W, H, BG, WHITE, GREY, GREY_D, BLUE_B, BLUE, BLUE_D, BLUE_E, TEAL,
    GREEN, YELLOW, GOLD, RED, MAROON, PURPLE, PINK,
)

SLIDES = []
def slide(fn): SLIDES.append(fn); return fn

TOTAL = 15  # number of content/title slides (set after counting)


# ============================================================ 01 TITLE
@slide
def s_title(ax, n):
    # faint vessel field
    rng = np.random.default_rng(7)
    for _ in range(26):
        x0 = rng.uniform(0, W); y0 = rng.uniform(0, H)
        ang = rng.uniform(0, 2*np.pi); L = rng.uniform(0.6, 1.8)
        glow_line(ax, [x0, x0+L*np.cos(ang)], [y0, y0+L*np.sin(ang)],
                  BLUE_E, lw=1.0, glow=False, alpha=0.18)
    draw_circle_of_willis(ax, 12.6, 4.7, 1.15, color=RED)
    draw_brain(ax, 12.6, 4.7, 1.0, color=BLUE_B, sulci=False, lw=1.4)

    ax.text(1.1, 6.0, "Neurovascular Disease", fontsize=46, weight="bold",
            color=WHITE, ha="left", va="center")
    ax.text(1.1, 4.9, "in Women", fontsize=46, weight="bold",
            color=BLUE, ha="left", va="center")
    glow_line(ax, [1.15, 7.4], [4.1, 4.1], TEAL, lw=2.6)
    ax.text(1.15, 3.45,
            "How sex, hormones and pregnancy reshape the cerebral circulation",
            fontsize=16, color=GREY, ha="left", va="center", style="italic")
    ax.text(1.15, 1.7, "A visual summary", fontsize=13, color=GREY_D, ha="left")


# ============================================================ 02 WHY GENDER
@slide
def s_why(ax, n):
    title(ax, "A circulation under hormonal control", accent=TEAL)
    ax.text(1.0, 6.55,
            "The vessels of the brain do not behave the same way in every body.",
            fontsize=16, color=WHITE, ha="left")
    ax.text(1.0, 6.0,
            "Sex hormones, the clotting shifts of pregnancy and sex-specific risk",
            fontsize=16, color=WHITE, ha="left")
    ax.text(1.0, 5.45,
            "factors all tilt the balance between flow, clotting and bleeding.",
            fontsize=16, color=WHITE, ha="left")

    cards = [
        ("Pregnancy &\npostpartum", BLUE, "A pro-thrombotic\nwindow"),
        ("Hormones &\ncontraception", PURPLE, "Estrogen tunes\nvascular risk"),
        ("Lifelong\nrisk", GOLD, "Pregnancy as a\ncardiovascular\nstress test"),
    ]
    xs = [3.2, 8.0, 12.8]
    for (head, col, body), x in zip(cards, xs):
        rbox(ax, x, 2.9, 3.7, 3.0, col)
        ax.text(x, 3.85, head, fontsize=17, color=col, ha="center", va="center",
                weight="bold")
        ax.text(x, 2.35, body, fontsize=13.5, color=WHITE, ha="center", va="center")


# ============================================================ 03 HEMOSTATIC BALANCE
@slide
def s_balance(ax, n):
    title(ax, "Pregnancy tilts hemostasis toward clotting", accent=BLUE)
    ax.text(1.0, 6.6,
            "Clotting is dialled up to limit blood loss at delivery — an adaptive shift.",
            fontsize=15.5, color=WHITE, ha="left")
    ax.text(1.0, 6.1,
            "The same shift makes the cerebral vessels prone to thrombosis.",
            fontsize=15.5, color=GREY, ha="left", style="italic")

    # see-saw scale tilting toward clotting
    px, py = 8.0, 3.4
    tilt = -13 * np.pi / 180
    L = 4.4
    dx, dy = (L/2)*np.cos(tilt), (L/2)*np.sin(tilt)
    # fulcrum
    glow_line(ax, [px-0.6, px, px+0.6], [py-1.4, py, py-1.4], GREY, lw=2.0, glow=False)
    glow_line(ax, [px-dx, px+dx], [py-dy, py+dy], WHITE, lw=3.0)
    # left pan = bleeding (up), right pan = clotting (down)
    for sgn, col, lab, val in [(-1, BLUE_B, "Bleeding", 0.55), (1, RED, "Clotting", 1.0)]:
        ex, ey = px + sgn*dx, py + sgn*dy
        glow_dot(ax, ex, ey, col, r=0.06)
        ax.add_patch(Wedge((ex, ey-0.95), 0.85, 200, 340, width=0.12,
                           color=col, alpha=0.9))
        glow_line(ax, [ex, ex], [ey, ey-0.95], col, lw=1.4, glow=False)
        ax.text(ex, ey-1.5, lab, fontsize=14, color=col, ha="center", weight="bold")
    arrow(ax, (px+1.0, py+1.9), (px+1.9, py+0.9), RED, lw=2.4)
    ax.text(px+1.5, py+2.2, "pregnancy", fontsize=12.5, color=RED, ha="center")

    for i, txt in enumerate([
        "Hypercoagulable state",
        "Volume shifts & dehydration",
        "Venous stasis"]):
        bullet(ax, 12.7, 5.2 - i*0.7, txt, color=RED, fs=14)
    ax.text(12.7, 2.7, "Highest risk: 3rd trimester\n$\\to$ first 6 weeks postpartum",
            fontsize=13.5, color=GOLD, ha="left", va="top")


# ============================================================ 04 STROKE IN PREGNANCY
@slide
def s_stroke_preg(ax, n):
    title(ax, "Stroke in pregnancy: rare, but it can be devastating", accent=RED)
    # big number
    ax.text(3.6, 5.4, "16–41", fontsize=58, color=RED, ha="center", weight="bold")
    ax.text(3.6, 4.3, "ischemic strokes", fontsize=15, color=WHITE, ha="center")
    ax.text(3.6, 3.8, "per 100,000 pregnancies", fontsize=13.5, color=GREY, ha="center")

    # risk timeline
    x0, x1, y = 6.6, 14.8, 4.6
    glow_line(ax, [x0, x1], [y, y], GREY, lw=1.6, glow=False)
    marks = [("Conception", 0.0, BLUE_E), ("T1", 0.16, BLUE_E),
             ("T2", 0.36, BLUE_E), ("T3", 0.56, GOLD),
             ("Delivery", 0.68, RED), ("6 wk pp", 0.86, RED), ("", 1.0, GREY_D)]
    # risk curve rising into late pregnancy / postpartum
    xs = np.linspace(x0, x1, 200)
    f = (xs - x0)/(x1 - x0)
    risk = 0.25 + 0.2*f + 1.0*np.exp(-((f-0.78)**2)/0.012)
    glow_line(ax, xs, y + risk, RED, lw=2.4)
    ax.text((x0+x1)/2, y+1.95, "relative stroke risk", fontsize=12, color=RED, ha="center")
    for lab, fpos, col in marks:
        xx = x0 + fpos*(x1-x0)
        glow_dot(ax, xx, y, col, r=0.05)
        if lab:
            ax.text(xx, y-0.45, lab, fontsize=11.5, color=col, ha="center", rotation=0)

    ax.text((x0+x1)/2, 2.2,
            "The hypercoagulable state peaks late — the late third trimester and the\n"
            "early postpartum weeks carry the greatest cerebrovascular risk.",
            fontsize=13.5, color=WHITE, ha="center")


# ============================================================ 05 PREECLAMPSIA cascade
@slide
def s_preeclampsia(ax, n):
    title(ax, "Pre-eclampsia / eclampsia: a vascular disease", accent=GOLD)
    ax.text(1.0, 6.7, "New-onset hypertension + end-organ injury after 20 weeks.",
            fontsize=15, color=WHITE, ha="left")
    ax.text(1.0, 6.25, "Eclampsia = pre-eclampsia with new seizures.",
            fontsize=14, color=GREY, ha="left", style="italic")

    steps = [
        ("Incomplete\ntrophoblast\nimplantation", PURPLE),
        ("Placental\nischemia", MAROON),
        ("Hypertension", GOLD),
        ("Endothelial\ninjury", RED),
    ]
    xs = [2.6, 5.7, 8.6, 11.4]
    for (txt, col), x in zip(steps, xs):
        rbox(ax, x, 4.7, 2.5, 1.6, col)
        ax.text(x, 4.7, txt, fontsize=13, color=WHITE, ha="center", va="center")
    for a, b in zip(xs[:-1], xs[1:]):
        arrow(ax, (a+1.35, 4.7), (b-1.35, 4.7), WHITE, lw=2.0)

    # end-organ fan-out
    organs = [("Kidney", "proteinuria", BLUE), ("Liver", "coagulopathy", TEAL),
              ("Brain", "seizures · stroke\nvisual loss", RED)]
    ox = [11.4, 13.0, 14.6]
    bx = [10.0, 11.9, 13.8]
    for (org, eff, col), x in zip(organs, bx):
        arrow(ax, (11.4, 3.9), (x, 3.0), col, lw=1.8)
        ax.text(x, 2.7, org, fontsize=13.5, color=col, ha="center", weight="bold")
        ax.text(x, 2.15, eff, fontsize=11.5, color=WHITE, ha="center", va="top")

    # incidence rise inset
    ax.text(2.0, 2.8, "US incidence", fontsize=12.5, color=GREY, ha="left")
    gx0, gx1, gy0 = 1.6, 5.2, 0.95
    glow_line(ax, [gx0, gx0], [gy0, gy0+1.6], GREY_D, lw=1.0, glow=False)
    glow_line(ax, [gx0, gx1], [gy0, gy0], GREY_D, lw=1.0, glow=False)
    glow_line(ax, [gx0+0.3, gx1-0.3], [gy0+0.12, gy0+1.35], GOLD, lw=2.4)
    glow_dot(ax, gx0+0.3, gy0+0.12, GOLD, r=0.06)
    glow_dot(ax, gx1-0.3, gy0+1.35, GOLD, r=0.06)
    ax.text(gx0+0.3, gy0+0.38, "0.3%", fontsize=11, color=GOLD, ha="left")
    ax.text(gx0+0.3, gy0-0.18, "1980", fontsize=10, color=GREY, ha="center")
    ax.text(gx1-0.3, gy0+1.15, "1.4%", fontsize=11, color=GOLD, ha="right")
    ax.text(gx1-0.3, gy0-0.18, "2010", fontsize=10, color=GREY, ha="center")


# ============================================================ 06 PRES
@slide
def s_pres(ax, n):
    title(ax, "PRES: the posterior brain loses its grip", accent=PURPLE)
    ax.text(1.0, 6.7,
            "The posterior circulation autoregulates poorly against surging pressure.",
            fontsize=15, color=WHITE, ha="left")
    ax.text(1.0, 6.2,
            "Fluid leaks into posterior white matter — posterior reversible",
            fontsize=15, color=WHITE, ha="left")
    ax.text(1.0, 5.7,
            "encephalopathy syndrome.",
            fontsize=15, color=WHITE, ha="left")

    # brain (top-down) with posterior region highlighted
    cx, cy, s = 4.6, 3.0, 1.5
    draw_brain(ax, cx, cy, s, color=BLUE_B, sulci=True, lw=2.0)
    # highlight posterior (left side of this side-view = occipital)
    th = np.linspace(2.2, 4.1, 60)
    xx = cx + s*1.35*0.95*np.cos(th)
    yy = cy + s*1.0*0.95*np.sin(th)
    for r in [0.5, 0.35, 0.2]:
        ax.scatter(cx + s*1.0*np.cos(th)*0.9 - 0.4, cy + s*0.7*np.sin(th),
                   s=2, color=PURPLE, alpha=0.0)
    # glowing posterior patch
    ax.add_patch(Circle((cx - s*0.95, cy + 0.0), s*0.55, color=PURPLE, alpha=0.16))
    ax.add_patch(Circle((cx - s*0.85, cy + 0.0), s*0.32, color=PURPLE, alpha=0.22))
    ax.text(cx - s*0.95, cy - s*0.95, "posterior\nwhite-matter edema",
            fontsize=11.5, color=PURPLE, ha="center", va="top")

    for i, txt in enumerate([
        ("Headache", BLUE_B),
        ("Visual changes", PURPLE),
        ("Seizures", RED),
        ("Confusion", GOLD)]):
        bullet(ax, 9.2, 4.6 - i*0.78, txt[0], color=txt[1], fs=16)
    ax.text(9.2, 1.3, "Usually reversible with prompt\nblood-pressure control.",
            fontsize=13, color=GREEN, ha="left", va="top")


# ============================================================ 07 RCVS
@slide
def s_rcvs(ax, n):
    title(ax, "RCVS: arteries clamp down in a thunderclap", accent=RED)
    ax.text(1.0, 6.7,
            "A sudden, maximal-at-onset headache with segmental arterial narrowing.",
            fontsize=15, color=WHITE, ha="left")
    ax.text(1.0, 6.2,
            "Monophasic — it constricts, then resolves over weeks.",
            fontsize=15, color=GREY, ha="left", style="italic")

    # beaded vessel ("string of beads")
    x0, x1, y = 2.0, 11.5, 4.3
    xs = np.linspace(x0, x1, 400)
    f = (xs-x0)/(x1-x0)
    width = 0.18*(1 + 0.75*np.cos(2*np.pi*5*f))  # beading
    glow_line(ax, xs, y+width, RED, lw=1.6, glow=False)
    glow_line(ax, xs, y-width, RED, lw=1.6, glow=False)
    glow_line(ax, xs, np.full_like(xs, y), RED, lw=1.0, glow=True, alpha=0.25)
    ax.fill_between(xs, y-width, y+width, color=RED, alpha=0.12)
    # arrows at constrictions
    for fc in [0.2, 0.4, 0.6, 0.8]:
        xc = x0 + fc*(x1-x0)
        arrow(ax, (xc, y+0.95), (xc, y+0.32), YELLOW, lw=1.6, mut=11)
    ax.text((x0+x1)/2, y+1.45, "segmental narrowing  ('string of beads')",
            fontsize=12.5, color=YELLOW, ha="center")

    lightning(ax, 13.5, 4.4, 0.85, color=YELLOW)
    ax.text(13.5, 2.9, "thunderclap\nheadache", fontsize=13, color=YELLOW,
            ha="center", va="top")

    ax.text(1.0, 2.3, "Triggers:", fontsize=13.5, color=GREY, ha="left", weight="bold")
    ax.text(1.0, 1.75,
            "vasoactive drugs · SSRIs/SNRIs · sympathomimetics · triptans · ergots · cannabis · cocaine",
            fontsize=12.5, color=WHITE, ha="left")
    ax.text(1.0, 1.2, "Strong overlap with pre-eclampsia / eclampsia.",
            fontsize=12.5, color=GOLD, ha="left", style="italic")


# ============================================================ 08 CVT
@slide
def s_cvt(ax, n):
    title(ax, "Cerebral venous thrombosis: the drainage clots", accent=BLUE)
    ax.text(1.0, 6.7,
            "Pregnancy's hypercoagulability can clot the brain's venous sinuses.",
            fontsize=15, color=WHITE, ha="left")

    # brain with superior sagittal sinus along the top + clot
    cx, cy, s = 4.4, 3.4, 1.5
    draw_brain(ax, cx, cy, s, color=BLUE_B, sulci=True, lw=1.8)
    # sinus = curve hugging the top
    th = np.linspace(0.15, np.pi-0.15, 80)
    sx = cx + s*1.35*1.02*np.cos(th)
    sy = cy + s*1.0*1.02*np.sin(th)
    glow_line(ax, sx, sy, BLUE, lw=3.0)
    ax.text(cx, cy + s*1.55, "superior sagittal sinus", fontsize=11.5,
            color=BLUE, ha="center")
    # clot
    clot_x, clot_y = cx + s*0.2, cy + s*1.0*1.02
    glow_dot(ax, clot_x, clot_y, RED, r=0.16)
    ax.text(clot_x+0.2, clot_y+0.45, "thrombus", fontsize=12, color=RED, ha="left")

    # timeline
    bullet(ax, 9.0, 5.0, "Peak window: late pregnancy", color=GOLD, fs=15)
    bullet(ax, 9.0, 4.3, "through the first 6 weeks postpartum", color=GOLD, fs=15, dot=False, dx=0.42)
    bullet(ax, 9.0, 3.4, "Headache · seizures · venous strokes", color=RED, fs=15)
    bullet(ax, 9.0, 2.6, "Confirm with MR / CT venography", color=BLUE_B, fs=15)
    bullet(ax, 9.0, 1.8, "Treat with anticoagulation (LMWH in pregnancy)",
           color=GREEN, fs=15)


# ============================================================ 09 MIGRAINE + AURA
@slide
def s_migraine(ax, n):
    title(ax, "Migraine with aura + estrogen = stroke risk", accent=MAROON)
    ax.text(1.0, 6.75,
            "Migraine is three times more common in women, and aura carries its own",
            fontsize=14.5, color=WHITE, ha="left")
    ax.text(1.0, 6.32,
            "small, independent risk of ischemic stroke.",
            fontsize=14.5, color=WHITE, ha="left")

    # contraindication callout
    rbox(ax, W/2, 5.35, 12.6, 0.85, RED, fill=0.12)
    ax.text(W/2, 5.35,
            "Migraine with aura  =  absolute contraindication to combined hormonal contraception",
            fontsize=14.5, color=RED, ha="center", va="center", weight="bold")

    # multiplier chain of growing bars
    items = [("baseline", 1.0, GREY), ("migraine\nwith aura", 1.9, GOLD),
             ("+ estrogen\ncontraception", 3.4, RED)]
    bx = [3.2, 7.2, 11.6]
    base_y = 1.55
    for (lab, h, col), x in zip(items, bx):
        H_ = 0.62 * h
        rbox(ax, x, base_y + H_/2, 1.55, H_, col, fill=0.16)
        ax.text(x, base_y - 0.45, lab, fontsize=13, color=col, ha="center", va="top")
        glow_dot(ax, x, base_y + H_, col, r=0.06)
    for a, b in zip(bx[:-1], bx[1:]):
        ax.text((a+b)/2, base_y + 0.45, "$\\times$", fontsize=24, color=WHITE,
                ha="center", va="center")

    ax.text(W/2, 4.15,
            "Combined hormonal contraception raises stroke risk with the estrogen",
            fontsize=13.5, color=GREY, ha="center")
    ax.text(W/2, 3.72,
            "dose — and that risk is multiplied by aura.",
            fontsize=13.5, color=GREY, ha="center")


# ============================================================ 10 STRESS TEST
@slide
def s_stress(ax, n):
    title(ax, "Pregnancy is a cardiovascular stress test", accent=GOLD)
    ax.text(1.0, 6.7,
            "Complications unmask the women whose vessels are already vulnerable —",
            fontsize=15, color=WHITE, ha="left")
    ax.text(1.0, 6.2,
            "a decades-long window to intervene before stroke ever happens.",
            fontsize=15, color=WHITE, ha="left")

    rows = [
        ("Gestational diabetes", "$\\approx$ 50% develop diabetes within 5 years", GOLD),
        ("Gestational hypertension", "2–4 $\\times$ risk of later hypertension", MAROON),
        ("Pre-eclampsia / eclampsia", "$\\geq$ 2 $\\times$ risk of stroke decades later", RED),
    ]
    for i, (a, b, col) in enumerate(rows):
        y = 4.9 - i*1.25
        rbox(ax, 4.3, y, 6.0, 1.0, col, fill=0.10)
        ax.text(4.3, y, a, fontsize=15.5, color=col, ha="center", va="center",
                weight="bold")
        arrow(ax, (7.5, y), (9.0, y), WHITE, lw=1.8)
        ax.text(9.3, y, b, fontsize=14.5, color=WHITE, ha="left", va="center")

    ax.text(W/2, 1.05,
            "A pregnancy history is part of every woman's stroke-risk assessment.",
            fontsize=14, color=TEAL, ha="center", style="italic")


# ============================================================ 11 AFIB
@slide
def s_afib(ax, n):
    title(ax, "Atrial fibrillation hits women harder", accent=BLUE)
    # ECG-like irregular trace
    x = np.linspace(2.0, 14.0, 1200)
    base = 6.4
    rng = np.random.default_rng(3)
    y = np.zeros_like(x) + base
    # irregular spikes
    spikes = np.sort(rng.uniform(2.2, 13.8, 16))
    for sp in spikes:
        y += 0.5*np.exp(-((x-sp)**2)/0.0008)
    y += 0.04*np.sin(40*x)
    glow_line(ax, x, y, TEAL, lw=1.8)

    # comparison bars
    by = 1.6
    for lab, val, col, bx in [("Women", 6.2, RED, 5.5), ("Men", 4.2, BLUE, 9.0)]:
        h = 0.42*val
        rbox(ax, bx, by + h/2, 1.7, h, col, fill=0.18)
        ax.text(bx, by + h + 0.35, f"{val:.1f}%", fontsize=20, color=col,
                ha="center", weight="bold")
        ax.text(bx, by - 0.45, lab, fontsize=15, color=WHITE, ha="center")
    ax.text(7.25, 5.0, "annual stroke incidence\nin nonvalvular AF",
            fontsize=13.5, color=GREY, ha="center")

    bullet(ax, 11.3, 4.4, "Female sex adds a point", color=GOLD, fs=14.5)
    bullet(ax, 11.3, 3.8, "to the stroke risk score", color=GOLD, fs=14.5, dot=False, dx=0.42)
    bullet(ax, 11.3, 2.9, "Worse deficits and", color=RED, fs=14.5)
    bullet(ax, 11.3, 2.3, "poorer quality of life", color=RED, fs=14.5, dot=False, dx=0.42)


# ============================================================ 12 LUPUS / APS
@slide
def s_lupus(ax, n):
    title(ax, "Lupus & antiphospholipid antibodies", accent=PURPLE)
    ax.text(1.0, 6.7,
            "Autoimmune disease is overwhelmingly a woman's disease — and lupus",
            fontsize=15, color=WHITE, ha="left")
    ax.text(1.0, 6.2,
            "reaches the brain through its blood vessels.",
            fontsize=15, color=WHITE, ha="left")

    ax.text(2.6, 5.0, "78%", fontsize=46, color=PURPLE, ha="center", weight="bold")
    ax.text(2.6, 4.0, "of autoimmune\ndisease is in women", fontsize=13,
            color=WHITE, ha="center", va="top")
    ax.text(2.6, 2.6, "Lupus: 7 $\\times$\nmore common\nin women", fontsize=13.5,
            color=MAROON, ha="center", va="top")

    routes = [
        ("Antiphospholipid\nsyndrome", "hypercoagulable state", RED),
        ("Libman–Sacks\nendocarditis", "cardioembolic stroke", GOLD),
        ("Hypertension &\ncoagulopathy", "small-vessel disease", TEAL),
    ]
    for i, (a, b, col) in enumerate(routes):
        y = 5.0 - i*1.45
        rbox(ax, 8.0, y, 4.0, 1.1, col, fill=0.10)
        ax.text(8.0, y, a, fontsize=13.5, color=col, ha="center", va="center",
                weight="bold")
        arrow(ax, (10.1, y), (11.4, y), WHITE, lw=1.8)
        ax.text(11.6, y, b, fontsize=13, color=WHITE, ha="left", va="center")
    ax.text(11.6, 0.95, "$\\to$  stroke", fontsize=15, color=RED, ha="left",
            weight="bold")


# ============================================================ 13 NMDAR (bonus neuro-immune-vascular? keep neuro)
# (skipped to stay strictly neurovascular)

# ============================================================ 13 TAKEAWAYS
@slide
def s_takeaways(ax, n):
    title(ax, "What to carry away", accent=TEAL)
    points = [
        ("Pregnancy is pro-thrombotic.",
         "The late third trimester and early postpartum carry the highest stroke risk.", BLUE),
        ("Pre-eclampsia is vascular.",
         "Endothelial injury drives PRES, seizures, hemorrhage and stroke.", GOLD),
        ("Think of the syndromes together.",
         "PRES, RCVS and CVT overlap in the peripartum brain.", PURPLE),
        ("Estrogen tunes risk.",
         "Migraine with aura contraindicates combined hormonal contraception.", MAROON),
        ("Pregnancy predicts the future.",
         "Its complications forecast stroke decades later — a window to act.", GREEN),
    ]
    for i, (head, body, col) in enumerate(points):
        y = 6.4 - i*1.15
        glow_dot(ax, 1.4, y, col, r=0.10)
        ax.text(1.9, y+0.18, head, fontsize=16.5, color=col, ha="left", va="center",
                weight="bold")
        ax.text(1.9, y-0.32, body, fontsize=13.5, color=WHITE, ha="left", va="center")


# ============================================================ 14 REFERENCES
@slide
def s_refs(ax, n):
    title(ax, "Reference", accent=GREY)
    ax.text(1.0, 6.4, "Primary source", fontsize=15, color=TEAL, ha="left",
            weight="bold")
    ax.text(1.0, 5.6,
            "O'Neal MA. A Review of Women's Neurology.",
            fontsize=16, color=WHITE, ha="left", style="italic")
    ax.text(1.0, 5.0,
            "The American Journal of Medicine. 2018;131(7):735–744.",
            fontsize=15, color=WHITE, ha="left")
    ax.text(1.0, 4.4,
            "https://doi.org/10.1016/j.amjmed.2017.11.053",
            fontsize=13.5, color=BLUE_B, ha="left")

    glow_line(ax, [1.0, 8.5], [3.7, 3.7], GREY_D, lw=1.0, glow=False)
    ax.text(1.0, 3.1,
            "Figures are original schematic illustrations created for this summary.",
            fontsize=12.5, color=GREY, ha="left", style="italic")

    # closing motif
    draw_circle_of_willis(ax, 13.0, 4.3, 0.9, color=RED)
    draw_brain(ax, 13.0, 4.3, 0.78, color=BLUE_B, sulci=False, lw=1.2)


# ============================================================ RENDER
def main():
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "Neurovascular_Disease_in_Women.pdf")
    total = len(SLIDES)
    with PdfPages(out) as pdf:
        for i, fn in enumerate(SLIDES, 1):
            fig, ax = new_slide()
            fn(ax, i)
            if i > 1:
                page_tag(ax, i, total)
            else:
                # title slide gets a slim footer only
                ax.text(W-0.5, 0.42, f"{i:02d} / {total:02d}", fontsize=10.5,
                        color=GREY_D, ha="right", va="center")
            pdf.savefig(fig, facecolor=BG)
            import matplotlib.pyplot as plt
            plt.close(fig)
    print("WROTE", out, "with", total, "slides")


if __name__ == "__main__":
    main()
