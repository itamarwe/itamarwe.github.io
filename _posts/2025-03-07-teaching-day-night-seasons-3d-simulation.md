---
layout: post
title: "How I Built a 3D Simulation to Teach My Kids About Day, Night, and Seasons"
comments: true
date: 2025-03-07
categories: ai
---

Usually when my kids ask why it gets dark at night, or why summer days are longer, I reach for a piece of paper and start drawing. Diagrams of the Earth tilted on its axis, arrows marking the Sun's rays. It works — but it has obvious limits. The concepts I'm trying to explain are three-dimensional and dynamic, and my drawings are neither.

This time I opened Cursor instead.

## A few prompts, a working simulation

After a handful of prompts and a few manual corrections, I had code running — an interactive 3D Earth orbiting the Sun, built with Three.js, a library I had never touched before.

<video src="/img/earth-videos/clip1.mp4" autoplay loop muted playsinline style="width:100%;border-radius:8px;margin:1rem 0"></video>

Day and night become immediately intuitive when you can drag the camera around with your mouse. You can watch the boundary between light and dark shift as the Earth rotates, and see in real time exactly why half the planet is always in darkness.

<video src="/img/earth-videos/clip2.mp4" autoplay loop muted playsinline style="width:100%;border-radius:8px;margin:1rem 0"></video>

I used to demonstrate this with a lamp and a basketball in the kids' room before bed. This is better.

## The harder concepts

The same tool handles things that are genuinely tricky to explain on paper: why winter days are shorter, why summer days are longer, and why places near the poles have months of continuous daylight or darkness.

<video src="/img/earth-videos/clip3.mp4" autoplay loop muted playsinline style="width:100%;border-radius:8px;margin:1rem 0"></video>

The Earth's axial tilt is one of those concepts that sounds simple but takes a moment to really internalize. When you can move the camera to sit above the North Pole in June and watch the Sun circle the horizon without ever setting, it clicks much faster.

## What surprised me

I'm still surprised by how quickly Cursor let me build something I never could have built on my own in this amount of time. Not because the code is too hard — but because Three.js was entirely new to me, and I had no reason to invest the time to learn it from scratch for a one-off teaching tool.

That's what actually changed here. Before AI coding tools, building something like this cost more than it was worth. Now it costs less than drawing it on paper.

You can [try the simulation live](https://www.itamar-weiss.com/solar-system/) or browse the [code on GitHub](https://github.com/itamarwe/solar-system-simulation).
