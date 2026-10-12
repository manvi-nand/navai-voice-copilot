// Siri-style voice overlay (doc §6.1). Animated waveform reacting to the current
// overlay state, with a transcript of the spoken response.
import React, { useEffect } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

import { OverlayState, useNavStore } from '../store/useNavStore';

const LABELS: Record<OverlayState, string> = {
  idle: '',
  wake: '',
  listening: 'Listening…',
  processing: 'Got it…',
  responding: '',
  done: '',
  error: '',
};

export function VoiceOverlay() {
  const overlay = useNavStore((s) => s.overlay);
  const responseText = useNavStore((s) => s.responseText);
  const errorMessage = useNavStore((s) => s.errorMessage);

  const pulse = useSharedValue(1);
  useEffect(() => {
    const active = overlay === 'listening' || overlay === 'responding' || overlay === 'processing';
    pulse.value = active
      ? withRepeat(withTiming(1.6, { duration: 500 }), -1, true)
      : withTiming(1);
  }, [overlay]);

  const waveStyle = useAnimatedStyle(() => ({ transform: [{ scaleY: pulse.value }] }));

  if (overlay === 'idle') return null;

  return (
    <View style={styles.backdrop}>
      <View style={styles.sheet}>
        <View style={styles.waveRow}>
          {[0, 1, 2, 3, 4].map((i) => (
            <Animated.View key={i} style={[styles.bar, waveStyle]} />
          ))}
        </View>
        {overlay === 'error' ? (
          <Text style={styles.error}>{errorMessage ?? "Couldn't hear clearly"}</Text>
        ) : overlay === 'responding' || overlay === 'done' ? (
          <Text style={styles.response}>{responseText}</Text>
        ) : (
          <Text style={styles.label}>{LABELS[overlay]}</Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0,0,0,0.35)',
  },
  sheet: {
    backgroundColor: '#101418',
    paddingVertical: 32,
    paddingHorizontal: 24,
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    alignItems: 'center',
  },
  waveRow: { flexDirection: 'row', height: 60, alignItems: 'center', gap: 8 },
  bar: { width: 8, height: 28, borderRadius: 4, backgroundColor: '#4da3ff' },
  label: { color: '#9aa6b2', marginTop: 18, fontSize: 16 },
  response: { color: '#fff', marginTop: 18, fontSize: 18, textAlign: 'center', lineHeight: 26 },
  error: { color: '#ff8a80', marginTop: 18, fontSize: 16, textAlign: 'center' },
});
