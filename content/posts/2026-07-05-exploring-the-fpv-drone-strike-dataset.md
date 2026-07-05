---
layout: post
title: "A Browser for the FPV Drone-Strike Dataset"
date: 2026-07-05
categories: drones
image: /img/fpv-viewer/social.png
---

<style>
.demo-video { width: 100%; border-radius: 8px; margin: 1rem 0; display: block;
  background: #000; }
</style>

![Explore the FPV strike dataset — a reconstructed 3-D attack path on the "Biranit" Iron Dome platform, in the viewer](/img/fpv-viewer/social.png)

A few weeks ago I [opened up a dataset of Hezbollah FPV drone-strike videos](/blog/fpv-drone-strikes-open-dataset/) — every clip I could pull out of OSINT, labelled and kept in one place so anyone building a defense could start from real footage instead of a press release. It worked as a *dataset*: a repo, a manifest, download links, files in S3. It was miserable as something to actually *look at*. To answer a simple question — "show me the strikes on air-defense sites near the border, and skip the propaganda intros" — you were downloading MP4s and scrubbing through them by hand.

So I built the thing that was missing: **a viewer that turns the folder-of-links into something you can browse, read, and fly through, right in the browser.** It's live at **[itamar-weiss.com/fpv](/fpv)**. This post is what it does and the two ideas behind it that I think are worth stealing for any video-forensics collection.

## Three ways to look at the same clip

The viewer is small on purpose — one dataset, three views, each answering a different question.

![The viewer gives you three views of every clip: a searchable gallery, an auto-annotated flight timeline, and an orbitable 3-D scene](/img/fpv-viewer/tool_flow.png)

The **gallery** is the front door: every clip as a card with a first-frame thumbnail, searchable by description, town or date, sortable, and filterable down to just the ones that have a reconstructed 3-D scene. The **player** adds a flight-annotation timeline underneath the video. And the **scene view** — for the clips I've reconstructed — lets you orbit the actual 3-D geometry of the strike and measure distances in it.

Here's the whole thing in one pass — browsing the gallery, reading a clip's flight-annotated player, and orbiting its reconstructed 3-D scene (the strike on the "Biranit" Iron Dome platform):

<video src="/img/fpv-viewer/viewer-demo.mp4" class="demo-video" autoplay loop muted playsinline></video>

It's the same catalog as the repo, just alive — and it grows as new footage surfaces. It's best experienced full-screen at **[itamar-weiss.com/fpv](/fpv)**.

## The clips are propaganda, so I annotate them

Here's the first idea that shaped the tool. These videos are *edited* — they're published as propaganda, not as evidence. A single clip opens on a title-card banner, cuts between flight segments, freezes on the moment of impact, and ends on a slow-motion replay with a branded outro. If you're a human trying to study tactics, or a model trying to learn from the footage, **most of the runtime is noise the editor added on top.** The camera is the weapon's eye, but only for part of the clip.

So every video in the viewer gets a **flight-annotation timeline**: the footage is segmented into *flight*, *banner*, *pause / freeze* and *replay*, and the player lets you jump straight to the parts that are genuinely the drone flying. Here's one clip, annotated — the 2026-06-06 Merkava-tank strike near Blat:

![The annotation timeline for one clip: banner, then alternating flight segments, a freeze near impact, and a slow-motion replay at the end](/img/fpv-viewer/annotated_clip.png)

You can read the edit right off the ribbon: an eight-second banner up front, a burst of flight segments broken up by brief freeze-frames as the editor punches in on targets, a longer pause near the moment of impact, and a replay tail at the end. The blue is the only part that's actually a camera moving through the world.

And this isn't a one-off. Once every clip is annotated, you can add it up across the whole dataset — and the split is its own small piece of intelligence:

![Across all annotated footage, barely half the seconds are actual flight; the rest is banners, freezes and replays](/img/fpv-viewer/footage_breakdown.png)

Of the roughly 2.4 hours of annotated footage, **only about half is real flight.** The other half is banners, freeze-frames and replays. That's the concrete argument for annotating: if you feed a reconstruction pipeline or a training set the raw clips, half your data is title cards and slow-motion — and, worse, the freezes and replays look like camera motion to a naive algorithm and quietly poison the geometry. The timeline is how you keep only the signal. (The segment boundaries here are auto-generated; they're a starting point, not hand-verified ground truth.)

## The clips you can fly

The second idea is the payoff from the [last post](/blog/fpv-drone-strikes-open-dataset/), made interactive. There I took a *single* clip and recovered the drone's real 3-D attack path straight from the pixels — no telemetry, just [VGGT](https://arxiv.org/abs/2503.11651) run over the isolated flight frames. Since then I've run that pipeline across the dataset, and **a growing share of the clips now have a full 3-D reconstruction** you can open in the browser.

Each scene is the recovered point cloud of the terrain plus the drone's flight path — the ordered camera centers — drawn from the launch camera along the approach to the terminal pose over the target, with a corner panel that plays the real footage in step with the reconstruction. You orbit it with the mouse, and there's a **measure tool**: click two points and it reads back the distance between them, so you can eyeball a standoff range or the size of a targeted vehicle in the reconstruction's own units. Filter the gallery to **3D scenes** and click any card's *3D scene* button to open one.

Do that across the whole collection and the anecdotes start turning into distributions: approach corridors, dive angles, standoff distances — the geometry of how these attacks actually unfold, browsable one clip at a time.

## Why bother building the viewer

I could have left it as a repo. But a dataset you can't *see* barely gets used, and the whole reason I opened this one up was for it to get used — by anyone trying to understand how the threat behaves, or to build and evaluate the sensors and algorithms that stop it. It's the same instinct behind [designing a microphone array to hear these drones](/blog/designing-a-mic-array-for-acoustic-drone-detection/): the tools only get you so far without representative data you can actually put your hands on.

So the viewer is live and it tracks the dataset as it grows: **[itamar-weiss.com/fpv](/fpv)**. The underlying collection — clips, labels, manifest — stays open at **[github.com/itamarwe/fpv-drone-strikes-lebanon-dataset](https://github.com/itamarwe/fpv-drone-strikes-lebanon-dataset)**. Browse it, learn from it, and if you have footage that belongs in it, send it my way.
