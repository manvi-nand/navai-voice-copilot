"""Agent + tool routing tests (offline heuristic path, mocks on)."""
import uuid

import pytest

from app.models import LatLng, QueryPayload
from app.session.store import SessionState

BLR = LatLng(lat=12.9716, lng=77.5946)


def _payload(text: str, sid: str, **kw) -> QueryPayload:
    return QueryPayload(transcript=text, current_location=BLR, session_id=sid, **kw)


@pytest.fixture
def session():
    return SessionState(session_id=str(uuid.uuid4()))


async def test_directions(session):
    from app.agent.graph import run_agent

    r = await run_agent(_payload("How long to Koramangala?", session.session_id), session)
    assert "get_directions" in r.tool_calls
    assert "minutes" in r.response_text
    assert session.destination["name"].lower().startswith("koramangala")


async def test_multiturn_followup_resolves_destination(session):
    from app.agent.graph import run_agent

    await run_agent(_payload("How long to the airport?", session.session_id), session)
    r = await run_agent(_payload("What about avoiding the highway?", session.session_id), session)
    assert "get_directions" in r.tool_calls
    assert "service road" in r.response_text


async def test_nearby_places(session):
    from app.agent.graph import run_agent

    r = await run_agent(_payload("Is there a pharmacy near me?", session.session_id), session)
    assert "find_nearby_places" in r.tool_calls
    assert session.last_place is not None


async def test_weather(session):
    from app.agent.graph import run_agent

    r = await run_agent(_payload("Will it rain before I reach home?", session.session_id), session)
    assert "get_weather" in r.tool_calls


async def test_save_place_surfaces_for_persistence(session):
    from app.agent.graph import run_agent

    r = await run_agent(_payload("Save this as my office", session.session_id), session)
    assert "save_place" in r.tool_calls
    assert r.saved_place is not None
    assert "office" in session.saved_places


async def test_saved_place_resolves_home(session):
    from app.agent.graph import run_agent
    from app.models import SavedPlace

    p = _payload(
        "How long to home?",
        session.session_id,
        saved_places={"home": SavedPlace(name="Home", lat=12.93, lng=77.62)},
    )
    r = await run_agent(p, session)
    assert "get_session_context" in r.tool_calls
    assert "get_directions" in r.tool_calls


async def test_on_route_detour(session):
    from app.agent.graph import run_agent

    await run_agent(_payload("How long to the airport?", session.session_id), session)
    r = await run_agent(_payload("Add a coffee stop on my way", session.session_id), session)
    assert "find_on_route_places" in r.tool_calls
    assert "minutes" in r.response_text
