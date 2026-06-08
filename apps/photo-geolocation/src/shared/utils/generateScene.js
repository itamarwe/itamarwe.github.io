/**
 * Deterministic seeded LCG random number generator.
 * Returns numbers in [0, 1).
 */
function makePrng(seed) {
  let s = (seed ^ 0x12345678) >>> 0
  return () => {
    s = Math.imul(s, 1664525) + 1013904223
    s = s >>> 0
    return s / 0x100000000
  }
}

/** AABB overlap check (top-down) with a minimum gap. */
function overlaps(a, b, pad = 1.5) {
  return (
    Math.abs(a.x - b.x) < (a.width  + b.width)  / 2 + pad &&
    Math.abs(a.z - b.z) < (a.depth  + b.depth)  / 2 + pad
  )
}

/**
 * Generate a city-block scene with box buildings.
 * Uses rejection sampling so building footprints never overlap.
 *
 * @param {number} seed  - integer seed for reproducibility
 * @param {number} count - desired number of buildings
 */
export function generateScene(seed = 42, count = 18) {
  const rand = makePrng(seed)
  const buildings = []
  const MAX_TRIES = 200   // per building

  for (let i = 0; i < count; i++) {
    let placed = null

    for (let tries = 0; tries < MAX_TRIES; tries++) {
      const angle  = rand() * Math.PI * 2
      const radius = 10 + rand() * 40

      const candidate = {
        id:     i,
        x:      Math.cos(angle) * radius + (rand() - 0.5) * 12,
        z:      Math.sin(angle) * radius + (rand() - 0.5) * 12,
        width:  rand() * 10 + 4,
        depth:  rand() * 10 + 4,
        height: rand() * 28 + 5,
        colorH: Math.floor(rand() * 40 + 20),  // warm hue
      }

      if (!buildings.some((b) => overlaps(candidate, b))) {
        placed = candidate
        break
      }
    }

    if (placed) buildings.push(placed)
    // If we exhausted tries, skip — the scene may end up with fewer buildings than requested,
    // which is fine and signals the space is full.
  }

  return buildings
}
