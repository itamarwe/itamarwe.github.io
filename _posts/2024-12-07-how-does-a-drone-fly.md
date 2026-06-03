---
layout: post
title: "How Does a Drone Fly?"
comments: true
date: 2024-12-07
categories: drones
---

During my reserve duty up north, I was surprised to discover that a lot of people don't understand the principles behind how a drone flies — even people who are experienced at flying them.

If you've ever wondered how this strange-looking aircraft actually manages to fly, this post is for you.

![A soldier holding a quadcopter](/img/drones/thread1/tweet1_photo1.jpg)

In recent years, drones have become more and more popular. If a decade ago a drone looked like something out of a science fiction movie, today every child knows how to recognize one, and many have already flown one themselves. Drones have changed, and are still changing, the battlefield — first in the Russia-Ukraine war, but also here in Israel, especially since October 7.

But how does a drone actually fly? That part is much less widely understood.

![Two small drones flying through a valley](/img/drones/thread1/1865455332018815245-1.jpg)

## Creating lift

For an aircraft to stay in the air, it has to create a force that pulls it upward against gravity. That force is called lift. A wing is an invention inspired by nature: it uses the speed of the wing, and the flow of air around it, to create a pressure difference between the upper and lower sides of the wing. The air below the wing pushes it upward more than the air above the wing pushes it downward, and that difference is lift.

![Airflow over an airplane wing creates lift](/img/drones/thread1/1865455334254321892-1.jpg)

But a wing has to move through the air to create lift. What do you do when you want to build an aircraft that can hover in place, like a drone? You use a rotating wing — a rotor. That way, the wing moves quickly relative to the air while still letting the aircraft stay in place.

So far that sounds simple, but the plot thickens.

![A fan with rotating blades](/img/drones/thread1/1865455336678699195-1.jpg)

## The spin problem

We all know Newton's third law: for every action there is an equal and opposite reaction. When the aircraft applies force to spin the rotor clockwise, the rotor applies force back on the aircraft and spins it counter-clockwise — like children on a merry-go-round turning the wheel one way so they rotate the other way.

![Children spinning a playground merry-go-round](/img/drones/thread1/1865455338809364587-1.jpg)

The problem is that this would make the aircraft spin constantly, which would make it unusable.

So what's the solution?

In helicopters, for example, the common solution is the tail rotor: it applies a force that opposes the spin created by the main rotor and stabilizes the helicopter.

![A helicopter using a tail rotor for stabilization](/img/drones/thread1/1865455341078503744-1.jpg)

Another solution used in helicopters is to use two overhead rotors that spin in opposite directions. One rotor creates a force that spins the helicopter in one direction, the other creates a force that spins it in the other direction, and the forces cancel each other out. That makes it possible to control both spin, or yaw, and lift.

![A tandem-rotor helicopter with two counter-rotating rotors](/img/drones/thread1/1865455344396247396-1.jpg)

But drones don't just hover and yaw — they also know how to tilt forward and backward, and left and right.

How do they do that?

They use four or more motors.

![Two people holding a large quadcopter with four motors](/img/drones/thread1/1865455346480751063-1.png)

## Lift without spin

If we look at the image below, each pair of adjacent rotors spins in the opposite direction to the other, so each one cancels out the rotation that the other creates. That gives you two pairs of rotors producing lift without making the drone spin.

![Lift: adjacent rotors spin clockwise and counter-clockwise](/img/drones/thread1/lift-rotor-directions.png)
![Lift: upward thrust from the rotors](/img/drones/thread1/lift-thrust.png)

## Rolling sideways

To roll to the right, the drone slows down the spin rate of the two rotors on the right side relative to the rotors on the left. Because the rotors spin in opposing directions, this doesn't make the drone spin — it only reduces the lift produced on the right side, so the left side rises and the right side drops.

![Roll right: speed up left rotors, slow down right rotors](/img/drones/thread1/roll-right-rotor-speeds.png)
![Roll right: more lift on the left, less lift on the right](/img/drones/thread1/roll-right-tilt.png)

## Tilting forward

In the same way, to tilt itself forward the drone slightly slows down the spin rate of the two front rotors relative to the rear rotors.

## Yawing in place

And what about yaw — rotating in place? Here the drone takes advantage of the very phenomenon we started with: the spin.

To yaw counter-clockwise, the drone slightly slows down the rotors that spin counter-clockwise. This way, the rotors spinning clockwise rotate the drone counter-clockwise more strongly than the counter-clockwise rotors push the drone clockwise.

![Yaw: clockwise and counter-clockwise rotor pairs](/img/drones/thread1/yaw-rotor-directions.png)

## Why this matters

The beauty of drone technology is that it's very simple — apart from the spinning rotors, there are no moving parts at all. That makes drones very simple, cheap, and reliable.

![A quadcopter in flight](/img/drones/thread1/tweet6_photo1.jpg)

That's it. That's the simple explanation of how drones fly.

In upcoming posts I'll write about why drones can't stay in the air for hours, the technological revolutions that made building drones possible, the challenges that still exist in integrating drones into the modern battlefield, and why some drones have wings.

![A fixed-wing drone](/img/drones/thread1/tweet7_photo1.jpg)

*Next in this series: [Why Can't Drones Fly for More Than 40 Minutes?](/drones/2024/12/11/why-drones-cant-fly-more-than-40-minutes.html).*

---

*This post is a translation of [a thread I originally posted on X](https://x.com/itamarwe/status/1865455329934197124).*
