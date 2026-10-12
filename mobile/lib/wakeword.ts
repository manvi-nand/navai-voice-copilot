// Porcupine on-device wake-word detection (doc §2.1, §4.1).
// Runs locally, no network. Fires onWake() when "Hey Nav" is detected.
//
// SETUP (dev build only): train a custom "Hey Nav" keyword in the Picovoice Console
// (free, personal), download the .ppn for iOS and Android, drop into assets/, and set
// EXPO_PUBLIC_PICOVOICE_KEY.
//
// In Expo Go the Porcupine native module isn't bundled, so this no-ops and the
// on-screen button is used instead.
import { hasNativeVoice } from './native';

const ACCESS_KEY = process.env.EXPO_PUBLIC_PICOVOICE_KEY ?? '';

let manager: any = null;

export async function startWakeWord(onWake: () => void): Promise<void> {
  if (!hasNativeVoice) {
    console.warn('[wakeword] Expo Go — wake word disabled, use the on-screen button');
    return;
  }
  if (!ACCESS_KEY) {
    console.warn('[wakeword] no Picovoice key — use the on-screen button to activate');
    return;
  }
  try {
    // Lazy require so Expo Go never loads the native module.
    const { PorcupineManager } = require('@picovoice/porcupine-react-native');
    manager = await PorcupineManager.fromKeywordPaths(
      ACCESS_KEY,
      ['assets/hey-nav.ppn'],
      (_keywordIndex: number) => onWake(),
      (err: unknown) => console.error('[wakeword]', err),
    );
    await manager.start();
  } catch (e) {
    console.warn('[wakeword] unavailable:', e);
  }
}

export async function stopWakeWord(): Promise<void> {
  try {
    await manager?.stop();
    await manager?.delete();
  } catch {
    /* ignore */
  }
  manager = null;
}
