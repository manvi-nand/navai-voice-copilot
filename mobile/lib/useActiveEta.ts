// Keeps the active destination's ETA live by re-polling the backend every 60s
// from the user's current location (doc §2.8 spirit — route awareness).
import { useEffect } from 'react';

import { getDirections } from './api';
import { useNavStore } from '../store/useNavStore';

const REFRESH_MS = 60_000;

export function useActiveEta(): void {
  const active = useNavStore((s) => s.activeDestination);
  const coords = useNavStore((s) => s.currentCoords);

  useEffect(() => {
    if (!active || !coords) return;

    let cancelled = false;
    const refresh = async () => {
      useNavStore.getState().updateActiveEta({ refreshing: true });
      try {
        const r = await getDirections(coords.lat, coords.lng, active.lat, active.lng);
        if (cancelled) return;
        useNavStore.getState().updateActiveEta({
          etaMin: r.duration_in_traffic_min,
          distanceKm: r.distance_km,
          trafficLevel: r.traffic_level,
          via: r.summary,
          updatedAt: Date.now(),
          refreshing: false,
        });
      } catch {
        if (!cancelled) useNavStore.getState().updateActiveEta({ refreshing: false });
      }
    };

    const id = setInterval(refresh, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
    // Re-arm when the destination changes (not on every ETA tick).
  }, [active?.lat, active?.lng, coords?.lat, coords?.lng]);
}
