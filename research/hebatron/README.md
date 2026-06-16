# Hebatron — figures, animation & interactive

Assets for the blog post *Training a Hebrew LLM: Behind the Scenes of Hebatron*
(`content/posts/2026-06-16-training-a-hebrew-llm.md`), which is a write-up of the
[ExplAInable](https://open.spotify.com/episode/4usi3lrCnaKAD5yDYyOlPt) episode on how
the PwC NEXT / National AI Program team trained Hebatron (a continued-pretrain + SFT
of NVIDIA's Nemotron).

## Layout

- `sim/figures.py` — the six static figures plus the 1200×630 social card. Pure
  matplotlib, dark 3b1b-style palette.
- `sim/train_anim.py` — the `training_arc.mp4` animation (loss falls while benchmarks
  stay flat, then break free after the batch-size change).
- The committed PNGs/MP4 live in `public/img/hebatron/`.
- The interactive batch-size explorer is a self-contained page at
  `public/hebatron/batch.html` (no build step, no dependencies).

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

Numbers taken from the episode: tokenizer compression ratios, throughput/cost
figures, the large-batch step targets, the LR-vs-batch √ rule. **Illustrative
reconstructions** (shapes that match what the speakers described, not Hebatron's
logged values): the MoE expert-routing entropy curves (`moe_entropy.png`) and the
loss-vs-benchmark training arc (`training_arc.mp4`). These are flagged in the figure
docstrings and in the post text. Hebrew words in `tokenization.png` are written in
transliteration because matplotlib doesn't shape right-to-left text correctly.
