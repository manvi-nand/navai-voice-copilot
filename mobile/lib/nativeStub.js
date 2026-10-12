// Stub for native-only modules (LiveKit, Porcupine) in the Expo Go demo bundle.
// These can't run in Expo Go; Metro aliases the real packages to this file (see
// metro.config.js) so their heavy native peer deps don't need to resolve. Nothing
// here is ever invoked at runtime — code paths that would use them are gated behind
// `hasNativeVoice` (lib/native.ts). In a real dev build the resolver passes through
// to the actual packages instead.
const handler = {
  get: (_target, prop) => {
    if (prop === '__esModule') return true;
    // Any access returns a callable no-op that also proxies further property access.
    return new Proxy(function () {}, handler);
  },
};
module.exports = new Proxy(function () {}, handler);
