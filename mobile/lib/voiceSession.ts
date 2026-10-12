// One push-to-talk round trip.
//
// Two modes:
//  * Native (dev build): full voice over LiveKit (doc §3.2) — publish mic, receive
//    the agent's TTS audio track, advance the overlay from data-channel events.
//  * Expo Go (no native build): LiveKit/WebRTC aren't available, so we fall back to
//    runTextQuery — POST the typed question to /query and play the spoken answer the
//    backend returns via /tts (expo-av works in Expo Go).
import { Audio } from 'expo-av';
import Constants from 'expo-constants';

import { postQuery } from './api';
import { configureAudioSession } from './ducking';
import { getCurrentCoords } from './gps';
import { hasNativeVoice } from './native';
import { persistSavedPlace } from './savedPlaces';
import { useNavStore } from '../store/useNavStore';

const HTTP =
  (Constants.expoConfig?.extra?.backendHttpUrl as string) ?? 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Degraded path (Expo Go): typed question -> real backend answer + spoken audio.
// ---------------------------------------------------------------------------
export async function runTextQuery(text: string): Promise<void> {
  const store = useNavStore.getState();
  if (!text.trim()) return;
  store.setError(null);
  store.setResponse('');
  store.setOverlay('processing');
  try {
    // Prefer the already-resolved current location; fall back to a fresh fix.
    const { lat, lng } =
      store.currentCoords ??
      (await getCurrentCoords().catch(() => ({ lat: 12.9716, lng: 77.5946 })));
    const lang = store.settings.language === 'auto' ? 'en-IN' : store.settings.language;
    const data = await postQuery({
      transcript: text,
      current_location: { lat, lng },
      session_id: store.sessionId,
      language: lang,
      saved_places: store.savedPlaces,
    });
    const s = useNavStore.getState();
    s.setResponse(data.response_text);
    s.setOverlay('responding');
    s.pushHistory({
      query: text,
      response: data.response_text,
      at: Date.now(),
      cards: data.cards ?? [],
    });
    if (data.saved_place) {
      const sp = data.saved_place;
      const all = await persistSavedPlace(sp.name, { name: sp.name, lat: sp.lat, lng: sp.lng });
      s.setSavedPlaces(all);
    }
    // Pin the active destination from a directions answer (for the live-ETA card).
    const route = (data.cards ?? []).find((c: any) => c.type === 'directions');
    if (route?.data?.dest_lat != null) {
      const d = route.data;
      s.setActiveDestination({
        name: (d.destination_name ?? 'Destination').split(',')[0],
        lat: d.dest_lat,
        lng: d.dest_lng,
        etaMin: d.duration_in_traffic_min,
        distanceKm: d.distance_km,
        trafficLevel: d.traffic_level,
        via: d.summary,
        updatedAt: Date.now(),
      });
    }
    await playSpokenAnswer(data.response_text, data.language ?? lang);
    useNavStore.getState().setOverlay('done');
    setTimeout(() => useNavStore.getState().setOverlay('idle'), 1500);
  } catch {
    useNavStore.getState().setError('Could not reach NavAI backend');
  }
}

async function playSpokenAnswer(text: string, language: string): Promise<void> {
  try {
    await configureAudioSession(); // ensure playback routes to the speaker
    const url = `${HTTP}/tts?text=${encodeURIComponent(text)}&language=${encodeURIComponent(language)}`;
    // iOS AVPlayer refuses to stream this over HTTP (error -11850), so download to a
    // local file first and play that — far more reliable.
    const FileSystem = require('expo-file-system/legacy');
    const localUri = `${FileSystem.cacheDirectory}tts-${Date.now()}.wav`;
    await FileSystem.downloadAsync(url, localUri);
    const { sound } = await Audio.Sound.createAsync(
      { uri: localUri },
      { shouldPlay: true, volume: 1.0 },
    );
    sound.setOnPlaybackStatusUpdate((status) => {
      if ('didJustFinish' in status && status.didJustFinish) {
        sound.unloadAsync();
        FileSystem.deleteAsync(localUri, { idempotent: true }).catch(() => {});
      }
    });
  } catch (e) {
    console.warn('[tts] playback failed', e);
  }
}

// ---------------------------------------------------------------------------
// Native path (dev build): full LiveKit voice. Lazy-loaded so Expo Go never
// touches the native modules.
// ---------------------------------------------------------------------------
let activeRoom: any = null;

export async function runVoiceQuery(): Promise<void> {
  if (!hasNativeVoice) {
    // In Expo Go the UI routes the mic button to the text box instead.
    console.warn('[voice] native voice unavailable in Expo Go — use the text box');
    return;
  }
  const store = useNavStore.getState();
  store.setError(null);
  store.setOverlay('listening');
  try {
    const { AudioSession, registerGlobals } = require('@livekit/react-native');
    registerGlobals();
    const { joinRoom, leaveRoom } = require('./livekit');
    const { fetchLiveKitToken } = require('./api');

    await AudioSession.startAudioSession();
    const { token, url } = await fetchLiveKitToken(store.sessionId);
    activeRoom = await joinRoom(url, token, {
      onAgentTrack: () => useNavStore.getState().setOverlay('responding'),
      onData: (msg: any) => handleEvent(msg),
    });
  } catch {
    useNavStore.getState().setError('No internet connection');
    await endVoiceSession();
  }
}

function handleEvent(msg: any): void {
  const s = useNavStore.getState();
  switch (msg.type) {
    case 'transcript':
      s.setOverlay('processing');
      break;
    case 'response':
      s.setResponse(msg.text);
      s.setOverlay('responding');
      s.pushHistory({ query: '(voice)', response: msg.text, at: Date.now() });
      if (msg.saved_place) {
        const sp = msg.saved_place;
        persistSavedPlace(sp.name, { name: sp.name, lat: sp.lat, lng: sp.lng }).then((all) =>
          useNavStore.getState().setSavedPlaces(all),
        );
      }
      break;
    case 'proactive':
      s.setResponse(msg.text);
      s.setOverlay('responding');
      break;
    case 'done':
      s.setOverlay('done');
      setTimeout(() => useNavStore.getState().setOverlay('idle'), 1500);
      endVoiceSession();
      break;
    case 'error':
      s.setError(msg.message ?? "Couldn't hear clearly");
      endVoiceSession();
      break;
  }
}

export async function endVoiceSession(): Promise<void> {
  try {
    if (activeRoom) {
      const { leaveRoom } = require('./livekit');
      await leaveRoom(activeRoom);
      const { AudioSession } = require('@livekit/react-native');
      await AudioSession.stopAudioSession();
    }
  } catch {
    /* ignore */
  }
  activeRoom = null;
}
