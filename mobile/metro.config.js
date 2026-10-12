// Metro config. For the Expo Go demo build we stub the native-only voice modules
// (LiveKit, Porcupine and their peers) so Metro doesn't try to bundle them or
// resolve their native peer dependencies. They're gated behind `hasNativeVoice` at
// runtime, so they're never invoked in Expo Go. A real dev/standalone build sets
// NAVAI_NATIVE_VOICE=1 to pass through to the real packages.
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

const NATIVE_VOICE = process.env.NAVAI_NATIVE_VOICE === '1';
const STUB = require.resolve('./lib/nativeStub.js');
const NATIVE_ONLY = [
  '@livekit/react-native',
  '@livekit/react-native-webrtc',
  'livekit-client',
  '@picovoice/porcupine-react-native',
  '@picovoice/react-native-voice-processor',
];

if (!NATIVE_VOICE) {
  config.resolver.resolveRequest = (context, moduleName, platform) => {
    if (NATIVE_ONLY.some((m) => moduleName === m || moduleName.startsWith(m + '/'))) {
      return { type: 'sourceFile', filePath: STUB };
    }
    return context.resolveRequest(context, moduleName, platform);
  };
}

module.exports = config;
