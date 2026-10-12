// Expo Router root layout. Sets up audio session + wake word, renders the overlay
// above all screens.
import { useEffect } from 'react';
import { Stack } from 'expo-router';

import { VoiceOverlay } from '../components/VoiceOverlay';
import { configureAudioSession } from '../lib/ducking';
import { requestLocationPermission } from '../lib/gps';
import { hasNativeVoice } from '../lib/native';
import { loadPersistedState, startPersistence } from '../lib/persist';
import { loadSavedPlaces } from '../lib/savedPlaces';
import { runVoiceQuery } from '../lib/voiceSession';
import { startWakeWord, stopWakeWord } from '../lib/wakeword';
import { useNavStore } from '../store/useNavStore';

export default function RootLayout() {
  const wakeWordEnabled = useNavStore((s) => s.settings.wakeWordEnabled);

  useEffect(() => {
    configureAudioSession();
    requestLocationPermission();
    loadSavedPlaces().then((p) => useNavStore.getState().setSavedPlaces(p));
    loadPersistedState();
    const unsub = startPersistence();
    return unsub;
  }, []);

  useEffect(() => {
    if (wakeWordEnabled) startWakeWord(() => runVoiceQuery());
    return () => {
      stopWakeWord();
    };
  }, [wakeWordEnabled]);

  return (
    <>
      <Stack screenOptions={{ headerShown: false }} />
      {/* Full-screen voice overlay only in the native voice build; in Expo Go the
          inline chat bubbles provide feedback instead. */}
      {hasNativeVoice && <VoiceOverlay />}
    </>
  );
}
