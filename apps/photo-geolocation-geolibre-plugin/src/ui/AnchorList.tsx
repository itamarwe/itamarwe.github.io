import { useStore } from '../store';

/**
 * The anchor list: add anchors, select the active one, arm a map click to set
 * its world point, and see at a glance whether each side (photo / map) is set.
 */
export default function AnchorList() {
  const anchors = useStore((s) => s.anchors);
  const activeAnchorId = useStore((s) => s.activeAnchorId);
  const placingMapPointFor = useStore((s) => s.placingMapPointFor);
  const photoUrl = useStore((s) => s.photoUrl);
  const addAnchor = useStore((s) => s.addAnchor);
  const removeAnchor = useStore((s) => s.removeAnchor);
  const setActiveAnchor = useStore((s) => s.setActiveAnchor);
  const armMapPlacement = useStore((s) => s.armMapPlacement);

  return (
    <div className="gp-anchors">
      <div className="gp-anchors__head">
        <span>Anchors</span>
        <button className="gp-btn gp-btn--sm" disabled={!photoUrl} onClick={() => addAnchor()}>
          + Add
        </button>
      </div>

      {anchors.length === 0 && (
        <p className="gp-hint">
          Add an anchor, then click the same physical point in the photo and on the map.
        </p>
      )}

      <ul className="gp-anchors__list">
        {anchors.map((a) => {
          const arming = placingMapPointFor === a.id;
          return (
            <li
              key={a.id}
              className={`gp-anchor ${a.id === activeAnchorId ? 'gp-anchor--active' : ''}`}
              onClick={() => setActiveAnchor(a.id)}
            >
              <span className="gp-dot gp-dot--inline" style={{ background: a.color }} />
              <span className="gp-anchor__id">#{a.id}</span>
              <span className={`gp-tag ${a.photoPixel ? 'gp-tag--on' : ''}`}>photo</span>
              <span className={`gp-tag ${a.mapPoint ? 'gp-tag--on' : ''}`}>map</span>
              <button
                className={`gp-btn gp-btn--sm ${arming ? 'gp-btn--armed' : ''}`}
                onClick={(e) => {
                  e.stopPropagation();
                  armMapPlacement(arming ? null : a.id);
                }}
              >
                {arming ? 'Click map…' : 'Set on map'}
              </button>
              <button
                className="gp-btn gp-btn--sm gp-btn--ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  removeAnchor(a.id);
                }}
              >
                ✕
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
