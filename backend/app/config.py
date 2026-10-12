"""Central configuration. All secrets come from environment / .env.

Mock-first: when USE_MOCKS is true (the default), external service clients
return canned, realistic responses so the whole pipeline runs offline without
any API keys. Flip USE_MOCKS=false and supply keys to hit real APIs.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- General ---
    app_name: str = "NavAI"
    environment: str = "dev"
    # Mock-first development: no external calls when true.
    use_mocks: bool = True

    # --- LLM (Gemini 2.5 Flash) ---
    google_api_key: str = ""  # also used for Maps/Places/Geocoding if shared
    gemini_model: str = "gemini-2.5-flash"
    # Wraps the whole ReAct loop (LLM turns + tool round trips), so it's larger than
    # the doc's per-call 5s budget (§9). Tune down once streaming lands in v2.
    llm_timeout_s: float = 20.0

    # --- Sarvam (STT + TTS) ---
    sarvam_api_key: str = ""
    sarvam_stt_model: str = "saaras:v3"

    # --- Google Maps Platform (Routes, Places New, Geocoding, Weather) ---
    google_maps_api_key: str = ""

    # --- OpenWeatherMap (deprecated: weather now uses the Google Weather API) ---
    openweather_api_key: str = ""

    # --- LiveKit (self-hosted via docker-compose for dev) ---
    livekit_url: str = "ws://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "secret"

    # --- VAD ---
    vad_silence_ms: int = 800  # single biggest tuning lever (doc §8); 1000-1200 in-car
    vad_sample_rate: int = 16000

    # --- Session ---
    session_ttl_minutes: int = 30  # context resets after 30m background (doc §2.5)

    def maps_key(self) -> str:
        return self.google_maps_api_key or self.google_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
