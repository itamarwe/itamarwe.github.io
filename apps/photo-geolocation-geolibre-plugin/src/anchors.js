// Distinct, perceptually-separated colors for anchor markers.
export const ANCHOR_COLORS = [
  '#ff3b30', // red
  '#ff9500', // orange
  '#ffcc00', // yellow
  '#34c759', // green
  '#00c7be', // teal
  '#007aff', // blue
  '#af52de', // purple
  '#ff2d92', // pink
  '#5856d6', // indigo
  '#a2845e', // brown
]

/** Pick the first unused colour from the palette; wrap around if all taken. */
export function nextAnchorColor(anchors, nextId) {
  const used = new Set(anchors.map((a) => a.color))
  const free = ANCHOR_COLORS.find((c) => !used.has(c))
  return free ?? ANCHOR_COLORS[(nextId - 1) % ANCHOR_COLORS.length]
}
