import PhotoPane from './PhotoPane';
import AnchorList from './AnchorList';
import PoseReadout from './PoseReadout';
import './panel.css';

/**
 * Root of the right-sidebar panel. Mounted into the bare container GeoLibre
 * hands us (see plugin.ts → registerRightPanel.render). All the anchor UX
 * lives here; the map side is wired by plugin.ts against the host map.
 */
export default function Panel() {
  return (
    <div className="gp-panel">
      <PhotoPane />
      <AnchorList />
      <PoseReadout />
    </div>
  );
}
