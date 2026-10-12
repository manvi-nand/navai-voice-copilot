// Saved places persisted to device storage (doc §2.7, §5.1 — device is source of
// truth). Synced to the backend with each query so 'home'/'office' resolve server-side.
import AsyncStorage from '@react-native-async-storage/async-storage';

export type SavedPlace = { name: string; lat: number; lng: number };
type SavedPlaces = Record<string, SavedPlace>;

const KEY = 'navai.savedPlaces';

export async function loadSavedPlaces(): Promise<SavedPlaces> {
  const raw = await AsyncStorage.getItem(KEY);
  return raw ? (JSON.parse(raw) as SavedPlaces) : {};
}

export async function persistSavedPlace(label: string, place: SavedPlace): Promise<SavedPlaces> {
  const all = await loadSavedPlaces();
  all[label] = place;
  await AsyncStorage.setItem(KEY, JSON.stringify(all));
  return all;
}

export async function removeSavedPlace(label: string): Promise<SavedPlaces> {
  const all = await loadSavedPlaces();
  delete all[label];
  await AsyncStorage.setItem(KEY, JSON.stringify(all));
  return all;
}
