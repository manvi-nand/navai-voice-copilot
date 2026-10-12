"""Session state store.

v1 is an in-memory dict behind a small interface so a Redis-backed
implementation can drop in later (doc Open Question #2 -> chose in-memory).

Holds per-drive: destination, saved places, conversation history, last-mentioned
place, language. Context expires after `session_ttl_minutes` of inactivity
(doc §2.5: resets when drive ends or app backgrounded > 30 min).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from app.config import settings


@dataclass
class SessionState:
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    # Multi-turn context
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    destination: Optional[dict[str, Any]] = None  # {name, lat, lng}
    last_place: Optional[dict[str, Any]] = None  # for "is it open?", "how far is it?"
    saved_places: dict[str, Any] = field(default_factory=dict)  # home, office, ...
    language: str = "en-IN"

    def touch(self) -> None:
        self.last_active = time.time()

    def is_expired(self, ttl_seconds: float) -> bool:
        return (time.time() - self.last_active) > ttl_seconds


class SessionStore:
    """In-memory session store. Swap for Redis by matching this interface."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get_or_create(self, session_id: str) -> SessionState:
        self._evict_expired()
        s = self._sessions.get(session_id)
        if s is None:
            s = SessionState(session_id=session_id)
            self._sessions[session_id] = s
        s.touch()
        return s

    def get(self, session_id: str) -> Optional[SessionState]:
        s = self._sessions.get(session_id)
        if s and s.is_expired(settings.session_ttl_minutes * 60):
            self._sessions.pop(session_id, None)
            return None
        return s

    def end(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def _evict_expired(self) -> None:
        ttl = settings.session_ttl_minutes * 60
        expired = [sid for sid, s in self._sessions.items() if s.is_expired(ttl)]
        for sid in expired:
            self._sessions.pop(sid, None)


# Process-wide singleton for v1.
store = SessionStore()
