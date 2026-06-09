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
- `deck.py` — the slides themselves.
- `Neurovascular_Disease_in_Women.pdf` — the rendered deck.

## Source

O'Neal MA. *A Review of Women's Neurology.* The American Journal of Medicine.
2018;131(7):735–744. https://doi.org/10.1016/j.amjmed.2017.11.053
