"""NavAI backend — FastAPI app.

Endpoints:
  GET  /health            liveness
  POST /query             text-test path: transcript in -> agent response (no audio).
                          Lets Week-2 agent work be tested without the mobile app.
  WS   /ws/voice          full voice pipeline: audio frames in -> VAD -> STT ->
                          agent -> TTS audio out. Mock-first so it runs offline.

A custom asyncio WebSocket handler is used deliberately — push-to-talk means one
discrete round trip per query, so no pipeline framework is needed (doc §3.2).
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from app.agent.graph import run_agent
from app.config import settings
from app.models import (
    AgentResponse,
    ErrorEvent,
    LatLng,
    QueryPayload,
    TokenRequest,
    TokenResponse,
)
from app.pipeline.stt import transcribe
from app.pipeline.tts import synthesize
from app.pipeline.vad import VAD
from app.proactive import registry
from app.services.livekit import create_access_token, room_name
from app.session.store import store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("navai")

app = FastAPI(title=settings.app_name)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "mocks": settings.use_mocks, "model": settings.gemini_model}


@app.post("/query", response_model=AgentResponse)
async def query(payload: QueryPayload) -> AgentResponse:
    """Text-test path: skip STT/TTS, run the agent directly."""
    session = store.get_or_create(payload.session_id)
    session.language = payload.language
    resp = await run_agent(payload, session)
    # Start/refresh proactive monitoring if this turn set a destination (doc §2.8).
    loc = {"lat": payload.current_location.lat, "lng": payload.current_location.lng}
    registry.ensure(session, loc)
    return resp


@app.get("/directions")
async def directions_endpoint(
    from_lat: float, from_lng: float, to_lat: float, to_lng: float,
    avoid_highways: bool = False,
) -> dict:
    """Live ETA between two points — used by the app's active-destination card to
    refresh without going through the agent."""
    from app.services.maps import get_directions

    return await get_directions(
        {"lat": from_lat, "lng": from_lng},
        {"lat": to_lat, "lng": to_lng},
        avoid_highways=avoid_highways,
    )


@app.get("/reverse_geocode")
async def reverse_geocode_endpoint(lat: float, lng: float) -> dict:
    """Coordinates -> human address, for the app's current-location bar."""
    from app.services.geocode import reverse_geocode

    return await reverse_geocode(lat, lng)


@app.get("/tts")
async def tts(text: str, language: str = "en-IN") -> Response:
    """Return spoken audio (WAV) for `text`. Lets clients that can't stream audio
    over WebRTC (e.g. the Expo Go demo build) still play real spoken answers."""
    audio = b"".join([chunk async for chunk in synthesize(text, language)])
    return Response(content=audio, media_type="audio/wav")


@app.post("/livekit/token", response_model=TokenResponse)
async def livekit_token(req: TokenRequest) -> TokenResponse:
    """Mint a join token for the app's per-drive LiveKit room."""
    return TokenResponse(
        token=create_access_token(req.session_id, req.identity),
        url=settings.livekit_url,
        room=room_name(req.session_id),
    )


@app.websocket("/ws/alerts")
async def alerts(ws: WebSocket) -> None:
    """Phase 2: app connects here for the drive; backend pushes proactive traffic
    alerts as they fire. Each alert carries spoken text the app sends to TTS."""
    await ws.accept()
    session_id = ws.query_params.get("session_id", "")
    session = store.get_or_create(session_id)
    loc_lat = float(ws.query_params.get("lat", 12.97))
    loc_lng = float(ws.query_params.get("lng", 77.59))
    monitor = registry.ensure(session, {"lat": loc_lat, "lng": loc_lng})
    try:
        while True:
            alert = await monitor.queue.get()
            await ws.send_json(alert)
    except (WebSocketDisconnect, RuntimeError):
        logger.info("alerts client disconnected")


@app.websocket("/ws/voice")
async def voice(ws: WebSocket) -> None:
    """One push-to-talk round trip.

    Protocol (mock-friendly):
      client -> {"type":"start", "session_id", "lat", "lng"}
      client -> binary audio frames (16kHz mono PCM)
      client -> {"type":"end"}            (or VAD fires server-side)
      server -> {"type":"transcript", "text"}
      server -> {"type":"response", "text", "tool_calls"}
      server -> binary TTS audio chunks
      server -> {"type":"done"}
    """
    await ws.accept()
    vad = VAD()
    audio_buf = bytearray()
    ctx: dict = {}
    try:
        while True:
            msg = await ws.receive()
            if "text" in msg and msg["text"] is not None:
                evt = _json(msg["text"])
                if evt.get("type") == "start":
                    ctx = evt
                    audio_buf.clear()
                    vad.reset()
                elif evt.get("type") == "end":
                    await _finish(ws, bytes(audio_buf), ctx)
                    audio_buf.clear()
            elif "bytes" in msg and msg["bytes"] is not None:
                frame = msg["bytes"]
                audio_buf.extend(frame)
                if vad.process(frame):  # server-side end-of-speech
                    await _finish(ws, bytes(audio_buf), ctx)
                    audio_buf.clear()
    except (WebSocketDisconnect, RuntimeError):
        # RuntimeError: receive() after the peer already sent a disconnect.
        logger.info("client disconnected")


async def _finish(ws: WebSocket, audio: bytes, ctx: dict) -> None:
    if not ctx.get("session_id"):
        await ws.send_json(ErrorEvent(code="no_session", message="missing start event").model_dump())
        return
    stt = await transcribe(audio, settings.vad_sample_rate)
    await ws.send_json({"type": "transcript", "text": stt["transcript"]})

    payload = QueryPayload(
        transcript=stt["transcript"],
        current_location=LatLng(lat=ctx.get("lat", 12.97), lng=ctx.get("lng", 77.59)),
        session_id=ctx["session_id"],
        language=stt["language"],
    )
    session = store.get_or_create(payload.session_id)
    session.language = payload.language
    resp = await run_agent(payload, session)
    registry.ensure(session, {"lat": payload.current_location.lat, "lng": payload.current_location.lng})
    await ws.send_json(
        {
            "type": "response",
            "text": resp.response_text,
            "tool_calls": resp.tool_calls,
            "saved_place": resp.saved_place,
        }
    )

    async for chunk in synthesize(resp.response_text, resp.language):
        await ws.send_bytes(chunk)
    await ws.send_json({"type": "done"})


def _json(s: str) -> dict:
    import json

    try:
        return json.loads(s)
    except Exception:  # noqa: BLE001
        return {}
