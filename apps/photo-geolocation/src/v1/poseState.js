/**
 * Mutable shared object for pose-estimation results.
 * Written by Map2D's per-frame draw loop, read by PosePanel's rAF display loop.
 *
 *   estimates: {
 *     [algoId]: {
 *       px, pz, heading,    // estimated pose (heading may be NaN for non-heading algos)
 *       fov,                // estimated horizontal FOV in degrees (Joint GN only; NaN otherwise)
 *       posErr,             // distance from actual camera in XZ plane
 *       headingErr,         // |wrap(estHeading − actualHeading)|
 *       fovErr,             // |estFov − actualFov| in degrees (Joint GN only)
 *     } | null
 *   }
 */
export const poseState = {
  estimates: {},
}
