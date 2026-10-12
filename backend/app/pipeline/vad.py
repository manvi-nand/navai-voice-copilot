"""Silero VAD wrapper — server-side end-of-speech detection (doc §3.2 step 4).

Mock-first: when use_mocks is on (or torch isn't installed), a length-based
heuristic stands in so the pipeline runs without the model.
"""
from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)


class VAD:
    """Streaming VAD. Feed 16kHz mono PCM frames; it reports end-of-speech after
    `vad_silence_ms` of trailing silence."""

    def __init__(self) -> None:
        self._model = None
        self._silence_ms = 0
        self._speech_started = False
        if not settings.use_mocks:
            self._load_model()

    def _load_model(self) -> None:
        try:
            import torch

            model, _ = torch.hub.load(
                "snakers4/silero-vad", "silero_vad", trust_repo=True
            )
            self._model = model
        except Exception:  # noqa: BLE001
            logger.warning("Silero VAD unavailable, falling back to heuristic VAD")
            self._model = None

    def reset(self) -> None:
        self._silence_ms = 0
        self._speech_started = False

    def is_speech(self, frame_pcm: bytes) -> bool:
        """Return True if `frame_pcm` contains speech."""
        if self._model is None:
            # Heuristic: nonzero energy => speech.
            return any(b != 0 for b in frame_pcm[:64])
        import torch

        audio = torch.frombuffer(frame_pcm, dtype=torch.int16).float() / 32768.0
        prob = self._model(audio, settings.vad_sample_rate).item()
        return prob > 0.5

    def process(self, frame_pcm: bytes, frame_ms: int = 30) -> bool:
        """Feed one frame. Returns True when end-of-speech is detected."""
        if self.is_speech(frame_pcm):
            self._speech_started = True
            self._silence_ms = 0
            return False
        if self._speech_started:
            self._silence_ms += frame_ms
            if self._silence_ms >= settings.vad_silence_ms:
                self.reset()
                return True
        return False
