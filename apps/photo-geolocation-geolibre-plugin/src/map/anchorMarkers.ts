import { Marker } from 'maplibre-gl';
import type { Map as MlMap } from 'maplibre-gl';
import { localToLl } from '../geo';
import { useStore } from '../store';

/**
 * Reflects placed anchors onto the host MapLibre map as colored markers.
 * We use plain MapLibre Markers (DOM pins) rather than a user-facing GeoJSON
 * layer so they don't clutter GeoLibre's layer list and are trivial to clear.
 * Subscribes to the store and re-syncs on every anchor change.
 */
export function attachAnchorMarkers(map: MlMap): () => void {
  const markers = new Map<number, Marker>();

  const sync = () => {
    const { anchors, origin } = useStore.getState();
    const seen = new Set<number>();
    if (origin) {
      for (const a of anchors) {
        if (!a.mapPoint) continue;
        seen.add(a.id);
        const { lat, lon } = localToLl(a.mapPoint.x, a.mapPoint.z, origin);
        let m = markers.get(a.id);
        if (!m) {
          m = new Marker({ color: a.color }).setLngLat([lon, lat]).addTo(map);
          markers.set(a.id, m);
        } else {
          m.setLngLat([lon, lat]);
        }
      }
    }
    // remove markers for anchors that no longer have a map point
    for (const [id, m] of markers) {
      if (!seen.has(id)) {
        m.remove();
        markers.delete(id);
      }
    }
  };

  const unsub = useStore.subscribe(sync);
  sync();

  return () => {
    unsub();
    for (const m of markers.values()) m.remove();
    markers.clear();
  };
}
