"""Sarvam TTS client (doc §3.2 step 9).

Streams audio chunks for the response text, in the language the question was asked
in (doc §2.6). Mock-first: yields a short silent PCM buffer so playback wiring can
be tested without a key.
"""
from __future__ import annotations

import logging
from typing import AsyncIterator

from app.config import settings

logger = logging.getLogger(__name__)

# Sarvam bulbul:v2 speakers are language-agnostic (one voice covers all supported
# Indian languages), so we use a single default. Override per language if desired.
# Valid speakers include: anushka, manisha, vidya, arya, abhilash, karun, hitesh.
_DEFAULT_SPEAKER = "anushka"
_VOICE_BY_LANG: dict[str, str] = {}


async def synthesize(text: str, language: str = "en-IN") -> AsyncIterator[bytes]:
    """Yield audio chunks (PCM/Opus) for `text` in the given language."""
    if settings.use_mocks:
        # 100ms of silence at 16kHz mono 16-bit as a stand-in chunk.
        yield b"\x00\x00" * 1600
        return
    async for chunk in _real_synthesize(text, language):
        yield chunk


async def _real_synthesize(text: str, language: str) -> AsyncIterator[bytes]:
    # Sarvam TTS returns base64-encoded WAV audio in JSON. For lower latency in v2,
    # switch to Sarvam's streaming TTS WebSocket and yield frames as they arrive.
    import base64

    import httpx

    url = "https://api.sarvam.ai/text-to-speech"
    headers = {"api-subscription-key": settings.sarvam_api_key}
    body = {
        "inputs": [text],
        "target_language_code": language,
        "speaker": _VOICE_BY_LANG.get(language, _DEFAULT_SPEAKER),
        "model": "bulbul:v2",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(url, headers=headers, json=body)
        r.raise_for_status()
        for b64 in r.json().get("audios", []):
            yield base64.b64decode(b64)
