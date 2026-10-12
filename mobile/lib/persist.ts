// Persists conversation + active destination across app restarts (and logs trip
// destinations for the "recent destinations" suggestions / future commute learning).
import AsyncStorage from '@react-native-async-storage/async-storage';

import { useNavStore } from '../store/useNavStore';

const KEY = 'navai.state.v1';

export async function loadPersistedState(): Promise<void> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (!raw) return;
    const s = JSON.parse(raw);
    useNavStore.setState({
      history: Array.isArray(s.history) ? s.history : [],
      activeDestination: s.activeDestination ?? null,
    });
  } catch {
    /* ignore corrupt cache */
  }
}

export function startPersistence(): () => void {
  let last = '';
  return useNavStore.subscribe((state) => {
    const snapshot = JSON.stringify({
      history: state.history,
      activeDestination: state.activeDestination,
    });
    if (snapshot !== last) {
      last = snapshot;
      AsyncStorage.setItem(KEY, snapshot).catch(() => {});
    }
  });
}
