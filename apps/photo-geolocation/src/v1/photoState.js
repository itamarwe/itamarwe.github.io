/**
 * Photo state — the photo is what the pose pipeline downstream is allowed
 * to see.
 *
 *   _capture   (hidden from algorithms)
 *     Scene-generation metadata used by PhotoView to render the "photo" —
 *     frozen camera params, scene seed, building count. Nothing in pose/
 *     imports this.
 *
 *   image      (public photo attributes — the rectangle of pixels)
 *     width, height in pixels. This is the only part estimators may read,
 *     and they don't even need the actual pixels — just the dimensions so
 *     they know where the principal point sits (assumed = width/2, 0).
 */
export const photoState = {
  _capture: {
    seed: 42,
    count: 18,
    camera: { px: 0, py: 45, pz: 90, dx: 0, dy: -0.45, dz: -0.89, fov: 60 },
  },
  image: {
    width:  900,
    height: 600,
  },
}
