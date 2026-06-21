# Solar-system post — figure source

The Python behind the social-share card for the post
[*How I Built a 3D Simulation to Teach My Kids About Day, Night, and
Seasons*](../../content/posts/2025-03-07-teaching-day-night-seasons-3d-simulation.md).

The post itself is built around videos of the live
[Three.js simulation](https://github.com/itamarwe/solar-system-simulation)
([try it](../../public/solar-system/)); this folder only generates the
1200×630 OpenGraph/Twitter card.

## Layout

```
sim/
  social.py   The 1200×630 social card: a glowing Sun lighting a tilted Earth
              with a day/night terminator and a faint orbit arc, over the post
              title. Pure-black background to match the site.
```

`social.py` writes straight into the post's image folder,
`public/img/solar-system/social.png` (path resolved relative to the script).

The Earth here is an **illustrative diagram**, not a frame from the actual
simulation: the disk is shaded by `dot(surface normal, sun direction)` so the
lit hemisphere faces the Sun and the night side falls into shadow, with a warm
terminator rim and a 23.5° tilted rotation axis. The continents are low-frequency
noise, just enough to read as a globe.

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install numpy matplotlib
python sim/social.py    # writes public/img/solar-system/social.png
```
