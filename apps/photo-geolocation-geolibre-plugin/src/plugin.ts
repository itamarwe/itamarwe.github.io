import { createRoot, type Root } from 'react-dom/client';
import { createElement } from 'react';
import type { Map as MlMap } from 'maplibre-gl';
import type { GeoLibreAppAPI, GeoLibrePlugin } from './geolibre';
import { resolveWorldPoint } from './resolver';
import { attachAnchorMarkers } from './map/anchorMarkers';
import { useStore } from './store';
import Panel from './ui/Panel';

const PANEL_ID = 'photo-geolocation';

let root: Root | null = null;
let unregisterPanel: (() => void) | null = null;
let unregisterMenu: (() => void) | null = null;
let detachMarkers: (() => void) | null = null;
let mapClickHandler: ((e: { lngLat: { lng: number; lat: number } }) => void) | null = null;
let boundMap: MlMap | null = null;

/**
 * Photo Geolocation — solve a camera's position from a single photo by matching
 * points between the image and the map (Perspective-n-Point).
 *
 * This plugin owns ONLY the PnP solver and the anchor UX. All geodata comes
 * from GeoLibre: clicks read lng/lat from the host map and height from the DSM
 * GeoLibre has loaded (see resolver.ts). No buildings/terrain logic here.
 */
export const photoGeolocationPlugin: GeoLibrePlugin = {
  id: PANEL_ID,
  name: 'Photo Geolocation',
  version: '0.1.0',

  activate(app: GeoLibreAppAPI) {
    const map = app.getMap() as unknown as MlMap | null;
    if (!map) return false;
    boundMap = map;

    // Local ENU frame origin = map centre at activation. Stable and generic;
    // anchors are stored relative to it and the solver works in metres here.
    const c = map.getCenter();
    useStore.getState().setOrigin({ lat: c.lat, lon: c.lng });

    // Right-sidebar panel — mount our own React root into GeoLibre's container.
    unregisterPanel = app.registerRightPanel({
      id: PANEL_ID,
      title: 'Photo Geolocation',
      dock: 'right-of-layers',
      defaultWidth: 360,
      render(container: HTMLElement) {
        root = createRoot(container);
        root.render(createElement(Panel));
        return () => {
          root?.unmount();
          root = null;
        };
      },
    });

    // Toolbar entry to (re)open the panel.
    unregisterMenu = app.registerToolbarMenu({
      id: `${PANEL_ID}-menu`,
      label: 'Photo Geolocation',
      items: [{ id: `${PANEL_ID}-open`, label: 'Open panel', onSelect: () => app.openRightPanel(PANEL_ID) }],
    });

    // Map clicks set the world point of the anchor armed in the panel.
    mapClickHandler = (e) => {
      const { placingMapPointFor, origin } = useStore.getState();
      if (placingMapPointFor == null || !origin) return;
      const wp = resolveWorldPoint(map as never, e.lngLat, origin);
      useStore.getState().setAnchorMapPoint(placingMapPointFor, wp);
    };
    map.on('click', mapClickHandler);

    detachMarkers = attachAnchorMarkers(map);

    app.openRightPanel(PANEL_ID);
  },

  deactivate(_app: GeoLibreAppAPI) {
    if (boundMap && mapClickHandler) boundMap.off('click', mapClickHandler);
    mapClickHandler = null;
    detachMarkers?.();
    detachMarkers = null;
    unregisterMenu?.();
    unregisterMenu = null;
    unregisterPanel?.();
    unregisterPanel = null;
    root?.unmount();
    root = null;
    boundMap = null;
  },
};

export default photoGeolocationPlugin;
