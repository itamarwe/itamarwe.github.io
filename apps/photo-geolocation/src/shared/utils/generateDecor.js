/**
 * Generate trees + rooftop people deterministically from a seed, given the
 * building list so we can avoid tree/building overlap and place people ON TOP
 * of a subset of buildings. Returns { trees: [...], people: [...] }.
 *
 * trees:  random heights (3–7u), scattered around ground plane avoiding buildings
 * people: all the same height (1.8u, tracked implicitly by the Person mesh);
 *         standing centred on top of a random subset of buildings
 */
function makePrng(seed) {
  let s = ((seed ^ 0x9e3779b1) >>> 0) || 1
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0
    return s / 0x100000000
  }
}

function overlapsAABB(a, b, pad = 0.5) {
  return (
    Math.abs(a.x - b.x) < (a.width  + b.width)  / 2 + pad &&
    Math.abs(a.z - b.z) < (a.depth  + b.depth)  / 2 + pad
  )
}

export function generateDecor(seed, buildings, opts = {}) {
  const treeCount = opts.treeCount ?? 32
  const peopleFraction = opts.peopleFraction ?? 0.4
  const rand = makePrng(seed * 31 + 7)

  // Trees ─── use rejection against buildings (as AABBs) and each other.
  const trees = []
  const treeAABBs = []
  let guard = 0
  while (trees.length < treeCount && guard++ < treeCount * 20) {
    const r = 6 + rand() * 55
    const ang = rand() * Math.PI * 2
    const x = Math.cos(ang) * r
    const z = Math.sin(ang) * r
    const trunkR = 0.3 + rand() * 0.3
    const candidate = { x, z, width: trunkR * 2, depth: trunkR * 2 }
    let clash = false
    for (const b of buildings) { if (overlapsAABB(candidate, b, 1.2)) { clash = true; break } }
    if (clash) continue
    for (const t of treeAABBs) { if (overlapsAABB(candidate, t, 1.0)) { clash = true; break } }
    if (clash) continue
    treeAABBs.push(candidate)
    trees.push({
      id: `t${trees.length}`,
      position: [x, 0, z],
      height: 3 + rand() * 4,
    })
  }

  // People ─── on top of a random subset of taller buildings.
  const people = []
  const tall = buildings.filter((b) => b.height >= 10)
  tall.forEach((b, idx) => {
    if (rand() < peopleFraction) {
      people.push({
        id: `p${idx}`,
        // Person's feet sit at y = b.height (rooftop). Use slight random offset
        // within the rooftop footprint so they don't always stand dead centre.
        position: [
          b.x + (rand() - 0.5) * Math.min(b.width - 1, 3),
          b.height,
          b.z + (rand() - 0.5) * Math.min(b.depth - 1, 3),
        ],
      })
    }
  })

  return { trees, people }
}
