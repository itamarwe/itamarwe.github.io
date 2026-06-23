/**
 * Minimal stand-ins for the GeoLibre host types this plugin depends on.
 *
 * In a real build against the GeoLibre plugin template these come from the
 * host package (e.g. `@geolibre/core` / the plugin SDK) — replace this file's
 * imports with the real ones there. They are reproduced here (a strict subset)
 * so the plugin typechecks in isolation and the contract it relies on is
 * explicit and small. Verified against GeoLibre's
 * `packages/plugins/src/types.ts`.
 */

import type { Marker } from 'maplibre-gl';

export type { Marker };

export type GeoLibreMapControlPosition =
  | 'top-left'
  | 'top-right'
  | 'bottom-left'
  | 'bottom-right';

export type GeoLibreRightPanelDock =
  | 'left-of-layers'
  | 'right-of-layers'
  | 'left-of-style'
  | 'right-of-style';

export interface GeoLibreRightPanelRegistration {
  id: string;
  title: string;
  dock?: GeoLibreRightPanelDock;
  icon?: string;
  defaultWidth?: number;
  /** Receives an empty container; may return a cleanup fn run on close. */
  render: (container: HTMLElement) => void | (() => void);
  onOpen?: () => void;
  onCollapse?: () => void;
  onClose?: () => void;
}

export interface GeoLibreToolbarMenu {
  id: string;
  label: string;
  icon?: string;
  items: Array<{ id: string; label: string; icon?: string; onSelect: () => void }>;
}

/** The MapLibre map surface we use (subset of maplibre-gl's Map). */
export interface MapLibreMap {
  getCenter(): { lng: number; lat: number };
  getTerrain?(): unknown | null;
  queryTerrainElevation?(lngLat: { lng: number; lat: number }): number | null;
  on(type: 'click', listener: (e: { lngLat: { lng: number; lat: number } }) => void): void;
  off(type: 'click', listener: (e: { lngLat: { lng: number; lat: number } }) => void): void;
  getCanvas(): HTMLCanvasElement;
}

/** Subset of GeoLibreAppAPI we call. */
export interface GeoLibreAppAPI {
  getMap(): MapLibreMap | null;
  registerRightPanel(panel: GeoLibreRightPanelRegistration): () => void;
  unregisterRightPanel(id: string): void;
  openRightPanel(id: string): boolean;
  registerToolbarMenu(menu: GeoLibreToolbarMenu): () => void;
}

export interface GeoLibrePlugin {
  id: string;
  name: string;
  version: string;
  activeByDefault?: boolean;
  activate: (app: GeoLibreAppAPI) => boolean | void | Promise<boolean | void>;
  deactivate: (app: GeoLibreAppAPI) => void;
  getProjectState?: () => unknown;
  applyProjectState?: (app: GeoLibreAppAPI, state: unknown) => boolean | void;
}
