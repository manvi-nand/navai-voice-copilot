// Settings (doc §6.2): wake word on/off, language preference, saved places.
import { Pressable, ScrollView, StyleSheet, Switch, Text, View } from 'react-native';
import { Link } from 'expo-router';

import { removeSavedPlace } from '../lib/savedPlaces';
import { useNavStore } from '../store/useNavStore';

const LANGS = ['auto', 'en-IN', 'hi-IN', 'ta-IN', 'te-IN', 'kn-IN'];

export default function SettingsScreen() {
  const settings = useNavStore((s) => s.settings);
  const setSettings = useNavStore((s) => s.setSettings);
  const savedPlaces = useNavStore((s) => s.savedPlaces);
  const setSavedPlaces = useNavStore((s) => s.setSavedPlaces);

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingTop: 64 }}>
      <Link href="/" style={styles.back}>‹ Back</Link>
      <Text style={styles.title}>Settings</Text>

      <View style={styles.row}>
        <Text style={styles.label}>Wake word “Hey Nav”</Text>
        <Switch
          value={settings.wakeWordEnabled}
          onValueChange={(v) => setSettings({ wakeWordEnabled: v })}
        />
      </View>

      <Text style={styles.section}>Response language</Text>
      <View style={styles.chips}>
        {LANGS.map((l) => (
          <Pressable
            key={l}
            style={[styles.chip, settings.language === l && styles.chipActive]}
            onPress={() => setSettings({ language: l })}
          >
            <Text style={styles.chipText}>{l}</Text>
          </Pressable>
        ))}
      </View>

      <Text style={styles.section}>Saved places</Text>
      {Object.entries(savedPlaces).map(([label, p]) => (
        <View key={label} style={styles.row}>
          <Text style={styles.label}>
            {label} · {p.name}
          </Text>
          <Pressable onPress={async () => setSavedPlaces(await removeSavedPlace(label))}>
            <Text style={styles.remove}>Remove</Text>
          </Pressable>
        </View>
      ))}
      {Object.keys(savedPlaces).length === 0 && (
        <Text style={styles.empty}>Say “save this as my home” while driving.</Text>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0e14', paddingHorizontal: 24 },
  back: { color: '#4da3ff', fontSize: 17, marginBottom: 8 },
  title: { color: '#fff', fontSize: 28, fontWeight: '700', marginBottom: 24 },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 14,
    borderBottomColor: '#1c2127',
    borderBottomWidth: 1,
  },
  label: { color: '#e6edf3', fontSize: 16 },
  section: { color: '#9aa6b2', fontSize: 14, marginTop: 24, marginBottom: 8 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { backgroundColor: '#151a1f', borderRadius: 16, paddingVertical: 8, paddingHorizontal: 14 },
  chipActive: { backgroundColor: '#1f6feb' },
  chipText: { color: '#fff' },
  remove: { color: '#ff8a80' },
  empty: { color: '#5b6770', marginTop: 8 },
});
