"""LangGraph state schema (doc §5.2)."""
from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class NavState(TypedDict, total=False):
    # Conversation messages (drives the ReAct loop).
    messages: Annotated[list, add_messages]
    # Request context, injected from session + GPS every turn.
    transcript: str  # current query
    current_location: dict  # { lat, lng }
    session_id: str  # drive session identifier
    conversation_history: list  # prior turns
    saved_places: dict  # home, office, custom
    tool_results: list  # outputs from tool calls
    response_text: str  # final response for TTS
    language: str  # detected language code
