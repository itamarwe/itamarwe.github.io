# Digital Dream — audio-reactive music video

A synthwave/retrowave video clip generated for the track **"Digital Dream" by
giladchat** (`AUDIO20251202110203.mp3`, 3:27). The visuals are driven entirely
by real analysis of the audio — nothing is faked or hand-keyed.

## The scene

- **Neon sun** rising over the horizon, pink→gold gradient with retro scanlines;
  it swells with the bass and pulses on detected onsets.
- **City skyline as an equaliser** — 64 towers whose heights are the log-frequency
  band energies of the audio, coloured bass-pink → treble-cyan.
- **Retro perspective grid floor** that scrolls faster when the track is louder.
- **Twinkling starfield** modulated by the treble band.
- **Shimmering reflection** of the sun and skyline in the grid "water".
- Intro **title card** that settles into a persistent lower-third.

## Pipeline

```
song.mp3 ──ffmpeg──▶ pcm.wav ──features.py──▶ features.npz
                                                   │
                              render.py (per-frame, numpy + Pillow)
                                                   │
                        worker.py × 4 (parallel) ──▶ seg_*.mp4
                                                   │
                              build.sh: concat + mux audio
                                                   ▼
                                          digital_dream.mp4
```

- `features.py` — decodes to mono PCM and computes, per video frame (30 fps):
  overall RMS, low/mid/high band energies, a 64-bin log-frequency spectrum, a
  spectral-flux onset envelope, and peak-picked beat impulses. Pure numpy STFT,
  no heavy deps.
- `render.py` — renders one frame from `features.npz`. `--preview T` writes a
  single PNG at time `T` for quick visual checks. Float32 compositing; glow via
  Gaussian-blurred screen blends.
- `worker.py` — renders a contiguous frame range and pipes raw RGB to an ffmpeg
  segment encoder.
- `build.sh` — fans out 4 workers across cores, then concatenates the segments
  and muxes the original audio into `digital_dream.mp4`.

## Regenerate

```bash
python3 -m venv venv && ./venv/bin/pip install numpy pillow
ffmpeg -y -i song.mp3 -ac 1 -ar 22050 -f wav pcm.wav
./venv/bin/python features.py
./build.sh          # -> digital_dream.mp4
```

Requires `ffmpeg` on the path. `song.mp3` is the source track (not committed here).
