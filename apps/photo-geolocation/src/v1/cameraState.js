/**
 * Mutable shared object for the 3D camera — ONLY used while the photo is being
 * edited (scene-building phase). Updated each frame by PhotoView when in edit
 * mode. Never touched by pose estimators.
 */
export const cameraState = {
  px: 0, py: 45, pz: 90,
  dx: 0, dy: -0.45, dz: -0.89,
  fov: 60,
}
