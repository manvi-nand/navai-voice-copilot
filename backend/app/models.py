"""Wire models for the audio message payload (doc §5.1) and API responses."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class LatLng(BaseModel):
    lat: float
    lng: float


class SavedPlace(BaseModel):
    name: str
    lat: float
    lng: float


class QueryPayload(BaseModel):
    """Assembled by the backend after VAD end-of-speech, before invoking the agent.

    For the text-test path the client can post this directly with `transcript`
    already filled in, skipping STT.
    """

    transcript: str = Field(..., description="English text of what the user said")
    current_location: LatLng = Field(..., description="GPS at time of query")
    session_id: str = Field(..., description="App-generated UUID per drive")
    language: str = Field("en-IN", description="Detected language for TTS voice")
    # Source of truth lives on the device (doc §5.1); the app syncs it each query so
    # the agent can resolve 'home' / 'office' without coordinates.
    saved_places: dict[str, SavedPlace] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    response_text: str
    language: str
    tool_calls: list[str] = Field(default_factory=list)
    session_id: str
    # When the agent saved a place this turn, the app persists it to device storage.
    saved_place: Optional[dict] = None
    # Structured tool results for rich client cards (route/weather/places).
    cards: list[dict] = Field(default_factory=list)


class TokenRequest(BaseModel):
    session_id: str
    identity: str = "navai-user"


class TokenResponse(BaseModel):
    token: str
    url: str
    room: str


class ErrorEvent(BaseModel):
    type: str = "error"
    code: str
    message: str
