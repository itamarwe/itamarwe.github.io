# VGGT-Ω post — figures, animation & interactive

Code behind the visuals in `content/posts/2026-07-09-vggt-omega.md`.
Outputs are committed under `public/img/vggt-omega/` and
`public/vggt-omega-viz/`.

## Layout

- `sim/figures.py` — all static PNGs (social card + 11 figures), matplotlib,
  pure-black `#000` background, house palette. All figures are qualitative
  schematics **except** `scaling.png`, which plots the point-error values
  published in the VGGT-Ω paper (Fig. 1); the data-curve x-positions are
  interpolated on the log axis between the reported 2K → 2M endpoints (noted
  in the figure caption and the post).
- `sim/optimize_vs_predict.py` — the split-screen MP4 (bundle adjustment
  jitter-converging vs one-pass snap). A stylized re-enactment, not real
  solver output — stated in its docstring and in the post.
- `sim/check_math.js` — brute-force verification of the interaction-count
  formulas shown in the Three.js interactive
  (`public/vggt-omega-viz/register-attention.html`).

## Reproduce

```bash
python3 -m venv venv && venv/bin/pip install numpy matplotlib
venv/bin/python sim/figures.py            # PNGs -> public/img/vggt-omega/
venv/bin/python sim/optimize_vs_predict.py  # needs ffmpeg on PATH
node sim/check_math.js                    # all lines should print OK
```
