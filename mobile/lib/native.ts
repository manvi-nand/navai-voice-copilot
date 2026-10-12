// Detects whether native modules are available. In Expo Go (the no-build demo
// runner) the custom native modules — LiveKit WebRTC and Porcupine — are NOT
// bundled, so we must avoid importing/using them or the app crashes on load.
// In a dev/production build they ARE available and the full voice path runs.
import Constants, { ExecutionEnvironment } from 'expo-constants';

// Expo Go reports StoreClient; dev/standalone builds report Bare/Standalone.
export const isExpoGo =
  Constants.executionEnvironment === ExecutionEnvironment.StoreClient;

// True when we can use LiveKit + Porcupine (i.e. a real dev build, not Expo Go).
export const hasNativeVoice = !isExpoGo;
