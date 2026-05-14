---
layout: post
title: "Why Can't Drones Fly for More Than 40 Minutes? (Part 3)"
comments: true
date: 2024-12-18
categories: drones
---

*Previously in this series: [Why Can't Drones Fly for More Than 40 Minutes? (Part 2)](/drones/2024/12/13/why-drones-cant-fly-more-than-40-minutes-part-2.html).*

In this final part of the series we'll talk about what *can* still be done to increase the flight time of drones.

In the previous parts we talked about a few counter-intuitive principles that determine the flight time of drones.

![Flight time against the battery-to-frame mass ratio, with the optimal choice marked](/img/drones/thread4/flight-time-recap.png)

The first counter-intuitive principle is that we can't increase a drone's flight time just by adding more batteries. The more batteries we add, the more energy the drone also has to spend just to carry those batteries — and there is a maximum flight time that can't be exceeded no matter how many batteries we add.

The second counter-intuitive principle is that the more lift a drone has to produce, the lower the efficiency of its propellers — so it needs more energy per unit of weight to keep itself in the air. Because of this, past a certain point, adding more batteries actually starts to *decrease* the flight time rather than increase it.

The maximum flight time is reached when the battery weight is twice the weight of the drone itself, but as you keep adding batteries the gain in flight time becomes negligible, the drone gets more expensive, and it becomes harder to maneuver. So as a rule of thumb, the optimal battery weight is around 0.6–0.7 of the drone's weight.

## So what *can* we do to increase flight time?

We saw that there are two main factors that determine a drone's flight time: the density of the energy source — how much energy is stored per unit of weight — and the efficiency of the drone — how much energy is needed to keep the drone in the air.

So to increase a drone's flight time we can do two things: use a denser energy source, and improve the drone's efficiency. Let's dive into both.

## A denser energy source

Every energy source has a property called specific energy. The idea is very simple — how much energy is stored per unit of weight. If we use a "denser" energy source, we can store more energy in the same battery weight and extend the flight time. If we had, for example, an energy source 10 times denser, we could swap in that battery and get 10 times the flight time.

The energy density of fuel is roughly 50–100 times greater than the energy density of batteries — and that difference can explain a large part of the gap between the limited flight time of drones and the flight time of fuel-powered aircraft.

![A table of energy densities by battery type, from lead acid up to lithium-air and gasoline](/img/drones/thread4/energy-density-table.png)

Advanced batteries at various stages of development could significantly extend the flight time of drones. Especially promising are metal-air batteries — which use the oxygen in the air, and are therefore lighter relative to the energy they store.

![A diagram of a metal-air battery: metal anode, electrolyte, cathode, and air](/img/drones/thread4/metal-air-battery.png)

## Improving efficiency

What else can we do? Improve the electrical and aerodynamic efficiency of the aircraft — for example, more efficient motors and more efficient propellers.

![Simulated airflow around a quadcopter from several angles](/img/drones/thread4/motor-propeller-efficiency.png)

Enlarging the propellers, or using a larger number of propellers, can also increase aerodynamic efficiency — because if you push a larger amount of air, you need to bring it to a lower speed, and the efficiency of generating lift is then higher, as we saw earlier.

![A multirotor aircraft with a large number of propellers](/img/drones/thread4/more-propellers.jpg)

Here too there's a trade-off. The more propellers there are, the more motors there are, and the aircraft becomes more expensive. And if you enlarge the propellers, maneuverability suffers — it's harder to change the speed of heavier propellers — and larger propellers are also less safe and more complex to use inside buildings, in dense vegetation, or close to the ground.

Because wings generate lift more efficiently than propellers, you can find drones combined with a fixed wing to increase payload capacity as well as flight time and range. But this solution turns the drone into an aircraft with vertical takeoff and landing capabilities, relevant only for missions where you don't need to hover and can simply fly.

![Fixed-wing drones with vertical-takeoff rotors](/img/drones/thread4/fixed-wing-drone.jpg)

That's it. The flight-time limit of drones bothered me for a long time, and we had to dive into several counter-intuitive principles to understand it. I hope I managed to make the problem accessible.

---

*This post is a translation of a thread I originally posted on X.*
