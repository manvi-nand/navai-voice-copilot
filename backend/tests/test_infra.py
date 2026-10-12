"""Session store, LiveKit token, and proactive monitor tests."""
import time
import uuid

import pytest

from app.session.store import SessionState, SessionStore


def test_session_expiry(monkeypatch):
    store = SessionStore()
    s = store.get_or_create("drive-1")
    assert store.get("drive-1") is s
    # Force last_active into the past beyond TTL.
    s.last_active = time.time() - 31 * 60
    assert store.get("drive-1") is None


def test_session_remembers_context():
    s = SessionState(session_id="d")
    s.destination = {"name": "Airport", "lat": 13.2, "lng": 77.7}
    s.last_place = {"name": "Starbucks"}
    assert s.destination["name"] == "Airport"


def test_livekit_token_roundtrip():
    jwt_pkg = pytest.importorskip("jwt")
    from app.services.livekit import create_access_token, room_name

    sid = str(uuid.uuid4())
    token = create_access_token(sid, "tester")
    decoded = jwt_pkg.decode(token, "secret", algorithms=["HS256"])
    assert decoded["video"]["room"] == room_name(sid)
    assert decoded["video"]["roomJoin"] is True


async def test_proactive_alert_on_worsening_traffic(monkeypatch):
    from app import proactive
    from app.services import maps as maps_svc
    from app.session.store import SessionState

    session = SessionState(session_id="p")
    session.destination = {"name": "Koramangala", "lat": 12.93, "lng": 77.62}

    etas = iter([20, 30])  # baseline then worsened

    async def fake_directions(origin, destination, avoid_highways=False, depart_in_minutes=0):
        if avoid_highways:
            return {"duration_in_traffic_min": 22, "summary": "service road"}
        return {"duration_in_traffic_min": next(etas), "summary": "Hosur Road"}

    monkeypatch.setattr(maps_svc, "get_directions", fake_directions)

    mon = proactive.Monitor(session=session)
    mon._loc = {"lat": 12.97, "lng": 77.59}
    await mon._check()  # baseline
    await mon._check()  # worsened -> alert
    alert = mon.queue.get_nowait()
    assert alert["type"] == "proactive"
    assert "saves" in alert["text"]
