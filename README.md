# NavAI — Hands-Free Voice Travel Companion

A native mobile voice assistant for hands-free driving in Indian cities. Say a wake
word, ask a natural question, hear a spoken answer — eyes stay on the road. Understands
Indian languages, follows up across turns, gets smarter about your routes over time.

> Personal project. Targets free API tiers. See `NavAI_TechProductDoc.pdf` for the full
> product & technical design.

## Architecture

Two parts that talk over WebSocket (audio) + HTTP. **All AI logic lives in the backend**;
the app is a thin voice I/O shell.

```
 ┌─────────────── Mobile (React Native + Expo) ───────────────┐
 │  Porcupine wake word · mic · GPS · Reanimated overlay ·     │
 │  LiveKit client · audio ducking · Zustand                   │
 └───────────────┬───────────────────────────────▲────────────┘
        audio (LiveKit / WS)              TTS audio + events
 ┌───────────────▼───────────────────────────────┴────────────┐
 │  Backend (FastAPI)                                          │
 │  Silero VAD → Sarvam STT (saaras:v3, translate) →           │
 │  LangGraph ReAct agent (Gemini 2.5 Flash) → Sarvam TTS      │
 │  Tools: directions · places · weather · geocode · session   │
 └─────────────────────────────────────────────────────────────┘
```

Target voice-to-voice latency: **< 2 seconds** (doc §8).

## Repo layout

```
backend/    FastAPI + LangGraph agent + voice pipeline   (build first — testable now)
mobile/     Expo app shell — overlay, LiveKit, wake word, GPS
```

## Start here

**Backend is fully runnable today, offline, with no API keys** (mock-first):

```bash
cd backend && python3.11 -m venv .venv && source .venv/bin/activate
pip install -e . && cp .env.example .env
uvicorn app.main:app --reload
python scripts/test_queries.py     # see the agent + tools answer queries
```

Then `mobile/` once you want the on-device experience: replace `YOUR_LOCAL_IP` in `mobile/app.json` with your computer's LAN IP, then `cd mobile && npm install && npx expo start`.

## Build plan (doc §7)

- **Week 1 — Backend voice pipeline** ✅ WS endpoint, VAD, Sarvam STT/TTS clients, echo via `/ws/voice`. Verified offline.
- **Week 2 — LangGraph agent + tools** ✅ `/query` text-test path; **7 tools** (5 core + `save_place`, `find_on_route_places`); real Gemini ReAct loop wired (drop in `GOOGLE_API_KEY`), offline heuristic fallback. Verified.
- **Week 3 — RN app shell** ✅ overlay state machine, Zustand store, GPS, ducking, **real LiveKit room client** (join, publish mic, receive agent audio + data events), `/livekit/token` endpoint. *Needs a device/simulator to exercise.*
- **Week 4 — Wake word + polish** ✅ Porcupine wiring + toggle, multilingual TTS voice selection, settings screen. *Needs a trained "Hey Nav" `.ppn` + in-car VAD tuning.*
- **Phase 2** ✅ saved places (voice-set + AsyncStorage persistence + sync), proactive traffic alerts (`/ws/alerts` + background `TrafficMonitor`), on-route detours. Logic verified by tests.

### Transport: two paths
- **`/ws/voice`** — audio over the same WebSocket. The simplest path; **fully runnable offline with mocks** and used for the smoke tests.
- **LiveKit room** (`app/room_agent.py` + mobile `lib/livekit.ts`) — the production WebRTC transport per the doc. Backend agent joins the room, subscribes to mic, publishes TTS. Needs real keys.

### Resolved open questions (doc §10)
Wake word → custom "Hey Nav" · Session store → in-memory (Redis-swappable) ·
LiveKit → self-hosted Docker for dev · Response language → match query language via Sarvam TTS.

## Tests
```bash
cd backend && pytest -q     # 11 tests: agent routing, multi-turn, Phase 2, session TTL, LiveKit token
```

## Status legend
✅ implemented & verified offline · needs device/keys where noted.
```
