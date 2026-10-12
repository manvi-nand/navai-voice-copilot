// Rich answer cards rendered under the assistant's spoken text in the chat.
import { StyleSheet, Text, View } from 'react-native';

import { RouteMap } from './RouteMap';

const TRAFFIC_COLOR: Record<string, string> = {
  light: '#3fb950',
  moderate: '#d29922',
  heavy: '#f85149',
};

function shortName(name?: string): string {
  if (!name) return 'Destination';
  return name.split(',')[0];
}

function distanceLabel(km?: number | null): string {
  if (km == null) return 'nearby';
  if (km < 1) return `${Math.round(km * 1000)} m away`;
  return `${km} km away`;
}

export function AnswerCards({ cards }: { cards?: any[] }) {
  if (!cards || cards.length === 0) return null;
  return (
    <View style={styles.wrap}>
      {cards.map((c, i) => {
        if (c.type === 'directions') return <RouteCard key={i} data={c.data} />;
        if (c.type === 'weather') return <WeatherCard key={i} data={c.data} />;
        if (c.type === 'places' || c.type === 'on_route')
          return <PlacesCard key={i} data={c.data} onRoute={c.type === 'on_route'} />;
        if (c.type === 'leave_by') return <LeaveByCard key={i} data={c.data} />;
        if (c.type === 'trip') return <TripCard key={i} data={c.data} />;
        if (c.type === 'route_compare') return <RouteCompareCard key={i} data={c.data} />;
        return null;
      })}
    </View>
  );
}

function RouteCard({ data }: { data: any }) {
  const color = TRAFFIC_COLOR[data.traffic_level] ?? '#8b98a9';
  return (
    <View style={styles.card}>
      <View style={styles.routeHead}>
        <Text style={styles.routeIcon}>🧭</Text>
        <Text style={styles.cardTitle} numberOfLines={1}>
          {shortName(data.destination_name)}
        </Text>
      </View>
      <Text style={styles.eta}>{data.duration_in_traffic_min} min</Text>
      <Text style={styles.routeSub}>
        {data.distance_km} km · via {data.summary}
      </Text>
      <View style={styles.chipRow}>
        <View style={[styles.trafficChip, { backgroundColor: color + '22' }]}>
          <View style={[styles.dot, { backgroundColor: color }]} />
          <Text style={[styles.trafficText, { color }]}>{data.traffic_level} traffic</Text>
        </View>
        {data.toll && (
          <View style={[styles.trafficChip, { backgroundColor: '#d2992222' }]}>
            <Text style={[styles.trafficText, { color: '#d29922' }]}>🪙 {data.toll}</Text>
          </View>
        )}
      </View>
      <RouteMap polyline={data.polyline} />
    </View>
  );
}

function LeaveByCard({ data }: { data: any }) {
  return (
    <View style={styles.card}>
      <View style={styles.routeHead}>
        <Text style={styles.routeIcon}>⏰</Text>
        <Text style={styles.cardTitle} numberOfLines={1}>
          {shortName(data.destination_name)}
        </Text>
      </View>
      <Text style={styles.eta}>Leave {data.leave_by}</Text>
      <Text style={styles.routeSub}>
        to arrive by {data.arrive_by} · {data.travel_minutes} min drive
      </Text>
    </View>
  );
}

function TripCard({ data }: { data: any }) {
  return (
    <View style={styles.card}>
      <View style={styles.routeHead}>
        <Text style={styles.routeIcon}>🧳</Text>
        <Text style={styles.cardTitle}>
          Trip · {data.total_minutes} min · {data.total_km} km
        </Text>
      </View>
      {(data.legs ?? []).map((leg: any, i: number) => (
        <View key={i} style={styles.legRow}>
          <View style={styles.legBullet}>
            <Text style={styles.legNum}>{i + 1}</Text>
          </View>
          <Text style={styles.legName} numberOfLines={1}>
            {shortName(leg.to)}
          </Text>
          <Text style={styles.legMeta}>
            {leg.minutes} min · {leg.km} km
          </Text>
        </View>
      ))}
    </View>
  );
}

function RouteCompareCard({ data }: { data: any }) {
  const f = data.fastest ?? {};
  const a = data.no_highway ?? {};
  const diff = (a.duration_in_traffic_min ?? 0) - (f.duration_in_traffic_min ?? 0);
  return (
    <View style={styles.card}>
      <View style={styles.routeHead}>
        <Text style={styles.routeIcon}>🔀</Text>
        <Text style={styles.cardTitle} numberOfLines={1}>
          {shortName(data.destination_name)}
        </Text>
      </View>
      <View style={styles.compareRow}>
        <View style={styles.compareCol}>
          <Text style={styles.compareLabel}>FASTEST</Text>
          <Text style={styles.compareEta}>{f.duration_in_traffic_min} min</Text>
          <Text style={styles.compareVia} numberOfLines={1}>via {f.summary}</Text>
        </View>
        <View style={styles.compareCol}>
          <Text style={styles.compareLabel}>NO HIGHWAY</Text>
          <Text style={styles.compareEta}>{a.duration_in_traffic_min} min</Text>
          <Text style={styles.compareVia} numberOfLines={1}>via {a.summary}</Text>
        </View>
      </View>
      <Text style={styles.compareDelta}>
        {diff === 0
          ? 'Same time either way'
          : diff > 0
            ? `Highway saves ${diff} min`
            : `Avoiding highway saves ${-diff} min`}
      </Text>
    </View>
  );
}

