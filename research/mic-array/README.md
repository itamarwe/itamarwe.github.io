# Mic-array study — simulation & figure source

The Python behind the post
[*Designing a Microphone Array to Detect FPV Drones*](../../content/posts/2026-06-09-designing-a-mic-array-for-acoustic-drone-detection.md).
Everything the post shows — geometry library, response-curve plots, baseline
histograms, the directionality figure, and the manim animations — is generated
from here.

## Layout

```
sim/
  arrays.py     Geometry generators (ULA, UCA, spiral, nested-aperiodic, dome,
                circular-aperiodic, …) + far-field delay-and-sum response,
                directivity, co-array / baseline-length helpers. Run directly
                for a quick table of dmin / alias-free freq / DI per geometry.
  figs.py       Response-curve figures: layouts, polar beam patterns, broadband
                curves, co-array scatter, the spacing/frequency tradeoff, and
                the recommendation backing chart.
  litfigs.py    Dark "3blue1brown"-style explainer figures: the algorithm
                pipeline, the topology-family gallery, the baseline-length
                histograms, and the steering / directionality figure.
scenes/
  anim.py       Manim scenes for the four embedded videos (Aliasing,
                BeamForming, CoArray, Recommended). No LaTeX — all labels are
                Text/Unicode.
```

`arrays.py` is the single source of truth for the geometry math; `figs.py`,
`litfigs.py`, and `anim.py` all import it.

## Running it

Use a virtualenv with `numpy scipy matplotlib manim` (manim only needed for the
videos). All figures are written to `out/figs/` (git-ignored).

```bash
cd sim
python arrays.py                 # sanity table, no files written
python figs.py                   # layouts / beam patterns / curves / co-array / tradeoff
RECO=1 python figs.py            # + recommendation backing chart
HIST=1 python litfigs.py         # baseline-length histograms
DIR=1  python litfigs.py         # endfire-vs-broadside directionality figure
python litfigs.py                # pipeline + topology-family gallery
```

Animations (rendered to `mp4`, then embedded in the post under
`public/img/mic-array/`):

```bash
cd scenes
manim -qh --format=mp4 anim.py Aliasing BeamForming CoArray Recommended
```

The figures committed under `public/img/mic-array/` are the outputs of these
scripts; re-running regenerates them byte-for-byte.
