// Backend HTTP client. The app only ever talks to our backend — never to Sarvam,
// Google, or Gemini directly (doc §3.1).
import Constants from 'expo-constants';

const HTTP =
  (Constants.expoConfig?.extra?.backendHttpUrl as string) ?? 'http://localhost:8000';

export interface LiveKitToken {
  token: string;
  url: string;
  room: string;
}

export async function fetchLiveKitToken(sessionId: string): Promise<LiveKitToken> {
  const r = await fetch(`${HTTP}/livekit/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, identity: 'navai-user' }),
  });
  if (!r.ok) throw new Error(`token ${r.status}`);
  return r.json();
}

export interface ReverseGeocode {
  address: string;
  short: string;
}

export async function reverseGeocode(lat: number, lng: number): Promise<ReverseGeocode> {
  const r = await fetch(`${HTTP}/reverse_geocode?lat=${lat}&lng=${lng}`);
  if (!r.ok) throw new Error(`reverse_geocode ${r.status}`);
  return r.json();
}

export async function getDirections(
  fromLat: number,
  fromLng: number,
  toLat: number,
  toLng: number,
): Promise<any> {
  const r = await fetch(
    `${HTTP}/directions?from_lat=${fromLat}&from_lng=${fromLng}&to_lat=${toLat}&to_lng=${toLng}`,
  );
  if (!r.ok) throw new Error(`directions ${r.status}`);
  return r.json();
}

// Text-test path (handy for debugging the agent without audio).
export async function postQuery(body: {
  transcript: string;
  current_location: { lat: number; lng: number };
  session_id: string;
  language?: string;
  saved_places?: Record<string, { name: string; lat: number; lng: number }>;
}) {
  const r = await fetch(`${HTTP}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return r.json();
}
