---
layout: post
title: "How to Geolocate a Photo From a Single Image"
comments: true
date: 2026-06-08
categories: ai
---

With images from the Iran conflict once again circulating across social media and OSINT communities, it's a good opportunity to talk about photo geolocation: how can you determine exactly where a photo was taken from a single image?

![A photo taken in Tel Aviv — where, exactly, was the camera standing?](/img/photo-geolocation/tel-aviv-photo.jpeg)

Most people think of geolocation as a visual search problem: identify a landmark, compare it against Street View, and narrow down the location.

But there's another approach.

## Solving for the camera, not the landmark

A classic computer vision algorithm called **Perspective-n-Point (PnP)** can estimate the exact position and orientation of the camera that captured an image.

The idea is surprisingly simple. If you can identify several points whose coordinates are known both in the real world and in the image, PnP can solve for the camera pose that best explains what the camera sees.

In practice, this means estimating:

- **Camera position** (x, y, z)
- **Camera orientation** (roll, pitch, yaw)
- **Focal length**

The algorithm searches for the camera configuration that minimizes the *reprojection error* — the gap between where the known points actually appear in the image and where the estimated camera would project them.

## A tool built on Tel Aviv's open GIS data

To demonstrate this, I built a small tool connected to Tel Aviv's open municipal GIS datasets, including building footprints and elevation information.

![The GeoPhoto tool: the photograph on the left, Tel Aviv's building map on the right](/img/photo-geolocation/tool-overview.png)

Given a photo, you select matching visual anchors in both the image and the map — building corners work particularly well — and the system estimates the camera location.

![Matching anchors on building corners in both views; the estimated camera pose appears on the right](/img/photo-geolocation/anchors-and-pose.jpeg)

Here's the full workflow end to end:

<video src="/img/photo-geolocation/demo.mp4" controls autoplay loop muted playsinline style="width:100%;border-radius:8px;margin:1rem 0"></video>

When I tested it on a photo I took in Tel Aviv, it recovered the shooting position with surprisingly high accuracy — down to the rooftop I was standing on.

It's a nice example of how techniques developed decades ago for computer vision are still incredibly powerful today, and how much information can be extracted from a single image when geometry meets maps.

## Try it yourself

You can try the tool with your own photo here: [itamarweiss.com/photo-geolocation](/photo-geolocation/).
