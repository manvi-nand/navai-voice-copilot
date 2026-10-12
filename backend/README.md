# NavAI Backend

FastAPI voice pipeline + LangGraph ReAct agent. Holds **all** AI logic — the mobile
app is a thin voice I/O shell (doc §3.1).

## Quick start (mock-first, no keys)

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .                      # core deps
cp .env.example .env                  # USE_MOCKS=true by default

uvicorn app.main:app --reload         # http://localhost:8000
```

In another terminal, run the Week-2 agent smoke test:

```bash
python scripts/test_queries.py
```

You should see spoken-style answers and the tools each query fired — all offline.

## Going live

Set keys in `.env` and flip `USE_MOCKS=false`:

| Key | Enables |
|-----|---------|
| `GOOGLE_API_KEY` | Real Gemini 2.5 Flash ReAct agent (else offline heuristic router) |
| `SARVAM_API_KEY` | Real STT (`saaras:v3` translate) + TTS |
| `GOOGLE_MAPS_API_KEY` | Real Directions / Places / Geocoding |
| `OPENWEATHER_API_KEY` | Real weather/forecast |

## LiveKit (audio transport, Week 3)

```bash
docker compose up -d        # self-hosted LiveKit on :7880 (dev creds in livekit.yaml)
```

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | liveness + mock/model status |
| `POST /query` | text-test: transcript in → agent response (no audio) |
| `POST /livekit/token` | mint a join token for the drive's LiveKit room |
| `WS /ws/voice` | full pipeline over one WS (mock-friendly, used by tests) |
| `WS /ws/alerts` | Phase 2: backend pushes proactive traffic alerts |

## Layout

```
app/
  main.py            FastAPI endpoints (above)
  config.py          settings + USE_MOCKS switch
  pipeline/          vad.py · stt.py · tts.py   (Silero + Sarvam, mock-first)
  agent/             graph.py · tools.py · state.py · prompts.py  (LangGraph ReAct)
  services/          maps · places · weather · geocode · livekit  (mock-first)
  session/           in-memory session store (Redis-swappable)
  proactive.py       TrafficMonitor — background route watching (doc §2.8)
  room_agent.py      production LiveKit transport (joins room, runs pipeline)
tests/               pytest suite (run: pytest -q)
```

## How the agent works (doc §3.3)

Gemini reads the transcript + injected GPS + session context and chooses among seven
tools — no hardcoded routing. Without a `GOOGLE_API_KEY`, a deterministic keyword
router exercises the same tools so you can develop fully offline. The two paths are
interchangeable behind `run_agent()`.
```
get_directions · find_nearby_places · find_on_route_places · get_weather
geocode_place · save_place · get_session_context
```

## Transport

- `/ws/voice` carries audio over the WebSocket itself — simplest, fully offline-testable.
- For production WebRTC, run the room agent (real keys):
  `python -m app.room_agent --session <id>` — it joins the LiveKit room, subscribes to
  the mic track, and publishes TTS back. No LiveKit Agents framework (doc §3.2).
