// NavAI home — current-location bar, chat-style conversation, polished input.
import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native';
import { Link } from 'expo-router';

import { ActiveDestinationCard } from '../components/ActiveDestinationCard';
import { AnswerCards } from '../components/Cards';
import { hasNativeVoice } from '../lib/native';
import { useActiveEta } from '../lib/useActiveEta';
import { useCurrentLocation } from '../lib/useCurrentLocation';
import { runTextQuery, runVoiceQuery } from '../lib/voiceSession';
import { useNavStore } from '../store/useNavStore';

const EXAMPLES = [
  'How long to Koramangala?',
  'Petrol bunk near me',
  'Will it rain soon?',
  'Where am I?',
];

export default function Home() {
  useCurrentLocation();
  useActiveEta();

  const history = useNavStore((s) => s.history);
  const overlay = useNavStore((s) => s.overlay);
  const responseText = useNavStore((s) => s.responseText);
  const currentShort = useNavStore((s) => s.currentShort);
  const currentAddress = useNavStore((s) => s.currentAddress);
  const locating = useNavStore((s) => s.locating);
  const activeDestination = useNavStore((s) => s.activeDestination);

  const [text, setText] = useState('');
  const [pending, setPending] = useState<string | null>(null);
  const scrollRef = useRef<ScrollView>(null);

  const busy = overlay === 'processing' || overlay === 'listening';

  // Conversation oldest -> newest for chat layout.
  const turns = [...history].reverse();

  useEffect(() => {
    const t = setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 80);
    return () => clearTimeout(t);
  }, [history.length, overlay, responseText]);

  const submit = (q: string) => {
    const query = q.trim();
    if (!query || busy) return;
    setText('');
    setPending(query);
    runTextQuery(query).finally(() => setPending(null));
  };

  // Context-aware quick replies.
  const suggestions: { label: string; q: string }[] = activeDestination
    ? [
        { label: '🅿️ Parking there', q: `Find parking near ${activeDestination.name}` },
        { label: '🔀 Avoid highway', q: 'What about avoiding the highway?' },
        { label: '☕ On the way', q: 'Anything good on the way?' },
        { label: '⛽ Petrol nearby', q: 'Petrol bunk near me' },
      ]
    : [
        { label: '📋 My briefing', q: 'Give me my driving briefing: time to my office, the traffic, and the weather' },
        { label: '⛽ Petrol near me', q: 'Petrol bunk near me' },
        { label: '🌧️ Will it rain?', q: 'Will it rain in the next hour?' },
        { label: '⚡ EV charger', q: 'Nearest EV charging station' },
      ];

  return (
    <SafeAreaView style={styles.safe}>
      {/* Location bar */}
      <View style={styles.locBar}>
        <View style={styles.pinDot} />
        <View style={{ flex: 1 }}>
          <Text style={styles.locLabel}>CURRENT LOCATION</Text>
          {locating ? (
            <View style={styles.locRow}>
              <ActivityIndicator size="small" color="#8b98a9" />
              <Text style={styles.locating}>  Locating…</Text>
            </View>
          ) : (
            <Text style={styles.locText} numberOfLines={1}>
              {currentShort ?? currentAddress ?? 'Location unavailable'}
            </Text>
          )}
        </View>
        <Link href="/settings" style={styles.gear}>
          ⚙
        </Link>
      </View>

      {/* Active destination (live ETA) */}
      <ActiveDestinationCard />

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.brand}>NavAI</Text>
        <Text style={styles.tagline}>Your hands-free travel companion</Text>
      </View>

      {/* Conversation */}
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={8}
      >
        <ScrollView
          ref={scrollRef}
          style={styles.convo}
          contentContainerStyle={styles.convoContent}
          keyboardShouldPersistTaps="handled"
        >
          {turns.length === 0 && !pending && (
            <View style={styles.empty}>
              <Text style={styles.emptyTitle}>Ask me anything about your drive</Text>
              <Text style={styles.emptySub}>Routes · traffic · nearby places · weather</Text>
              <View style={styles.chips}>
                {EXAMPLES.map((ex) => (
                  <Pressable key={ex} style={styles.chip} onPress={() => submit(ex)}>
                    <Text style={styles.chipText}>{ex}</Text>
                  </Pressable>
                ))}
              </View>
            </View>
          )}

          {turns.map((t, i) => (
            <View key={i}>
              <Bubble role="user" text={t.query} />
              <Bubble role="assistant" text={t.response} />
              <AnswerCards cards={t.cards} />
            </View>
          ))}

          {pending && (
            <View>
              <Bubble role="user" text={pending} />
              {overlay === 'processing' && <TypingBubble />}
            </View>
          )}
        </ScrollView>

        {/* Context-aware quick replies */}
        {(turns.length > 0 || activeDestination) && (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            keyboardShouldPersistTaps="handled"
            style={styles.suggestions}
            contentContainerStyle={styles.suggestionsContent}
          >
            {suggestions.map((s) => (
              <Pressable key={s.label} style={styles.suggChip} onPress={() => submit(s.q)}>
                <Text style={styles.suggText}>{s.label}</Text>
              </Pressable>
            ))}
          </ScrollView>
        )}

        {/* Input bar */}
        <View style={styles.inputBar}>
          <TextInput
            style={styles.input}
            placeholder="Ask anything…"
            placeholderTextColor="#5b6770"
            value={text}
            onChangeText={setText}
            onSubmitEditing={() => submit(text)}
            returnKeyType="send"
            editable={!busy}
          />
          {hasNativeVoice && (
            <Pressable style={styles.micBtn} onPress={() => runVoiceQuery()} disabled={busy}>
              <Text style={styles.micIcon}>🎙</Text>
            </Pressable>
          )}
          <Pressable
            style={[styles.sendBtn, (busy || !text.trim()) && styles.sendBtnOff]}
            onPress={() => submit(text)}
            disabled={busy || !text.trim()}
          >
            <Text style={styles.sendIcon}>↑</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Bubble({ role, text }: { role: 'user' | 'assistant'; text: string }) {
  const isUser = role === 'user';
  return (
    <View style={[styles.bubbleRow, isUser ? styles.rowRight : styles.rowLeft]}>
      <View style={[styles.bubble, isUser ? styles.userBubble : styles.aiBubble]}>
        <Text style={isUser ? styles.userText : styles.aiText}>{text}</Text>
      </View>
    </View>
  );
}

