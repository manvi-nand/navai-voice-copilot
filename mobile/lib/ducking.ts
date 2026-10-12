// Audio session config (doc §4.1).
//
// IMPORTANT: allowsRecordingIOS must be FALSE for playback, otherwise iOS routes
// audio to the quiet earpiece instead of the speaker (this was why TTS was silent).
// playsInSilentModeIOS lets answers play even with the ringer switch off.
import { Audio } from 'expo-av';

export async function configureAudioSession(): Promise<void> {
  try {
    await Audio.setAudioModeAsync({
      allowsRecordingIOS: false,
      playsInSilentModeIOS: true,
      staysActiveInBackground: false,
      shouldDuckAndroid: true,
      playThroughEarpieceAndroid: false,
    });
  } catch (e) {
    console.warn('[audio] setAudioMode failed', e);
  }
}
