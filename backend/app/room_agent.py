"""Backend LiveKit room agent — the production audio transport (doc §3.1, §3.2).

This is the server side of the LiveKit path: the agent joins a drive's room as a
participant, subscribes to the user's mic track, runs the same pipeline used by
/ws/voice (VAD -> Sarvam STT -> LangGraph agent -> Sarvam TTS), publishes the answer
back as an audio track, and sends control events (transcript/response/done) as data
packets.

Deliberately NOT built on the LiveKit Agents framework — push-to-talk is one discrete
round trip per query, so a plain rtc participant loop is enough and simpler (doc §3.2).

Run a worker that serves rooms on demand:
    python -m app.room_agent --session <session_id>
or dispatch `serve_room(session_id, location)` from a join webhook.

Requires the `livekit` (rtc) SDK and real keys; it does nothing in mock mode.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging

from app.agent.graph import run_agent
from app.config import settings
from app.models import LatLng, QueryPayload
from app.pipeline.stt import transcribe
from app.pipeline.tts import synthesize
from app.pipeline.vad import VAD
from app.services.livekit import create_agent_token
from app.session.store import store

logger = logging.getLogger("navai.room_agent")

SAMPLE_RATE = 16000
NUM_CHANNELS = 1


async def serve_room(session_id: str, location: dict) -> None:
    """Join the room for `session_id` and serve queries until the user leaves."""
    from livekit import rtc

    room = rtc.Room()
    audio_source = rtc.AudioSource(SAMPLE_RATE, NUM_CHANNELS)
    tts_track = rtc.LocalAudioTrack.create_audio_track("navai-tts", audio_source)

    @room.on("track_subscribed")
    def _on_track(track, publication, participant):  # noqa: ANN001
        if track.kind == rtc.TrackKind.KIND_AUDIO and participant.identity != "navai-agent":
            asyncio.create_task(
                _consume_user_audio(room, track, session_id, location, audio_source)
            )

    await room.connect(settings.livekit_url, create_agent_token(session_id))
    await room.local_participant.publish_track(tts_track)
    logger.info("room agent joined %s", session_id)

    # Stay alive while the room has the user in it.
    disconnected = asyncio.Event()
    room.on("disconnected", lambda *_: disconnected.set())
    await disconnected.wait()


async def _consume_user_audio(room, track, session_id, location, audio_source) -> None:
    """Read mic frames, detect end-of-speech, then run one query round trip."""
    from livekit import rtc

    vad = VAD()
    buf = bytearray()
    stream = rtc.AudioStream(track)
    async for event in stream:
        frame: rtc.AudioFrame = event.frame
        pcm = bytes(frame.data)
        buf.extend(pcm)
        if vad.process(pcm, frame_ms=int(frame.samples_per_channel / SAMPLE_RATE * 1000)):
            await _handle_turn(room, bytes(buf), session_id, location, audio_source)
            buf.clear()


async def _handle_turn(room, audio, session_id, location, audio_source) -> None:
    from livekit import rtc

    stt = await transcribe(audio, SAMPLE_RATE)
    await _publish_data(room, {"type": "transcript", "text": stt["transcript"]})

    session = store.get_or_create(session_id)
    payload = QueryPayload(
        transcript=stt["transcript"],
        current_location=LatLng(**location),
        session_id=session_id,
        language=stt["language"],
        saved_places={k: v for k, v in session.saved_places.items()},  # already synced
    )
    resp = await run_agent(payload, session)
    await _publish_data(
        room,
        {"type": "response", "text": resp.response_text,
         "tool_calls": resp.tool_calls, "saved_place": resp.saved_place},
    )

    async for chunk in synthesize(resp.response_text, resp.language):
        frame = rtc.AudioFrame(
            data=chunk, sample_rate=SAMPLE_RATE, num_channels=NUM_CHANNELS,
            samples_per_channel=len(chunk) // 2,
        )
        await audio_source.capture_frame(frame)
    await _publish_data(room, {"type": "done"})


async def _publish_data(room, msg: dict) -> None:
    await room.local_participant.publish_data(json.dumps(msg).encode())


def _main() -> None:
    if settings.use_mocks:
        raise SystemExit("room agent needs real keys; set USE_MOCKS=false")
    p = argparse.ArgumentParser()
    p.add_argument("--session", required=True)
    p.add_argument("--lat", type=float, default=12.97)
    p.add_argument("--lng", type=float, default=77.59)
    args = p.parse_args()
    asyncio.run(serve_room(args.session, {"lat": args.lat, "lng": args.lng}))


if __name__ == "__main__":
    _main()
