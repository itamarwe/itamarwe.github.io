"""
Two-slide condensed summary of "Neurovascular Disease in Women",
in the same 3Blue1Brown / manim style as the full deck.
"""
import os
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
from manimlike import (
    new_slide, glow_line, glow_dot, arrow, rbox, title, bullet,
    draw_brain, draw_circle_of_willis,
    W, H, BG, WHITE, GREY, GREY_D, BLUE_B, BLUE, BLUE_D, BLUE_E, TEAL,
    GREEN, YELLOW, GOLD, RED, MAROON, PURPLE, PINK,
)


def mini_card(ax, cx, cy, w, h, col, head, lines):
    rbox(ax, cx, cy, w, h, col, fill=0.08)
    ax.text(cx - w/2 + 0.35, cy + h/2 - 0.45, head, fontsize=14.5, color=col,
            ha="left", va="center", weight="bold")
    ty = cy + h/2 - 0.97
    for ln, lc in lines:
        ax.text(cx - w/2 + 0.35, ty, ln, fontsize=11.8, color=lc, ha="left",
                va="center")
        ty -= 0.46


# ============================================================ SLIDE 1
def slide1(ax):
    title(ax, "The peripartum brain", sub="Pregnancy turns the cerebral circulation pro-thrombotic",
          accent=BLUE)

    # left motif
    draw_circle_of_willis(ax, 2.55, 4.55, 0.74, color=RED)
    draw_brain(ax, 2.55, 4.55, 0.62, color=BLUE_B, sulci=False, lw=1.2)
    ax.text(2.55, 2.45,
            "Clotting is dialled up to limit\nblood loss at delivery — the\n"
            "same shift clots the brain.",
            fontsize=11.5, color=GREY, ha="center", va="top", style="italic",
            linespacing=1.35)
    ax.text(2.55, 0.95, "Highest risk: late 3rd trimester\n$\\to$ first 6 weeks postpartum",
            fontsize=11, color=GOLD, ha="center", va="top", linespacing=1.3)

    cards = [
        (BLUE, "Stroke in pregnancy",
         [("16–41 / 100,000 pregnancies", WHITE),
          ("Hypercoagulability + venous", WHITE),
          ("stasis; peaks late & postpartum", WHITE)]),
        (GOLD, "Pre-eclampsia / eclampsia",
         [("Hypertension + end-organ injury", WHITE),
          ("Endothelial injury $\\to$ seizures,", WHITE),
          ("stroke, hemorrhage  ·  PRES", WHITE)]),
        (RED, "RCVS",
         [("Thunderclap headache", WHITE),
          ("Segmental 'string-of-beads'", WHITE),
          ("narrowing; resolves in weeks", WHITE)]),
        (TEAL, "Cerebral venous thrombosis",
         [("Sinuses clot in the", WHITE),
          ("peripartum window", WHITE),
          ("Treat: anticoagulation (LMWH)", WHITE)]),
    ]
    xs = [7.0, 12.6, 7.0, 12.6]
    ys = [5.0, 5.0, 2.2, 2.2]
    for (col, head, lines), x, y in zip(cards, xs, ys):
        mini_card(ax, x, y, 5.2, 2.3, col, head, lines)


# ============================================================ SLIDE 2
def slide2(ax):
    title(ax, "Hormones & lifelong risk", sub="Estrogen tunes the vessels; pregnancy forecasts the future",
          accent=PURPLE)

    cards = [
        (MAROON, "Migraine with aura",
         [("Aura = independent stroke risk", WHITE),
          ("Magnified by estrogen-containing", WHITE),
          ("contraception", WHITE),
          ("Absolute contraindication to CHC", RED)]),
        (GOLD, "Pregnancy = stress test",
         [("Gestational diabetes $\\to$ ~50% in 5 yr", WHITE),
          ("Gestational HTN $\\to$ 2–4$\\times$ later HTN", WHITE),
          ("Pre-eclampsia $\\to$ $\\geq$2$\\times$ stroke later", WHITE),
          ("A decades-long window to act", TEAL)]),
        (BLUE, "Atrial fibrillation",
         [("Higher stroke risk than men", WHITE),
          ("6.2% vs 4.2% per year (NVAF)", WHITE),
          ("Female sex adds a risk point", WHITE),
          ("Worse deficits & outcomes", WHITE)]),
        (PURPLE, "Lupus & APS",
         [("78% of autoimmune disease", WHITE),
          ("is in women; lupus 7$\\times$ more", WHITE),
          ("Antiphospholipid syndrome &", WHITE),
          ("Libman–Sacks $\\to$ stroke", RED)]),
    ]
    xs = [4.6, 11.4, 4.6, 11.4]
    ys = [5.35, 5.35, 2.4, 2.4]
    for (col, head, lines), x, y in zip(cards, xs, ys):
        mini_card(ax, x, y, 6.4, 2.7, col, head, lines)

    # reference footer band
    glow_line(ax, [1.0, W-1.0], [1.0, 1.0], GREY_D, lw=1.0, glow=False, alpha=0.6)
    ax.text(W/2, 0.62,
            "O'Neal MA. A Review of Women's Neurology. Am J Med. 2018;131(7):735–744.  ·  "
            "doi.org/10.1016/j.amjmed.2017.11.053",
            fontsize=10.5, color=GREY, ha="center", va="center")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "Neurovascular_Disease_in_Women_Summary.pdf")
    with PdfPages(out) as pdf:
        for i, fn in enumerate([slide1, slide2], 1):
            fig, ax = new_slide()
            fn(ax)
            ax.text(W-0.5, 0.42, f"{i} / 2", fontsize=10.5, color=GREY_D,
                    ha="right", va="center")
            ax.text(0.5, 0.42, "NEUROVASCULAR DISEASE IN WOMEN — SUMMARY",
                    fontsize=9.5, color=GREY_D, ha="left", va="center")
            pdf.savefig(fig, facecolor=BG)
            plt.close(fig)
    print("WROTE", out)


if __name__ == "__main__":
    main()
