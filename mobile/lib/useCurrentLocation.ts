// Resolves the device GPS to a human address and keeps it in the store, powering
// the current-location bar at the top of the home screen.
import { useEffect } from 'react';

import { reverseGeocode } from './api';
import { getCurrentCoords, requestLocationPermission } from './gps';
import { useNavStore } from '../store/useNavStore';

export function useCurrentLocation(): void {
  const setLocation = useNavStore((s) => s.setLocation);
  const setLocating = useNavStore((s) => s.setLocating);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLocating(true);
      try {
        await requestLocationPermission();
        const coords = await getCurrentCoords();
        let address: string | null = null;
        let short: string | null = null;
        try {
          const rg = await reverseGeocode(coords.lat, coords.lng);
          address = rg.address;
          short = rg.short;
        } catch {
          /* keep coords even if naming fails */
        }
        if (!cancelled) setLocation(coords, address, short);
      } catch {
        if (!cancelled) {
          setLocation({ lat: 12.9716, lng: 77.5946 }, 'Location unavailable', 'Set location');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);
}
