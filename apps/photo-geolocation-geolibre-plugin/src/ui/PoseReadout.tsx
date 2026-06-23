import { useStore } from '../store';
import { ESTIMATORS } from '../pose/registry.js';

/**
 * Estimated camera location per enabled estimator. There's no ground truth for
 * a real uploaded photo, so we show the solved lat/lon (+ heading, elevation)
 * rather than an error — matching the original tool's PosePanel.
 */
export default function PoseReadout() {
  const estimates = useStore((s) => s.estimates);
  const enabled = useStore((s) => s.enabledEstimators);
  const toggleEstimator = useStore((s) => s.toggleEstimator);
  const obsCount = useStore(
    (s) => s.anchors.filter((a) => a.photoPixel && a.mapPoint).length,
  );

  return (
    <div className="gp-pose">
      <div className="gp-pose__head">
        <span>Pose estimation</span>
        <span className="gp-count">{obsCount} obs</span>
      </div>
      {(ESTIMATORS as Array<{ id: string; name: string; minAnchors: number; color: string }>).map(
        (e) => {
          const on = enabled.has(e.id);
          const est = estimates[e.id];
          const notEnough = obsCount < e.minAnchors;
          return (
            <div key={e.id} className="gp-pose__row" onClick={() => toggleEstimator(e.id)}>
              <input type="checkbox" checked={on} readOnly style={{ accentColor: e.color }} />
              <span className="gp-pose__name" style={{ color: on ? e.color : undefined }}>
                {e.name}
              </span>
              <span className="gp-pose__val">
                {!on
                  ? '—'
                  : notEnough
                    ? `min ${e.minAnchors}`
                    : est
                      ? `${est.lat.toFixed(5)}, ${est.lon.toFixed(5)}` +
                        (Number.isFinite(est.headingDeg)
                          ? ` · ${((est.headingDeg % 360) + 360) % 360 | 0}°`
                          : '') +
                        (Number.isFinite(est.elevation) ? ` · ${Math.round(est.elevation)} m` : '')
                      : 'no solution'}
              </span>
            </div>
          );
        },
      )}
    </div>
  );
}
