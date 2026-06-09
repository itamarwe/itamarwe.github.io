# Neurovascular Disease in Women

A 14-slide presentation summarising neurovascular (cerebrovascular) disease in
women, styled after 3Blue1Brown / manim — deep near-black background, the manim
colour palette, glowing strokes, LaTeX-style serif type, and original schematic
vascular diagrams (Circle of Willis, the hemostatic balance, the pre-eclampsia
cascade, PRES, RCVS "string of beads", cerebral venous sinuses, and more).

The deck is rendered as a vector PDF rather than a video, so it is produced with
matplotlib (which gives multi-page vector output) using the manim look-and-feel
rather than the manim engine itself.

## Topics

Hormonal control of the cerebral circulation · the pro-thrombotic shift of
pregnancy · stroke in pregnancy · pre-eclampsia / eclampsia · PRES · reversible
cerebral vasoconstriction syndrome · cerebral venous thrombosis · migraine with
aura & combined hormonal contraception · pregnancy as a cardiovascular stress
test · atrial fibrillation · lupus & antiphospholipid antibodies.

## Build

```bash
pip install matplotlib numpy
python deck.py        # writes Neurovascular_Disease_in_Women.pdf next to the script
```

- `manimlike.py` — shared 3b1b/manim-style palette and drawing helpers.
- `deck.py` — the full 14-slide deck.
- `summary.py` — a 2-slide text-card summary.
- `condensed.py` — a 3-slide condensed version that keeps the deck's
  visualisations (balance, risk timeline, pre-eclampsia cascade, PRES brain,
  RCVS beading, CVT sinus, migraine multiplier, AF bars, lupus routes) in
  grouped panels.
- `narrative.py` — a 9-slide narrative pitch deck using the same data to make
  the case for founding a Center for Women's Neurovascular Disease: how women's
  cerebrovascular disease differs from men's (biology, risk factors, diagnosis),
  what's overlooked, and where the opportunity is.
- `*.pdf` — the rendered decks.

Each script writes its PDF next to itself:

```bash
python deck.py        # 14-slide clinical deck
python summary.py     # 2-slide summary
python condensed.py   # 3-slide condensed deck
python narrative.py   # 9-slide founding-a-center narrative
```

## Source

O'Neal MA. *A Review of Women's Neurology.* The American Journal of Medicine.
2018;131(7):735–744. https://doi.org/10.1016/j.amjmed.2017.11.053
