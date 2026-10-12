// Pinned active-destination card with live ETA, shown under the location bar once
// the user asks for directions. Dismissable.
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { useNavStore } from '../store/useNavStore';

const TRAFFIC_COLOR: Record<string, string> = {
  light: '#3fb950',
  moderate: '#d29922',
  heavy: '#f85149',
};

export function ActiveDestinationCard() {
  const active = useNavStore((s) => s.activeDestination);
  const clear = useNavStore((s) => s.setActiveDestination);
  if (!active) return null;

  const color = TRAFFIC_COLOR[active.trafficLevel] ?? '#8b98a9';

  return (
    <View style={styles.card}>
      <View style={[styles.bar, { backgroundColor: color }]} />
      <View style={{ flex: 1 }}>
        <View style={styles.row}>
          <Text style={styles.label}>EN ROUTE TO</Text>
          {active.refreshing && <ActivityIndicator size="small" color="#6b7886" />}
        </View>
        <Text style={styles.name} numberOfLines={1}>
          {active.name}
        </Text>
        <Text style={styles.meta}>
          {active.distanceKm} km · via {active.via}
        </Text>
      </View>
      <View style={styles.etaBox}>
        <Text style={[styles.eta, { color }]}>{active.etaMin}</Text>
        <Text style={styles.etaUnit}>min</Text>
      </View>
      <Pressable hitSlop={10} style={styles.close} onPress={() => clear(null)}>
        <Text style={styles.closeText}>✕</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 16,
    marginTop: 10,
    backgroundColor: '#11161e',
    borderColor: '#1f2935',
    borderWidth: 1,
    borderRadius: 16,
    paddingVertical: 12,
    paddingRight: 12,
    overflow: 'hidden',
    gap: 12,
  },
  bar: { width: 4, alignSelf: 'stretch', borderTopLeftRadius: 16, borderBottomLeftRadius: 16 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  label: { color: '#6b7886', fontSize: 10, fontWeight: '700', letterSpacing: 1 },
  name: { color: '#fff', fontSize: 17, fontWeight: '700', marginTop: 1 },
  meta: { color: '#8b98a9', fontSize: 13, marginTop: 1 },
  etaBox: { alignItems: 'center', minWidth: 52 },
  eta: { fontSize: 26, fontWeight: '800', letterSpacing: -0.5 },
  etaUnit: { color: '#6b7886', fontSize: 11, fontWeight: '600', marginTop: -2 },
  close: { padding: 4 },
  closeText: { color: '#5b6770', fontSize: 16 },
});
