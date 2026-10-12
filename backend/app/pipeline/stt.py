"""Sarvam saaras:v3 STT client (doc §3.2 step 5).

Streaming WebSocket STT in translate mode: Indian-language audio in, English
transcript + detected-language metadata out.

Mock-first: returns a canned transcript so the pipeline runs without a key.
"""
from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)


async def transcribe(audio_pcm: bytes, sample_rate: int = 16000) -> dict:
    """Return {transcript, language}. `language` is the detected source language
    (used to pick the TTS voice), while transcript is translated to English."""
    if settings.use_mocks:
        return {
            "transcript": "How long to Koramangala in this traffic?",
            "language": "en-IN",
        }
    return await _real_transcribe(audio_pcm, sample_rate)


async def _real_transcribe(audio_pcm: bytes, sample_rate: int) -> dict:
    # TODO: connect to Sarvam streaming STT WebSocket with translate mode.
    # Docs: https://docs.sarvam.ai  (model: saaras:v3)
    # Push audio frames, read partial + final transcripts, return final + language.
    import httpx

    url = "https://api.sarvam.ai/speech-to-text-translate"
    headers = {"api-subscription-key": settings.sarvam_api_key}
    files = {"file": ("audio.wav", audio_pcm, "audio/wav")}
    data = {"model": settings.sarvam_stt_model}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(url, headers=headers, files=files, data=data)
        r.raise_for_status()
        payload = r.json()
    return {
        "transcript": payload.get("transcript", ""),
        "language": payload.get("language_code", "en-IN"),
    }
