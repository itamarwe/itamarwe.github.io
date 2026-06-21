---
layout: post
title: "An Open Dataset of FPV Drone Strikes — and a 3-D Flight Path From One Clip"
comments: true
date: 2026-06-21
categories: drones
image: /img/fpv-drone-strikes/social.png
---

![An open dataset of FPV drone strikes, and a real 3-D flight path reconstructed from one clip](/img/fpv-drone-strikes/social.png)

The cheapest, fastest-evolving threat on Israel's northern border right now is a
$500 quadcopter with a warhead zip-tied to it. Hezbollah has been flying FPV
(first-person-view) drones across the frontier and posting the strike videos as
propaganda — and every one of those clips is also, whether they like it or not, a
piece of intelligence. The camera *is* the weapon's eye. If you watch enough of
them, patterns fall out: what gets targeted, from what direction, with what
approach profile.

So I started collecting them. The result is an open, constantly-updated dataset of
Hezbollah FPV drone-strike videos:
**[github.com/itamarwe/fpv-drone-strikes-lebanon-dataset](https://github.com/itamarwe/fpv-drone-strikes-lebanon-dataset)**.
It's public on purpose. **I want anyone who is trying to understand how the enemy
operates — or to build the sensors and algorithms that stop these drones — to be
able to start from real data instead of a press release.** This post is what's in
it, and a demo of the kind of thing you can pull out of a single clip: a real 3-D
flight path, reconstructed straight from the footage.

## What's in the dataset

At the time of writing it's **95 strike videos** spanning 2026-04-29 to 2026-06-13,
and it grows as new footage surfaces. The repo itself is deliberately lightweight —
a catalog with stable links — while the MP4s and thumbnails live in S3. Each entry
is just enough to be useful:

- a **date**,
- a **first-frame thumbnail**,
- a short **description** of the target and location (e.g. *"Merkava tank, Beaufort
  Castle"*, *"Excavator, Majdal Zoun"*), and
- a **download link** to the raw clip.

A separate manifest also carries a **confidence** field and notes — because a lot of
these are labelled from the Arabic title card burned into the video, and I'd rather
be honest about which labels are certain and which are inferred. Of the 95, about
two-thirds are high-confidence reads.

A couple of representative entries:
[Sholef howitzer, Adaissah (2026-06-06)](https://github.com/itamarwe/fpv-drone-strikes-lebanon-dataset)
and
[D9 armored bulldozer, Tayr Harfa (2026-06-12)](https://github.com/itamarwe/fpv-drone-strikes-lebanon-dataset)
— the full table with thumbnails and download links is in the repo README.

## What the enemy is actually striking

Once you tabulate the target labels, the mix is its own piece of intelligence. This
is **real counts** from the dataset manifest, not an estimate:

![Target mix across the dataset: Merkava tanks, personnel, Namer APCs, engineering vehicles, Humvees, sensors and air-defense](/img/fpv-drone-strikes/target_mix.png)

Armor dominates — Merkava tanks are the single most-targeted category — followed by
personnel and Namer APCs. But the long tail is the interesting part: **engineering
vehicles** (D9 bulldozers, excavators) clearing terrain, and a cluster of
**sensors, air-defense and counter-UAS platforms** — surveillance cameras, radar,
Iron Dome launchers, even "anti-drone platforms." The enemy is deliberately going
after the things that would *see* or *stop* the next drone. That alone tells you
where defensive effort is worth spending.

And it keeps coming. Plotting the videos by date, the log just climbs:

![Cumulative documented strike videos over time, climbing steadily from late April to mid-June 2026](/img/fpv-drone-strikes/timeline.png)

That's the case for keeping this open and current: a snapshot ages instantly; a
living dataset lets a detection model — or a person — keep learning as the tactics
shift.

## The fun part: a 3-D flight path from one clip

Here's what got me excited enough to write this up. A strike video is a monocular
camera moving through a real scene. That's exactly the input that modern
feed-forward 3-D reconstruction eats for breakfast. So I took **one** clip — the
2026-06-06 Sholef-howitzer strike near Adaissah — and asked: can I recover the
drone's actual 3-D flight path, with no telemetry, just from the pixels?

Short answer: yes.

The pipeline is short, and I kept all of it
[in the repo](https://github.com/itamarwe/fpv-drone-strikes-lebanon-dataset)
alongside the figure code for this post:

![Pipeline: strike video → isolate the FPV footage → VGGT → camera poses + point cloud → flight path](/img/fpv-drone-strikes/pipeline.png)

The one non-obvious step is the first one. These clips are *edited propaganda*: they
open with a title card and a logo sting, sometimes splice in a replay, and end on a
branded outro. None of that is camera motion through a scene — feed it to a
reconstructor and it pollutes everything. So before anything else I had to **isolate
the segment that's genuinely FPV footage** (here, roughly seconds 8 through 46 of a
53-second clip) and drop the rest.

Then the real work is done by **[VGGT](https://arxiv.org/abs/2503.11651)** (Visual
Geometry Grounded Transformer, Wang et al., CVPR 2025) — a network that takes a
handful of frames and, in a single forward pass, predicts the camera pose for each
frame plus a dense 3-D point cloud of the scene. No per-scene optimization, no
COLMAP, no telemetry. I ran the real model through the public
[facebook/vggt-omega](https://huggingface.co/spaces/facebook/vggt-omega) Space on 38
sampled frames. **The camera centers it recovers, in order, *are* the drone's flight
path.**

Here's the extraction. On the left is the actual FPV feed — the drone's own view,
sweeping over terrain, past buildings, onto the target. On the right is the VGGT
reconstruction: the scene as a point cloud, and the flight path drawing itself in,
one recovered pose per frame, as the view orbits so you can see it's genuinely 3-D.

<video src="/img/fpv-drone-strikes/path_extraction.mp4" autoplay loop muted playsinline style="width:100%; border-radius:8px; margin:1rem 0;"></video>

And the reconstruction on its own — the terrain ahead fanning out from the dense
depth estimate, with the approach traced from the launch view (green) down the
cyan-to-gold line to the terminal pose over the target:

![VGGT reconstruction of the scene point cloud with the recovered FPV flight path](/img/fpv-drone-strikes/reconstruction_hero.png)

## Being honest about what this is

This is the *real* model output, not an illustration — so let me be just as real
about its limits:

- **Scale is relative.** VGGT recovers geometry up to an unknown global scale (and a
  rotation). The *shape* of the trajectory and the scene are real; the absolute
  meters and the true vertical are not pinned down without extra information.
- **A couple of poses are wrong.** Of the 38 frames, VGGT mis-estimated **2** —
  motion-blurred frames where it briefly snapped the camera back near the origin. I
  flag those as outliers (the red crosses) and interpolate the drawn line across
  them rather than pretending they're good. That's a normal failure mode on fast,
  fisheye, compressed FPV video, and it's worth seeing.
- **The depth is noisy.** FPV lenses are heavily distorted, the sky and motion blur
  give the network little to grab onto, and the point cloud fans out accordingly.
  It's a reconstruction, not a survey.

Even with those caveats, the payoff is striking: from a propaganda clip and a single
forward pass, you get a geometric reconstruction of the approach. Do that across the
whole dataset and you start to see **approach corridors, dive angles, and standoff
distances** as distributions, not anecdotes.

## Why I'm keeping it open

Defense against these drones is a data problem before it's a hardware problem. Every
clip is a labelled example of how the threat actually behaves — and that's exactly
what you need to train a detector, validate a sensor placement, or stress-test a
counter-UAS system against real attack geometry rather than a tidy simulation. It's
the same reason I went down the rabbit hole of
[designing a microphone array to detect FPV drones](/blog/designing-a-mic-array-for-acoustic-drone-detection/):
the physics and the algorithms only get you so far without representative data to
point them at.

So the dataset stays public and stays current. If you're researching the threat,
building a defense, or just want to understand what's happening on the border with
your own eyes:
**[github.com/itamarwe/fpv-drone-strikes-lebanon-dataset](https://github.com/itamarwe/fpv-drone-strikes-lebanon-dataset)**.
Use it, learn from it, and if you have footage that belongs in it, send it my way.