function WeatherCard({ data }: { data: any }) {
  const rain = data.rain_expected;
  const emoji = rain ? '🌧️' : '⛅';
  return (
    <View style={styles.card}>
      <View style={styles.routeHead}>
        <Text style={styles.routeIcon}>{emoji}</Text>
        <Text style={styles.cardTitle}>Weather · {data.place}</Text>
      </View>
      <Text style={styles.weatherNow}>{data.current}</Text>
      <Text style={[styles.weatherRain, { color: rain ? '#58a6ff' : '#8b98a9' }]}>
        {rain && data.rain_in_minutes != null
          ? `Rain in about ${data.rain_in_minutes} min`
          : data.summary}
      </Text>
    </View>
  );
}

function PlacesCard({ data, onRoute }: { data: any; onRoute: boolean }) {
  const results = (data.results ?? []).slice(0, 4);
  return (
    <View style={styles.card}>
      <View style={styles.routeHead}>
        <Text style={styles.routeIcon}>📍</Text>
        <Text style={styles.cardTitle}>
          {data.place_type} {onRoute ? 'on your route' : 'nearby'}
        </Text>
      </View>
      {results.map((p: any, i: number) => (
        <View key={i} style={styles.placeRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.placeName} numberOfLines={1}>
              {p.name}
            </Text>
            <Text style={styles.placeMeta}>
              {onRoute ? `+${p.added_minutes} min detour` : distanceLabel(p.distance_km)}
            </Text>
          </View>
          {!onRoute && p.open_now != null && (
            <Text style={[styles.openTag, { color: p.open_now ? '#3fb950' : '#f85149' }]}>
              {p.open_now ? 'Open' : 'Closed'}
            </Text>
          )}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginTop: 4, marginBottom: 6, alignSelf: 'flex-start', maxWidth: '92%' },
  card: {
    backgroundColor: '#11161e',
    borderColor: '#1f2935',
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    marginTop: 8,
    minWidth: 230,
  },
  routeHead: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 },
  routeIcon: { fontSize: 16 },
  cardTitle: { color: '#9fb1c4', fontSize: 13, fontWeight: '700', flexShrink: 1 },
  eta: { color: '#fff', fontSize: 30, fontWeight: '800', letterSpacing: -0.5 },
  routeSub: { color: '#8b98a9', fontSize: 14, marginTop: 2 },
  trafficChip: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: 6,
    borderRadius: 12,
    paddingVertical: 5,
    paddingHorizontal: 10,
    marginTop: 12,
  },
  dot: { width: 7, height: 7, borderRadius: 4 },
  trafficText: { fontSize: 13, fontWeight: '600', textTransform: 'capitalize' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  // Trip legs
  legRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8, gap: 10 },
  legBullet: { width: 22, height: 22, borderRadius: 11, backgroundColor: '#1f2935', alignItems: 'center', justifyContent: 'center' },
  legNum: { color: '#9fb1c4', fontSize: 12, fontWeight: '700' },
  legName: { color: '#e6edf3', fontSize: 15, fontWeight: '600', flex: 1 },
  legMeta: { color: '#8b98a9', fontSize: 13 },
  // Route compare
  compareRow: { flexDirection: 'row', gap: 12, marginTop: 4 },
  compareCol: { flex: 1, backgroundColor: '#0d131c', borderRadius: 12, padding: 12 },
  compareLabel: { color: '#6b7886', fontSize: 10, fontWeight: '700', letterSpacing: 1 },
  compareEta: { color: '#fff', fontSize: 22, fontWeight: '800', marginTop: 4 },
  compareVia: { color: '#8b98a9', fontSize: 12, marginTop: 2 },
  compareDelta: { color: '#58a6ff', fontSize: 14, fontWeight: '600', marginTop: 12 },
  weatherNow: { color: '#fff', fontSize: 22, fontWeight: '700', textTransform: 'capitalize' },
  weatherRain: { fontSize: 15, marginTop: 4 },
  placeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 9,
    borderTopColor: '#1a2230',
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  placeName: { color: '#e6edf3', fontSize: 15, fontWeight: '600' },
  placeMeta: { color: '#8b98a9', fontSize: 13, marginTop: 1 },
  openTag: { fontSize: 13, fontWeight: '700' },
});
