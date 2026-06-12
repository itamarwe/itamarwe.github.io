---
layout: post
title: "The Dolly Zoom, From the Inside"
comments: true
date: 2026-06-12
categories: graphics
image: /img/dolly-zoom/social.png
---

<style>
.viz-frame { width: 100%; aspect-ratio: 16/10; border: 0; border-radius: 8px;
  margin: 1rem 0; background: #000; }
@media (max-width: 600px) { .viz-frame { aspect-ratio: 3/4; } }
</style>

You've seen it a hundred times. A character stares down a hallway, the camera
holds them dead centre at exactly the same size — and yet the walls seem to
*lunge* toward them, the far end of the corridor rushing in or falling away. It's
the shot Hitchcock invented for *Vertigo*, and it shows up every time a director
wants to put unease on screen without moving the actor. The **dolly zoom**.

The effect feels like an optical illusion, but it's pure geometry. I wanted to
take it apart — so I built a 3-D scene with **two views side by side**: on the left,
what the camera sees; on the right, a top-down map of where the camera actually is
and how its field of view fans out across the scene. Drive the slider and both
update together:

<video src="/img/dolly-zoom/dolly-zoom.mp4" autoplay loop muted playsinline style="width:100%;border-radius:8px;margin:1rem 0"></video>

It's a soldier on a road through a valley in southern Lebanon — pine and cypress
on the slopes, ridgelines on the horizon, a second soldier standing **100 m back**.
The foreground soldier never changes size. Everything behind him does: the
mountains swell, the forest crowds in, and the distant soldier balloons from a
speck into a presence right over his shoulder. The top-down view tells you *why* —
watch the camera slide backwards down the road while its view-cone narrows to a
sliver.

## Two knobs, moving in lockstep

A dolly zoom is two camera moves performed at once, tuned to cancel each other for
exactly one object in the frame:

- **Zoom** — you lengthen the lens. The field of view narrows, magnifying
  everything uniformly.
- **Dolly** — you physically roll the camera backward, away from the subject.

Zoom in and the subject would grow; dolly back and it would shrink. Do both in the
right ratio and the subject holds perfectly still. The trick is that these two
moves *don't* cancel for anything at a different distance — and that's where the
whole effect lives.

## The one equation

An object of real height *H* sitting at distance *d* from the camera, seen through
a lens with vertical field of view *θ*, fills this fraction of the frame:

```
screen size  ∝  H / ( d · tan(θ/2) )
```

To keep the subject pinned at a constant on-screen size, you hold the denominator
constant:

```
d · tan(θ/2)  =  constant
```

So when you narrow the field of view (smaller *θ*, longer lens), you must increase
*d* by the same factor — dolly the camera back. That's the entire rig in one line.

![The dolly-zoom geometry: same subject size, different background slice](/img/dolly-zoom/geometry.png)

Both cameras above frame the subject identically — the subject fills the frame
either way. But trace each lens's cone out to the background: the **wide lens up
close** spreads its rays into a *tall* slice of the world, so any given tree or
ridge occupies a small fraction of that slice and looks far away. The
**telephoto, dollied back**, captures a *narrow* slice — the same tree now fills
most of the frame and looks like it's breathing down the subject's neck. This is
exactly the view-cone you can watch widen and narrow in the top-down panel of the
demo.

## It's the dolly that compresses, not the zoom

Here's the part that surprised me. Put the background object at distance *d + Δ*,
where *Δ* is the fixed gap behind the subject (100 m in my scene). Its size on
screen, *relative* to the subject, works out to:

```
background size / subject size  ∝  d / (d + Δ)
```

Notice what's *not* in that expression: the focal length. The lens dropped out
entirely. Zoom magnifies the subject and the background by the same factor, so it
can never change their *ratio*. The only thing that moves the ratio is **d**, the
dolly distance.

- Camera up close, *d* small: `d / (d + Δ)` is tiny, so the background is crushed
  down — small and far.
- Camera dollied back, *d* large: `d / (d + Δ)` climbs toward 1, the gap stops
  mattering, and the background swells to nearly the subject's relative scale.

So the dolly is doing the dramatic work — collapsing or expanding depth. The zoom
is just bookkeeping that holds the subject still so your eye has a fixed anchor to
measure all that motion against. Strip the zoom away and you'd still get the
compression; you just wouldn't notice it, because the subject would be sliding
around too.

## Drive it yourself

The demo below is fully interactive — drag the slider, or hit **Auto** to let it
sweep. Push it from 1× toward 30× and watch the **lens** climb from a wide ~23 mm
into deep telephoto near 700 mm, the **dolly distance** stretch from 6 m out to
180 m, and the field of view collapse from 55° down to about 2° — all while the
soldier stays exactly where he is.

<iframe src="/dolly-zoom/" title="Interactive dolly-zoom demo — camera view and top-down map, side by side" loading="lazy" class="viz-frame"></iframe>

Keep one eye on the top-down map, which is drawn to a **fixed** scale — the two
soldiers never move on it. The cyan wedge is the camera's field of view; as it
narrows, the camera glyph is the only thing that slides, rolling backwards down the
road to hold the subject's green marker at the same apparent size. By 30× the tan
marker 100 m back has been swallowed inside a 2°-wide sliver of a cone. The readouts
along the bottom are the whole point: every parameter that produces the effect, live
and coupled.

## How it's built

The scene is a few hundred lines of [Three.js](https://threejs.org/) — a dusk sky,
a valley floor, ridgelines, a scattered Mediterranean forest, and two soldiers
built from boxes and cylinders. The left panel is a perspective camera; the right
panel is an orthographic camera looking straight down, sharing the same world. The
dolly zoom itself is four lines in the render loop. Starting from a base field of
view and distance, each slider value *z* maps to:

```js
const halfFovRad = Math.atan(baseHalfTan / z);   // narrow the FOV
const distance   = BASE_DISTANCE * z;            // dolly back in proportion
camera.fov = THREE.MathUtils.radToDeg(halfFovRad * 2);
camera.position.z = distance;
```

`baseHalfTan` is `tan(θ₀/2)` at 1×. Dividing it by *z* shrinks the field of view;
multiplying the distance by *z* keeps `d · tan(θ/2)` constant. That's the equation
from above, transcribed directly into code. The focal-length readout is just the
same FOV expressed as a 35 mm-equivalent lens, because "20 mm vs 200 mm" is more
intuitive than "60° vs 6°" if you've ever held a camera.

The physics here is over a century old, and the shot itself is 70. But there's
something clarifying about being able to grab the two knobs yourself and feel how
rigidly they're coupled — how the most disorienting shot in cinema is really just
`d · tan(θ/2) = constant`, held steady while everything behind it gives way.
