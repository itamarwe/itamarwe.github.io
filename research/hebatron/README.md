# Hebatron — figures, animation & interactive

Assets for the blog post *Training a Hebrew LLM: Behind the Scenes of Hebatron*
(`content/posts/2026-06-16-training-a-hebrew-llm.md`), which is a write-up of the
[ExplAInable](https://open.spotify.com/episode/4usi3lrCnaKAD5yDYyOlPt) episode on how
the PwC NEXT / National AI Program team trained Hebatron (a continued-pretrain + SFT
of NVIDIA's Nemotron).

## Layout

- `sim/figures.py` — the seven static figures plus the 1200×630 social card. Pure
  matplotlib, dark 3b1b-style palette. Includes the MoE routing schematic
  (`moe_schematic.png`) and the batch-size / steps chart (`batch_size.png`).
- `sim/train_anim.py` — the `training_arc.mp4` animation (loss falls while benchmarks
  stay flat, then break free after the batch-size change).
- The committed PNGs/MP4 live in `public/img/hebatron/`.

## Regenerating

```bash
python3 -m venv research/.venv
research/.venv/bin/pip install numpy scipy matplotlib imageio-ffmpeg
research/.venv/bin/python research/hebatron/sim/figures.py
research/.venv/bin/python research/hebatron/sim/train_anim.py
```

Output paths are derived from `__file__`, so they land in `public/img/hebatron/`
regardless of where you run from.

## Honesty note

Charts use real numbers from the episode: tokenizer compression ratios, the 250B-token
budget and the 2M→10.5M global batch sizes (so `batch_size.png` is exact: steps =
250B / batch), the 20k–100k efficient window and the LR-vs-batch √ rule, and the
throughput/cost figures. `moe_schematic.png` is a **schematic** (lit vs. idle experts,
no quantities implied), and `training_arc.mp4` is a **qualitative schematic** of the
loss-vs-benchmark pattern with no numeric axes. Hebrew words in `tokenization.png` are
written in transliteration because matplotlib doesn't shape right-to-left text
correctly.
