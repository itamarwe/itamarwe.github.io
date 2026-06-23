import { create } from 'zustand';
// plain-JS modules ported verbatim from the original tool (typed as any)
import { buildObservations } from './pose/algorithms.js';
import { ESTIMATORS } from './pose/registry.js';
import { nextAnchorColor } from './anchors.js';
import { localToLl, type Origin } from './geo';
import type { WorldPoint } from './resolver';

export interface PhotoPixel {
  x: number;
  y: number;
}
export interface Anchor {
  id: number;
  color: string;
  photoPixel: PhotoPixel | null;
  mapPoint: WorldPoint | null;
}
export interface Estimate {
  lat: number;
  lon: number;
  headingDeg: number;
  elevation: number;
}

interface State {
  // photo
  photoUrl: string | null;
  photoName: string | null;
  image: { width: number; height: number };
  // anchors
  anchors: Anchor[];
  activeAnchorId: number | null;
  nextAnchorId: number;
  /** Anchor id armed to receive the next map click, or null. */
  placingMapPointFor: number | null;
  // map frame
  origin: Origin | null;
  // estimators
  enabledEstimators: Set<string>;
  estimates: Record<string, Estimate | null>;

  setPhoto(url: string, width: number, height: number, name?: string): void;
  clearPhoto(): void;
  setOrigin(origin: Origin): void;
  addAnchor(): void;
  removeAnchor(id: number): void;
  setActiveAnchor(id: number): void;
  armMapPlacement(id: number | null): void;
  setAnchorPhotoPixel(id: number, photoPixel: PhotoPixel): void;
  setAnchorMapPoint(id: number, mapPoint: WorldPoint): void;
  toggleEstimator(id: string): void;
  recompute(): void;
}

function makeAnchor(nextId: number, anchors: Anchor[]): Anchor {
  return { id: nextId, color: nextAnchorColor(anchors, nextId), photoPixel: null, mapPoint: null };
}

export const useStore = create<State>((set, get) => ({
  photoUrl: null,
  photoName: null,
  image: { width: 0, height: 0 },
  anchors: [],
  activeAnchorId: null,
  nextAnchorId: 1,
  placingMapPointFor: null,
  origin: null,
  enabledEstimators: new Set<string>(ESTIMATORS.map((e: { id: string }) => e.id)),
  estimates: {},

  setPhoto: (url, width, height, name) =>
    set((state) => {
      if (state.photoUrl && state.photoUrl !== url) {
        try {
          URL.revokeObjectURL(state.photoUrl);
        } catch {
          /* ignore */
        }
      }
      return {
        photoUrl: url,
        photoName: name ?? null,
        image: { width: Math.max(1, Math.round(width)), height: Math.max(1, Math.round(height)) },
        // keep map points; the user re-picks photo pixels on the new image
        anchors: state.anchors.map((a) => ({ ...a, photoPixel: null })),
        activeAnchorId: null,
        placingMapPointFor: null,
      };
    }),

  clearPhoto: () =>
    set((state) => {
      if (state.photoUrl) {
        try {
          URL.revokeObjectURL(state.photoUrl);
        } catch {
          /* ignore */
        }
      }
      return {
        photoUrl: null,
        photoName: null,
        anchors: [],
        activeAnchorId: null,
        nextAnchorId: 1,
        placingMapPointFor: null,
        estimates: {},
      };
    }),

  setOrigin: (origin) => set({ origin }),

  addAnchor: () =>
    set((state) => {
      if (!state.photoUrl) return {};
      const anchor = makeAnchor(state.nextAnchorId, state.anchors);
      return {
        anchors: [...state.anchors, anchor],
        activeAnchorId: anchor.id,
        nextAnchorId: state.nextAnchorId + 1,
      };
    }),

  removeAnchor: (id) =>
    set((state) => ({
      anchors: state.anchors.filter((a) => a.id !== id),
      activeAnchorId: state.activeAnchorId === id ? null : state.activeAnchorId,
      placingMapPointFor: state.placingMapPointFor === id ? null : state.placingMapPointFor,
    })),

  setActiveAnchor: (id) =>
    set((state) => ({ activeAnchorId: state.activeAnchorId === id ? null : id })),

  armMapPlacement: (id) => set({ placingMapPointFor: id }),

  setAnchorPhotoPixel: (id, photoPixel) => {
    set((state) => ({
      anchors: state.anchors.map((a) => (a.id === id ? { ...a, photoPixel } : a)),
    }));
    get().recompute();
  },

  setAnchorMapPoint: (id, mapPoint) => {
    set((state) => ({
      anchors: state.anchors.map((a) => (a.id === id ? { ...a, mapPoint } : a)),
      placingMapPointFor: null,
    }));
    get().recompute();
  },

  toggleEstimator: (id) =>
    set((state) => {
      const next = new Set(state.enabledEstimators);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return { enabledEstimators: next };
    }),

  recompute: () => {
    const { anchors, image, origin, enabledEstimators } = get();
    if (!origin || !image.width || !image.height) {
      set({ estimates: {} });
      return;
    }
    const observations = buildObservations(anchors);
    const ctx = { photoWidth: image.width, photoHeight: image.height };
    const estimates: Record<string, Estimate | null> = {};
    for (const e of ESTIMATORS as Array<{ id: string; fn: Function }>) {
      if (!enabledEstimators.has(e.id)) {
        estimates[e.id] = null;
        continue;
      }
      let r: any = null;
      try {
        r = e.fn(observations, ctx);
      } catch {
        r = null;
      }
      if (r && Number.isFinite(r.px) && Number.isFinite(r.pz)) {
        const ll = localToLl(r.px, r.pz, origin);
        estimates[e.id] = {
          lat: ll.lat,
          lon: ll.lon,
          headingDeg: Number.isFinite(r.heading) ? (r.heading * 180) / Math.PI : NaN,
          elevation: Number.isFinite(r.py) ? r.py : NaN,
        };
      } else {
        estimates[e.id] = null;
      }
    }
    set({ estimates });
  },
}));
