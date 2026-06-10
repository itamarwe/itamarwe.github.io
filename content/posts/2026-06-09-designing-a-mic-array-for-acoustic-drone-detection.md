---
layout: post
title: "Designing a Microphone Array to Detect FPV Drones"
comments: true
date: 2026-06-09
categories: drones
image: /img/mic-array/social.png
---

<style>
.viz-frame { width: 100%; aspect-ratio: 16/10; border: 0; border-radius: 8px;
  margin: 1rem 0; background: #000; }
@media (max-width: 600px) { .viz-frame { aspect-ratio: 3/4; } }
</style>

You can detect an FPV drone before you can see it. The motors and props throw off a
characteristic whine — a blade-pass fundamental and its harmonics — sitting right
in the **300–4000 Hz** band. So a natural question: if I wanted to *detect* and
*classify* drones acoustically with a small array of microphones, **what shape
should that array be?**

I spent a weekend reading the literature and simulating the alternatives. This
post walks through the physics that constrains the design, compares the usual
geometries with simulated response curves, and lands on a recommendation. The
target: **16 microphones**, the 300–4000 Hz band, and an algorithm that processes
all 16 channels at once on an edge accelerator (Hailo / Jetson) — not necessarily
classical "beamform-then-detect."

## What the research says: algorithms and array shapes

Two bodies of work bear on this design — how people *classify* drone audio, and
how people *shape* the array.

**Detecting and classifying drone audio.** A good map of the field is this
[2025 holistic review of acoustic UAV detection](https://pubs.aip.org/aip/adv/article/15/12/120701/3373725/).
It splits into three generations:

1. **Classical signal processing.** A drone emits a quasi-periodic harmonic comb
   (blade-pass fundamental plus harmonics), so early detectors used harmonic-line
   and spectral-correlation detectors, matched filters, and energy thresholds.
   Cheap and interpretable, but brittle to wind and to harmonics that drift with
   throttle.
2. **Feature-engineered ML.** Extract MFCCs / spectral statistics and classify
   with SVM, kNN, or random forests. A cubic-kernel SVM on MFCCs reaches
   [~96.7% accuracy](https://www.frontiersin.org/journals/communications-and-networks/articles/10.3389/frcmn.2024.1440727/full)
   — very light to run, but dependent on hand-chosen features.
3. **Deep learning on spectrograms.** CNNs, RNNs, and CRNNs over Mel/STFT
   spectrograms now dominate; across studies CNN ≈ CRNN > RNN, with STFT-CNN
   detection above 98% and hybrid MFCC+STFT CNNs around 98.5%. Data scarcity is
   patched with [GAN-synthesised audio](https://pubmed.ncbi.nlm.nih.gov/34372189/),
   and recent work pushes into drone-*type* recognition
   ([AUDRON](https://arxiv.org/abs/2512.20407)).

**One-step vs multi-step** is exactly the
[sound-event-localization-and-detection (SELD) question](https://www.nature.com/articles/s44384-025-00036-3):

- *Multi-step / cascaded* — detect-then-classify, or estimate direction with a
  classical method (MUSIC, SRP-PHAT, beamforming) and feed a separate detector;
  in SELD, train detection first and transfer those weights to a direction model.
  Each stage is simple and swappable, but errors propagate and the pipeline is
  fiddly.
- *One-step / joint* — a single multichannel network takes raw channels or
  GCC-PHAT features and emits detection (and optionally direction) together. The
  [CRNN is the canonical SELD backbone](https://dcase.community/challenge2020/task-sound-event-localization-and-detection),
  and the [ACCDOA formulation](https://arxiv.org/abs/2006.12014) folds detection
  and direction into a single regression target. UAV-specific instances include
  real-time joint detect-and-localize systems and a
  [U-Net over dense beamformed energy maps](https://arxiv.org/abs/2508.00307).
- *Verdict* — joint models win on deployment simplicity; a few studies find
  cascaded better when detection and localization differ greatly in difficulty,
  at the cost of training complexity. For a 16-channel edge detector, a **joint
  CRNN / ACCDOA-style network fed GCC-PHAT** is the well-supported default — which
  is precisely why the array should maximize spatial-feature richness rather than
  form a pretty beam.

![Multi-step (cascaded detect-then-localize) versus one-step (a single joint multichannel network) pipelines for acoustic drone detection](/img/mic-array/algorithms_pipeline.png)

**Array topologies.** The geometry space is just as well mapped:

- **Uniform** (ULA, UCA): textbook baselines, excellent narrowband DOA, but
  aliasing caps the band — a
  [15-cm square drone array is unambiguous only to ~1.1 kHz](https://acta-acustica.edpsciences.org/articles/aacus/full_html/2026/01/aacus250134/aacus250134.html).
- **Aperiodic planar**: spiral / sunflower and randomized layouts from the
  acoustic-camera lineage, and
  [genetic-algorithm-optimized positions tuned for UAV DOA](https://www.mdpi.com/2504-446X/9/2/149).
- **Sparse / virtual-aperture**:
  [coprime](https://pubmed.ncbi.nlm.nih.gov/26233043/), nested, minimum-redundancy
  and [fractal](https://arxiv.org/abs/2001.01217) arrays break the λ/2 grid on
  purpose to synthesize a large *co-array* from few mics — a coprime pair of
  N+M−1 elements rivals an MN-element line. An
  [indoor-localization benchmark](https://arxiv.org/abs/2406.09001) ranks
  Open-Box > Nested > Billboard among sparse geometries. This is the formal
  backbone of the baseline-diversity argument below.
- **3-D / volumetric**:
  [tetrahedral arrays with DNNs](https://www.mdpi.com/1424-8220/26/6/1778) and
  [spherical arrays running spherical-harmonic MUSIC](https://ieeexplore.ieee.org/abstract/document/10051923/)
  that have tracked two UAVs at once. These give full 3-D direction and remove
  the up/down ambiguity of any flat array.

![The microphone-array topology families: uniform line and ring, aperiodic planar spiral, sparse coprime and nested layouts, and a 3-D volumetric dome](/img/mic-array/topology_families.png)

The recommendation below — a **nested-aperiodic dome** — is the drone-tuned
intersection of those last two families: a sparse, co-array-maximizing layout
lifted into 3-D, with the smallest baseline deliberately held ≤4 cm so nothing
aliases inside 300–4000 Hz.

## The one rule that fixes everything: λ/2

An array localizes sound by comparing the *phase* of a wavefront across its
microphones. The catch is sampling. Just like you can't reconstruct a 10 kHz tone
sampled at 5 kHz, you can't unambiguously sample a wavefront in *space* if your
microphones are too far apart. When the spacing exceeds **half a wavelength**, two
completely different arrival directions produce the *identical* set of phases at
the mics — a "grating lobe." The array literally cannot tell them apart.

<video src="/img/mic-array/Aliasing.mp4" autoplay loop muted playsinline style="width:100%;border-radius:8px;margin:1rem 0"></video>

At our top frequency of 4 kHz the wavelength is just 8.6 cm, so the **smallest
spacing between microphones has to be ≤ 4.3 cm**. But there's an opposing
pressure: angular resolution scales with the array's *aperture* (its overall
size) relative to wavelength. At 300 Hz the wavelength is 1.14 m, so to get any
bearing resolution at the bottom of the band you want a *large* aperture.

![The core tradeoff: the spacing needed to avoid aliasing shrinks with frequency, while resolution wants a large aperture](/img/mic-array/tradeoff.png)

Small spacing *and* large aperture, with only 16 microphones — you can't have both
with a uniform grid. A 1.2 m line at 4.3 cm spacing would need ~28 mics. **This
single conflict is what drives the entire design toward non-uniform, multi-scale
layouts.**

## How geometry shapes the response

I simulated the far-field response (a delay-and-sum beam pattern) for the usual
candidates: a line (ULA), a single ring (UCA), concentric rings, a spiral, a
random planar layout, and a 3-D hemispherical dome. The most important contrast is
between **uniform** and **aperiodic** spacing:

<video src="/img/mic-array/BeamForming.mp4" autoplay loop muted playsinline style="width:100%;border-radius:8px;margin:1rem 0"></video>

A uniform ring grows sharp, discrete **grating lobes** at high frequency — phantom
directions as loud as the real one. An aperiodic spiral, with the *same* 16 mics
and the *same* aperture, smears that energy into a low, diffuse sidelobe floor
instead. There are no phantom directions, just slightly raised noise.

Here are the polar beam patterns across the band, live. **Switch geometry, drag
the frequency slider, and orbit the 3-D response "balloon"** — the bulges that
sprout away from the blue look-direction as you raise the frequency on the ring
(UCA) are grating lobes; the nested-aperiodic dome keeps them suppressed:

<iframe src="/mic-array-viz/beam.html" title="Interactive 3-D beam-pattern explorer — drag to rotate, switch geometry, sweep frequency" loading="lazy" class="viz-frame"></iframe>

## The insight that matters for a 16-channel network

Here's the thing that reframed the problem for me. If you're feeding all 16
channels into a neural network (raw multichannel, or a stack of GCC-PHAT
cross-correlations), you don't actually care about a textbook beam. You care about
**how many independent spatial measurements the geometry hands the network.**

Every *pair* of microphones is one baseline — one time-difference / coherence cue.
With 16 mics that's 120 pairs. But on a uniform ring, those 120 pairs collapse
onto just **8 distinct baseline lengths** — hugely redundant. An aperiodic layout
spreads them across ~100 distinct baselines:

<video src="/img/mic-array/CoArray.mp4" autoplay loop muted playsinline style="width:100%;border-radius:8px;margin:1rem 0"></video>

<iframe src="/mic-array-viz/coarray.html" title="Interactive 3-D co-array explorer — switch geometry to compare baseline diversity" loading="lazy" class="viz-frame"></iframe>

Flip between the geometries above: the **UCA collapses its 120 pairs onto 8
distinct baselines** (15× redundant — the cyan cloud snaps into a few rings),
while the **nested dome spreads them across ~95** (1.3× redundant — a full 3-D
cloud). That spread is exactly the spatial information a 16-channel network feeds
on.

Collapsing that cloud onto a 1-D histogram of baseline *lengths* makes the
trade-offs even sharper — here for the 1.2 m arrays:

![Histograms of the 120 pairwise baseline lengths for each array at 1.2 m aperture: the uniform ring piles them onto 8 lengths, aperiodic layouts spread them out, and only the nested array has both a cluster of tiny baselines and a spread of large ones](/img/mic-array/baseline_histograms_large.png)

The uniform ring dumps all 120 pairs onto **8 lengths** (tall spikes, nothing
below ~23 cm). A *circular aperiodic* ring spreads them richly but still keeps
almost nothing small — which is why its high-frequency floor rises. Only the
**nested** array shows the multi-scale signature: a cluster of tiny baselines
*left of the 4.3 cm line* (which keep 4 kHz unambiguous) **plus** a spread out to
the full aperture (which buys low-frequency resolution).

More distinct baselines means more independent spatial features, which means
easier detection and coarse bearing — **without** needing classical beamforming at
all. This is the real reason to prefer an aperiodic array for a *learned*
detector: discrete grating lobes are genuine ambiguities a network can't undo from
a single snapshot, whereas an elevated sidelobe floor is benign and learnable.

## The recommendation: a nested-aperiodic dome

Combining both pressures gives a clear winner — a **multi-scale (nested) aperiodic
layout**: a *tight central cluster* of ~6 mics within a ≤4 cm radius (which keeps
the minimum spacing small enough to stay alias-free up past 4 kHz), plus ~10
*outrigger* mics spread aperiodically out to the full aperture (which buys the
low-frequency resolution). Lift the centre mics out of plane onto a shallow
**dome**, and you also break the up/down ambiguity that every flat array suffers —
which matters because FPV threats come from *above*.

<video src="/img/mic-array/Recommended.mp4" autoplay loop muted playsinline style="width:100%;border-radius:8px;margin:1rem 0"></video>

The simulations back it up. Across both form factors, the nested design is the
**only** layout that stays alias-free past 4 kHz *and* exposes 100+ distinct
baselines. Here are the response curves for the large (1.2 m) array — note how the
single ring (UCA) and line (ULA) collapse to near-0 dB peak sidelobes (full
ambiguity) at high frequency, while the nested designs hold a clean floor and a
sharp 7° beam:

![Recommendation backing for the 120 cm array: layouts, 3-D dome, peak-sidelobe and beamwidth vs frequency](/img/mic-array/recommend_large.png)

I analysed two sizes:

| | Medium (~35–40 cm) | Large (~1.0–1.2 m) |
|---|---|---|
| Min spacing (centre cluster) | ~2–4 cm | ~3–4 cm |
| Alias-free to | ~7.5 kHz | ~4.5 kHz |
| Beamwidth @ 3 kHz | ~20° | **~7°** |
| Best at | portability, vehicle/post mount, coarse bearing | long-range SNR, sharp low-freq bearing |
| Trade | wider beam, shorter range | bulky; needs a rigid weatherproof frame |

If the array has to be **flat** (a roof panel, a wall), drop the dome to a plane —
you keep every broadband and diversity benefit and only lose elevation
discrimination. That's the pragmatic default when a 3-D structure isn't practical.

**What to avoid:** the uniform single ring (UCA) and the plain line (ULA). The ring
is a workhorse for *narrowband* DOA and shows up everywhere in the literature, but
for a 300–4000 Hz *broadband* detector with only 16 mics it aliases over most of
the band. The line is 1-D only and, at 1.2 m, fully ambiguous up high.

## A few practical notes

- **You don't need beamform-then-detect.** Feed raw multichannel into a CNN/CRNN,
  or pre-compute the 120 GCC-PHAT cross-correlations into a "spatial image" and let
  a small conv net classify it. Both map cleanly onto INT8 inference on Hailo or
  Jetson, and 120 cross-correlations is nothing for a Jetson.
- **Sample at ≥10–16 kHz** to cover 4 kHz with anti-alias margin. 16 ch × 16 kHz ×
  16-bit is ~4 Mbit/s — trivial.
- **Calibrate.** Aperiodic arrays live or die on accurate per-mic position and
  phase calibration — bake the *measured* positions into the feature extractor.
- **MEMS mics** (digital I²S/PDM, phase-matched) are the obvious building block:
  cheap and easy to mount on a PCB dome or disk.

The whole thing — the geometry library, the response-curve simulations, and the
manim animations above — is a couple hundred lines of Python. The physics is old
(spatial Nyquist, aperiodic phased arrays from the acoustic-camera world); the new
part is realizing that when a 16-channel network is doing the detection, the right
objective isn't a pretty beam, it's **baseline diversity**.
