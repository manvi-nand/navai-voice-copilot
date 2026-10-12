// GPS via expo-location (doc §4.1). High accuracy; coordinates are sent with each
// query so backend tools receive live location from state.
import * as Location from 'expo-location';

export async function requestLocationPermission(): Promise<boolean> {
  const { status } = await Location.requestForegroundPermissionsAsync();
  return status === 'granted';
}

export async function getCurrentCoords(): Promise<{ lat: number; lng: number }> {
  const pos = await Location.getCurrentPositionAsync({
    accuracy: Location.Accuracy.High,
  });
  return { lat: pos.coords.latitude, lng: pos.coords.longitude };
}

// Phase 2: background watch for proactive traffic alerts (doc §2.8).
export function watchPosition(
  cb: (coords: { lat: number; lng: number }) => void,
): Promise<Location.LocationSubscription> {
  return Location.watchPositionAsync(
    { accuracy: Location.Accuracy.High, distanceInterval: 50 },
    (pos) => cb({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
  );
}
