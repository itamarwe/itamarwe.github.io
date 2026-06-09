---
layout: post
title: "Designing a Microphone Array to Hear FPV Drones"
comments: true
date: 2026-06-09
categories: drones
---

You can hear an FPV drone before you can see it. The motors and props throw off a
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

Here are the polar beam patterns for the medium (40 cm) array across the band.
Watch the petals multiply on the ring-based layouts as frequency climbs:

![Delay-and-sum beam patterns at 300/1000/2000/4000 Hz for six geometries, 40 cm aperture](/img/mic-array/beampatterns_medium.png)

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

![Co-array (pairwise baselines) and baseline-length histograms: uniform ring vs aperiodic layouts](/img/mic-array/coarray_medium.png)

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
part is realizing that when a 16-channel network is doing the listening, the right
objective isn't a pretty beam, it's **baseline diversity**.
