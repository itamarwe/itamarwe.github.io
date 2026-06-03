---
layout: post
title: "Why Can't Drones Fly for More Than 40 Minutes?"
comments: true
date: 2024-12-11
categories: drones
---

*Previously in this series: [How Does a Drone Fly?](/drones/2024/12/07/how-does-a-drone-fly.html).*

Why is the flight time of drones so limited, and what can be done about it?

![A drone in flight, with a controller and a watch](/img/drones/thread2/tweet1_photo1.jpg)

One of the biggest limitations of drones is their flight time. Almost no matter how you look at it, the maximum flight time of most drones stays around 30–40 minutes, which sharply limits their range and the missions they can perform.

![Soldiers operating a drone in a forest](/img/drones/thread2/drone-operators-forest.jpg)

The importance of flight time is clear: the longer a drone can stay in the air, the greater its operating range, the better it can hold an area continuously, the more efficiently it can use its flight time, and the less often it has to go through risky takeoffs and landings.

![A drone flying while a person controls it from the ground](/img/drones/thread2/drone-flight-time-range.jpg)

It turns out that the flight-time limit comes from a universal constraint shared by every aircraft, but it shows up especially strongly in drones. Hidden behind it are a few counter-intuitive principles.

![Many different drones flying over a landscape](/img/drones/thread2/drone-variety.jpg)

## A first thought experiment

Let's start with a short thought experiment. Imagine a fictional aircraft that weighs 1 kg and is made entirely of battery. It has no unnecessary weight at all. Now imagine that it can use the energy in that battery to generate enough lift to hold the 1 kg aircraft in the air for one minute.

How could we extend its flight time?

![An ideal 1 kg aircraft made entirely of battery flying for one minute](/img/drones/thread2/ideal-one-kg-one-minute.jpg)

The obvious, intuitive answer is to add another battery.

Suppose we add another 1 kg battery. What will the flight time be?

![A 2 kg version of the ideal aircraft with a question mark over the flight time](/img/drones/thread2/ideal-two-kg-question.jpg)

On one hand, the aircraft now has twice as much energy. On the other hand, it also has to generate lift for twice as much weight, so its energy consumption rises by roughly a factor of two. Overall, the flight time does not increase.

You can also think of it as the equivalent of two of the previous aircraft tied together, which makes it obvious that the flight time should stay the same.

![A 2 kg aircraft is equivalent to two 1 kg aircraft tied together](/img/drones/thread2/doubled-battery-same-flight-time.jpg)

## Real aircraft are worse than the ideal model

To reason about the limits of flight time, it helps to imagine an *ideal aircraft* — a thought experiment in which the aircraft is made of nothing but battery.

Any real aircraft that actually gets built won't be made entirely of battery. It will have a body, motors, propellers, electronics, and so on — and therefore it will fly for less time than the ideal aircraft we imagined. The energy stored in the battery has to generate lift not just for the weight of the battery, but for all that additional weight too.

![A rotor generating lift to hold up a 1 kg weight for 30 seconds](/img/drones/thread2/tweet2_photo1.jpg)

## Adding batteries has a ceiling

If we take a battery that is very small compared to the weight of the aircraft, it's obvious that the flight time will be very short. The more batteries we add, the more the weight of the aircraft itself becomes negligible compared to the weight of the battery — and we get closer and closer to the ideal model.

But here's the catch: the maximum flight time we can ever reach is, at best, the flight time of the ideal aircraft — the one that's all battery.

![Flight time rises with the battery-to-frame mass ratio but plateaus at the ideal aircraft's flight time](/img/drones/thread2/tweet3_photo1.jpg)

This thought experiment shows us why there is a flight-time limit — for any aircraft — that can't be beaten simply by adding more batteries.

But reality is even more complex than that. Past a certain point, adding more batteries doesn't grow the flight time at all — it actually *decreases* it. That means that for any given drone there is an optimal battery weight that yields the maximum flight time. How can that be?

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

## So what *can* we do to increase flight time?

In the final part of the thread, we can turn from the limits themselves to the things that can actually move them.

![A drone balancing lift and weight for one minute](/img/drones/thread4/lift-weight-recap.jpg)

There are two main factors that determine a drone's flight time: the density of the energy source — how much energy is stored per unit of weight — and the efficiency of the drone — how much energy is needed to keep the drone in the air.

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

*This post is a translation of a thread I originally posted on X, in three parts ([part 1](https://x.com/itamarwe/status/1866933141308576124), [part 2](https://x.com/itamarwe/status/1867685047215472954), [part 3](https://x.com/itamarwe/status/1874135174163919048)).*
