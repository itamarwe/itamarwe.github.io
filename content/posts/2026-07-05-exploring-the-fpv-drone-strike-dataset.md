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

A few weeks ago I [opened up a dataset of Hezbollah FPV drone-strike videos](/blog/fpv-drone-strikes-open-dataset/) — roughly fifty clips I'd pulled off my phone, labelled and kept in one place so anyone building in defense — or anyone in the field — could start from real footage. I put everything on S3 and [published a repo with links on GitHub](https://github.com/itamarwe/fpv-drone-strikes-lebanon-dataset). It made an impact — I received dozens of messages — but it still wasn't accessible enough. It wasn't something a commander in the field could just watch, or an engineer could share as a link with a colleague. To answer a simple question — "show me the strikes on air-defense sites near the border, and skip the propaganda intros" — you had to download MP4s and scrub through them by hand.

Many of those messages — from engineers in the industry, military researchers, and civilians — were about the flight paths: estimates of speed and altitude. The clips are heavily edited, low quality, and noisy, but **that information is still in the footage** — it's encoded in how the camera moves through the world. I put in the work to extract it with computer vision: reconstruct the 3-D scene, recover camera positions along each clip, and make the result browsable. In parallel I kept collecting — scraping every open source I could find — and the catalog is now **150+ videos** at the time of writing, up from those original fifty.

That's what **[itamarweiss.com/fpv](/fpv)** is: a browser-facing viewer over the whole collection — a searchable gallery, an annotated video player, and orbitable 3-D scenes — so you can browse, watch, and fly through a strike without downloading anything first. I built it fast, so it can be a bit buggy; not every clip has a 3-D scene yet; and some reconstructions are extremely noisy or inaccurate. But it's a starting point.

## YouTube for FPV attacks

Think of it as YouTube for FPV attacks — three pieces wired together: a **gallery** of the full dataset, a **video viewer** for watching each clip, and a **3-D scene viewer** for the ones I've reconstructed.

![The viewer is a searchable gallery, a flight-annotated video player, and an orbitable 3-D scene viewer](/img/fpv-viewer/tool_flow.png)

The **gallery** is the front door — every clip as a card with a first-frame thumbnail, searchable by description, town or date, sortable, and filterable down to just the ones that have a 3-D scene. Open any card and you're in the **video viewer**, with a flight-annotation timeline underneath so you can jump straight to the parts that are genuinely the drone flying. For the clips I've run through the reconstruction pipeline, the **3-D scene viewer** opens the recovered geometry of the strike: orbit the terrain, follow the attack path, and measure distances in the scene.

Here's the whole thing in one pass — browsing the gallery, watching a clip in the video viewer, and opening its 3-D scene (the strike on the "Biranit" Iron Dome platform):

<video src="/img/fpv-viewer/viewer-demo.mp4" class="demo-video" autoplay loop muted playsinline></video>

It's the same catalog as the repo, just alive — and it grows as new footage surfaces. It's best experienced full-screen at **[itamarweiss.com/fpv](/fpv)**.

## Annotations: extracting the flight segments

Every clip is *edited* — published as propaganda. The pattern is always the same: a title-card banner up front, cuts between flight segments, a freeze on the moment of impact, then a slow-motion replay and branded outro. **Most of the runtime is noise the editor layered on top**; the camera is the weapon's eye, but only for part of the file.

So in order to extract: the footage is segmented into *flight*, *banner*, *pause / freeze* and *replay*, and the player lets you jump straight to the parts that are genuinely the drone flying. Here's one clip, annotated — the 2026-06-06 Merkava-tank strike near Blat:

![The annotation timeline for one clip: banner, then alternating flight segments, a freeze near impact, and a slow-motion replay at the end](/img/fpv-viewer/annotated_clip.png)

Those boundaries come from a quick automated annotator I wrote — useful, but not robust enough to trust without a manual pass. I've reviewed most of the clips; a handful still haven't been cleaned up.

![Across all annotated footage, barely half the seconds are actual flight; the rest is banners, freezes and replays](/img/fpv-viewer/footage_breakdown.png)

Of the roughly 2.4 hours of annotated footage, **only about half is real flight.** The other half is banners, freeze-frames and replays.

## Exploring the attack scenes in 3-D

The second idea is the payoff from the [last post](/blog/fpv-drone-strikes-open-dataset/), made interactive. There I took a *single* clip and recovered the drone's real 3-D attack path straight from the pixels, just [VGGT-Omega](https://vggt-omega.github.io/) run over the isolated flight frames. Since then I've run that pipeline across the dataset, and **a growing share of the clips now have a full 3-D reconstruction** you can open in the browser.

Each scene is the recovered point cloud of the terrain plus the drone's flight path — the ordered camera centers — drawn from the launch camera along the approach to the terminal pose over the target, with a corner panel that plays the real footage in step with the reconstruction. You orbit it with the mouse, and there's a **measure tool**: click two points and it reads back the distance between them, so you can eyeball a standoff range or the size of a targeted vehicle in the reconstruction's own units. Filter the gallery to **3D scenes** and click any card's *3D scene* button to open one.

Do that across the whole collection and the anecdotes start turning into distributions: approach corridors, dive angles, standoff distances, and speeds along the path — the geometry of how these attacks actually unfold, browsable one clip at a time.

## Why bother building the viewer

I could have left it as a repo. But a dataset you can't *see* barely gets used, and the whole reason I opened this one up was for it to get used — by anyone trying to understand how the threat behaves, or to build and evaluate the sensors and algorithms that stop it. It's the same instinct behind [designing a microphone array to hear these drones](/blog/designing-a-mic-array-for-acoustic-drone-detection/): the tools only get you so far without representative data you can actually put your hands on.

So the viewer is live and it tracks the dataset as it grows: **[itamarweiss.com/fpv](/fpv)**. The underlying collection — clips, labels, manifest — stays open at **[github.com/itamarwe/fpv-drone-strikes-lebanon-dataset](https://github.com/itamarwe/fpv-drone-strikes-lebanon-dataset)**. Browse it, learn from it, and if you have footage that belongs in it, send it my way.
