import { estimateFullPnP, estimateFullPnPRansac } from './algorithms'

export const ESTIMATORS = [
  {
    id: 'full-pnp',
    name: 'Full PnP',
    blurb: '6-DOF: x, z, camY, heading, pitch, f',
    color: '#22c55e',
    shape: 'triangle',
    minAnchors: 4,
    hasHeading: true,
    hasFov: true,
    fn: estimateFullPnP,
  },
  {
    id: 'full-pnp-ransac',
    name: 'Full PnP RANSAC',
    blurb: 'Robust 6-DOF with outlier rejection',
    color: '#f59e0b',
    shape: 'circle',
    minAnchors: 5,
    hasHeading: true,
    hasFov: true,
    fn: estimateFullPnPRansac,
  },
]
