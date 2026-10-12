// Global app state (Zustand) — lightweight, no Redux (doc §4.1).
import { create } from 'zustand';

export type OverlayState =
  | 'idle'
  | 'wake'
  | 'listening'
  | 'processing'
  | 'responding'
  | 'done'
  | 'error';

export interface QueryHistoryItem {
  query: string;
  response: string;
  at: number;
  cards?: any[];
}

export type SavedPlace = { name: string; lat: number; lng: number };

export interface ActiveDestination {
  name: string;
  lat: number;
  lng: number;
  etaMin: number;
  distanceKm: number;
  trafficLevel: string;
  via: string;
  refreshing?: boolean;
  updatedAt: number;
}

export interface Settings {
  wakeWordEnabled: boolean;
  language: string; // 'auto' | 'en-IN' | 'hi-IN' | ...
}

interface NavStore {
  overlay: OverlayState;
  sessionId: string;
  responseText: string;
  errorMessage: string | null;
  history: QueryHistoryItem[];
  activeDestination: ActiveDestination | null;
  savedPlaces: Record<string, SavedPlace>;
  settings: Settings;
  // Current location
  currentCoords: { lat: number; lng: number } | null;
  currentAddress: string | null;
  currentShort: string | null;
  locating: boolean;

  setOverlay: (s: OverlayState) => void;
  setResponse: (text: string) => void;
  setError: (msg: string | null) => void;
  pushHistory: (item: QueryHistoryItem) => void;
  setSavedPlaces: (places: Record<string, SavedPlace>) => void;
  setActiveDestination: (d: ActiveDestination | null) => void;
  updateActiveEta: (patch: Partial<ActiveDestination>) => void;
  setSettings: (patch: Partial<Settings>) => void;
  setLocation: (coords: { lat: number; lng: number }, address: string | null, short: string | null) => void;
  setLocating: (v: boolean) => void;
  newSession: () => void;
}

const uuid = () =>
  'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });

export const useNavStore = create<NavStore>((set) => ({
  overlay: 'idle',
  sessionId: uuid(),
  responseText: '',
  errorMessage: null,
  history: [],
  activeDestination: null,
  savedPlaces: {},
  settings: { wakeWordEnabled: true, language: 'auto' },
  currentCoords: null,
  currentAddress: null,
  currentShort: null,
  locating: false,

  setOverlay: (overlay) => set({ overlay }),
  setResponse: (responseText) => set({ responseText }),
  setError: (errorMessage) => set({ errorMessage, overlay: errorMessage ? 'error' : 'idle' }),
  pushHistory: (item) => set((s) => ({ history: [item, ...s.history].slice(0, 8) })),
  setSavedPlaces: (savedPlaces) => set({ savedPlaces }),
  setActiveDestination: (activeDestination) => set({ activeDestination }),
  updateActiveEta: (patch) =>
    set((s) => (s.activeDestination ? { activeDestination: { ...s.activeDestination, ...patch } } : {})),
  setSettings: (patch) => set((s) => ({ settings: { ...s.settings, ...patch } })),
  setLocation: (currentCoords, currentAddress, currentShort) =>
    set({ currentCoords, currentAddress, currentShort, locating: false }),
  setLocating: (locating) => set({ locating }),
  newSession: () => set({ sessionId: uuid() }),
}));
