"""LiveKit access-token minting (doc §4.1 transport).

The mobile app asks the backend for a short-lived JWT to join its per-drive room,
then streams mic audio in and receives the agent's TTS audio track back. Keys never
leave the backend.
"""
from __future__ import annotations

from app.config import settings


def room_name(session_id: str) -> str:
    return f"navai-{session_id}"


def create_access_token(session_id: str, identity: str = "navai-user") -> str:
    """Mint a join token for the session's room (mobile app or backend agent)."""
    from livekit import api

    room = room_name(session_id)
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room,
                can_publish=True,
                can_subscribe=True,
            )
        )
        .to_jwt()
    )
    return token


def create_agent_token(session_id: str) -> str:
    """Token for the backend room agent participant."""
    return create_access_token(session_id, identity="navai-agent")