function TypingBubble() {
  return (
    <View style={[styles.bubbleRow, styles.rowLeft]}>
      <View style={[styles.bubble, styles.aiBubble, styles.typing]}>
        <ActivityIndicator size="small" color="#8b98a9" />
        <Text style={styles.typingText}>  NavAI is thinking…</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#0a0e14' },
  // Location bar
  locBar: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 16,
    marginTop: 8,
    backgroundColor: '#151b24',
    borderRadius: 16,
    paddingVertical: 12,
    paddingHorizontal: 16,
    gap: 12,
  },
  pinDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: '#3b82f6' },
  locLabel: { color: '#6b7886', fontSize: 10, fontWeight: '700', letterSpacing: 1 },
  locRow: { flexDirection: 'row', alignItems: 'center', marginTop: 2 },
  locating: { color: '#8b98a9', fontSize: 15 },
  locText: { color: '#e6edf3', fontSize: 15, fontWeight: '600', marginTop: 2 },
  gear: { color: '#8b98a9', fontSize: 22, paddingHorizontal: 4 },
  // Header
  header: { paddingHorizontal: 20, paddingTop: 18, paddingBottom: 6 },
  brand: { color: '#fff', fontSize: 30, fontWeight: '800', letterSpacing: -0.5 },
  tagline: { color: '#6b7886', fontSize: 13, marginTop: 2 },
  // Conversation
  convo: { flex: 1 },
  convoContent: { padding: 16, paddingBottom: 8 },
  empty: { alignItems: 'center', marginTop: 48, paddingHorizontal: 16 },
  emptyTitle: { color: '#e6edf3', fontSize: 18, fontWeight: '700', textAlign: 'center' },
  emptySub: { color: '#6b7886', fontSize: 14, marginTop: 6, marginBottom: 24 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 10 },
  chip: {
    backgroundColor: '#151b24',
    borderColor: '#222c38',
    borderWidth: 1,
    borderRadius: 20,
    paddingVertical: 10,
    paddingHorizontal: 16,
  },
  chipText: { color: '#9fb1c4', fontSize: 14 },
  // Bubbles
  bubbleRow: { flexDirection: 'row', marginVertical: 5 },
  rowLeft: { justifyContent: 'flex-start' },
  rowRight: { justifyContent: 'flex-end' },
  bubble: { maxWidth: '82%', borderRadius: 18, paddingVertical: 11, paddingHorizontal: 15 },
  userBubble: { backgroundColor: '#2f6fed', borderBottomRightRadius: 5 },
  aiBubble: { backgroundColor: '#161d27', borderBottomLeftRadius: 5 },
  userText: { color: '#fff', fontSize: 16, lineHeight: 22 },
  aiText: { color: '#e6edf3', fontSize: 16, lineHeight: 23 },
  typing: { flexDirection: 'row', alignItems: 'center' },
  typingText: { color: '#8b98a9', fontSize: 15 },
  // Input
  suggestions: { maxHeight: 44, flexGrow: 0 },
  suggestionsContent: { paddingHorizontal: 12, gap: 8, alignItems: 'center' },
  suggChip: {
    backgroundColor: '#151b24',
    borderColor: '#222c38',
    borderWidth: 1,
    borderRadius: 18,
    paddingVertical: 8,
    paddingHorizontal: 14,
  },
  suggText: { color: '#9fb1c4', fontSize: 13, fontWeight: '600' },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 8,
    borderTopColor: '#161d27',
    borderTopWidth: 1,
    backgroundColor: '#0a0e14',
  },
  input: {
    flex: 1,
    backgroundColor: '#151b24',
    borderRadius: 22,
    paddingHorizontal: 18,
    paddingVertical: Platform.OS === 'ios' ? 12 : 8,
    color: '#fff',
    fontSize: 16,
  },
  micBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#151b24', alignItems: 'center', justifyContent: 'center' },
  micIcon: { fontSize: 20 },
  sendBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#2f6fed', alignItems: 'center', justifyContent: 'center' },
  sendBtnOff: { backgroundColor: '#1d2733' },
  sendIcon: { color: '#fff', fontSize: 22, fontWeight: '800' },
});
