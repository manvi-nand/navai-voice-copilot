// Visual route map with live traffic, drawn from the backend route polyline.
// Uses react-native-maps (Apple Maps on iOS — no API key, built-in traffic layer).
// Tapping it opens the route in the native Google/Apple Maps app for full
// interactive pan/zoom + live traffic. The require is guarded so the app degrades
// gracefully if maps aren't available.
import {
  ActionSheetIOS,
  Dimensions,
  Linking,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';

let Maps: any = null;
try {
  Maps = require('react-native-maps');
} catch {
  Maps = null;
}

const MAP_WIDTH = Math.round(Dimensions.get('window').width * 0.74);

type Pt = { latitude: number; longitude: number };

function openRoute(start: Pt, end: Pt) {
  const o = `${start.latitude},${start.longitude}`;
  const d = `${end.latitude},${end.longitude}`;
  const google = `https://www.google.com/maps/dir/?api=1&origin=${o}&destination=${d}&travelmode=driving`;
  const apple = `http://maps.apple.com/?saddr=${o}&daddr=${d}&dirflg=d`;

  if (Platform.OS === 'ios') {
    ActionSheetIOS.showActionSheetWithOptions(
      {
        title: 'Open directions in',
        options: ['Google Maps', 'Apple Maps', 'Cancel'],
        cancelButtonIndex: 2,
      },
      (i) => {
        if (i === 0) Linking.openURL(google);
        else if (i === 1) Linking.openURL(apple);
      },
    );
  } else {
    Linking.openURL(google);
  }
}

export function RouteMap({ polyline, height = 180 }: { polyline?: Pt[]; height?: number }) {
  if (!Maps || !polyline || polyline.length < 2) return null;

  const MapView = Maps.default;
  const { Marker, Polyline, PROVIDER_DEFAULT } = Maps;

  const lats = polyline.map((p) => p.latitude);
  const lngs = polyline.map((p) => p.longitude);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  const region = {
    latitude: (minLat + maxLat) / 2,
    longitude: (minLng + maxLng) / 2,
    latitudeDelta: Math.max((maxLat - minLat) * 1.6, 0.02),
    longitudeDelta: Math.max((maxLng - minLng) * 1.6, 0.02),
  };
  const start = polyline[0];
  const end = polyline[polyline.length - 1];

  return (
    <Pressable
      style={[styles.wrap, { height, width: MAP_WIDTH }]}
      onPress={() => openRoute(start, end)}
    >
      <MapView
        style={StyleSheet.absoluteFill}
        provider={PROVIDER_DEFAULT}
        initialRegion={region}
        showsTraffic
        showsCompass={false}
        toolbarEnabled={false}
        pointerEvents="none"
      >
        <Polyline coordinates={polyline} strokeColor="#2f6fed" strokeWidth={5} />
        <Marker coordinate={start} pinColor="#3fb950" />
        <Marker coordinate={end} pinColor="#f85149" />
      </MapView>
      <View style={styles.badge}>
        <Text style={styles.badgeText}>Open in Maps ↗</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: 12,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: '#0d1117',
  },
  badge: {
    position: 'absolute',
    right: 8,
    bottom: 8,
    backgroundColor: 'rgba(10,14,20,0.82)',
    borderRadius: 8,
    paddingVertical: 6,
    paddingHorizontal: 10,
  },
  badgeText: { color: '#fff', fontSize: 12, fontWeight: '700' },
});
