---
layout: post
title: "Why Can't Drones Fly for More Than 40 Minutes? (Part 2)"
comments: true
date: 2024-12-13
categories: drones
---

In the [previous parts](/drones/2024/12/11/why-drones-cant-fly-more-than-40-minutes.html) we talked about the principles behind how drones fly, and about the counter-intuitive insight that a drone's flight time is limited no matter how many batteries we add — and in fact, that this is true for any aircraft.

In this part we'll focus on another counter-intuitive insight: past a certain point, adding more batteries will actually *decrease* the drone's flight time rather than increase it. That means that for any given drone there is an optimal battery weight that yields the maximum flight time. How can that be?

## Why more batteries can mean less flight time

The reason a drone's flight time starts to shrink past a certain point as we add batteries comes down to this: the faster a drone's propellers spin, the less efficiently the drone generates lift. In other words, keeping one kilogram of drone in the air for one minute requires more energy the faster the propellers have to spin.

## How a propeller generates lift

How does a propeller generate lift? Simplifying a bit: a propeller pushes air downward. Every action has a reaction, so this pushes the drone upward against gravity and keeps it in the air.

![A propeller pushes air down to generate lift up](/img/drones/thread3/propeller-lift.png)

## How much air is pushed down

How much air does the propeller push per unit of time? A cylinder of air, with a volume equal to the propeller's area times the air's velocity — and a mass equal to that volume times the air's density (if we simplify).

![The mass of air pushed down equals density times area times velocity](/img/drones/thread3/air-mass.png)

## How much lift is produced

How much lift does the propeller generate? The lift force acting on the drone — from Newton's second law — is proportional to the mass of air times its velocity. And since the mass of air is itself proportional to the velocity, the lift comes out proportional to the air velocity *squared*.

![Lift is proportional to the air velocity squared](/img/drones/thread3/lift-formula.png)

## How much power is consumed

How much energy is required per unit of time to generate that lift? From the most basic kinetic energy formula — energy is half the mass times the velocity squared — the required power comes out proportional to the air velocity *cubed*.

![Power consumed is proportional to the air velocity cubed](/img/drones/thread3/power-formula.png)

## Efficiency drops as the propeller works harder

From here you can immediately see that efficiency drops as the propeller has to generate more lift. For example, if the velocity of the air the propeller pushes is doubled, the lift grows by a factor of 4 — but the energy required grows by a factor of 8.

![Doubling the air velocity multiplies lift by 4 but power by 8](/img/drones/thread3/power-vs-lift.png)

## The optimal battery weight

If we take this insight into account and now calculate the flight time as a function of battery weight, we get that the optimal flight time is reached when the battery weight is twice the weight of the drone without the battery.

![Flight time against the battery-to-frame mass ratio, with the optimal choice marked](/img/drones/thread3/optimal-battery-weight.png)

That said, because the graph becomes very flat well before that point, from around where the battery weight is 60–70% of the weight of the drone without the batteries the flight time barely grows anymore. That's why this is a very common operating point in practice.

## What's next

In the next part of the thread we'll talk about what *can* still be done to increase the flight time of drones.

---

*This post is a translation of [a thread I originally posted on X](https://x.com/itamarwe/status/1867685047215472954).*
