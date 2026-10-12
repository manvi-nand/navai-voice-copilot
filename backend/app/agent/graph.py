"""LangGraph ReAct agent (doc §3.3).

Two execution paths:
  * Real: Gemini 2.5 Flash via langchain-google-genai, wired into LangGraph's
    prebuilt ReAct agent. Used when GOOGLE_API_KEY is set.
  * Offline heuristic: a deterministic keyword router that calls the same tools and
    fills response templates. Used when no key is present, so Week-2 work is testable
    fully offline. Replaced transparently the moment a key is provided.
"""
from __future__ import annotations

import asyncio
import logging

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import build_tools
from app.config import settings
from app.models import AgentResponse, QueryPayload
from app.session.store import SessionState

logger = logging.getLogger(__name__)


async def run_agent(payload: QueryPayload, session: SessionState) -> AgentResponse:
    loc = {"lat": payload.current_location.lat, "lng": payload.current_location.lng}
    # Sync device-owned saved places into session so 'home'/'office' resolve (doc §5.1).
    if payload.saved_places:
        session.saved_places.update(
            {k: v.model_dump() for k, v in payload.saved_places.items()}
        )
    before_saved = set(session.saved_places)
    cards: list[dict] = []
    tools = build_tools(loc, session, cards)

    session.conversation_history.append({"role": "user", "text": payload.transcript})
    try:
        # Gemini is an external call, so it stays behind USE_MOCKS. Mock mode (or no
        # key) uses the deterministic offline router.
        if settings.google_api_key and not settings.use_mocks:
            text, calls = await _run_gemini(payload, session, tools)
        else:
            text, calls = await _run_heuristic(payload, session, tools)
    except asyncio.TimeoutError:
        text, calls = "I couldn't process that, try again.", []
    except Exception:  # noqa: BLE001 — agent must never crash the pipeline (doc §9)
        logger.exception("agent error")
        text, calls = "Something went wrong, try again.", []

    session.conversation_history.append({"role": "assistant", "text": text})
    # If a place was saved this turn, tell the app to persist it.
    new_labels = set(session.saved_places) - before_saved
    saved_place = session.saved_places[next(iter(new_labels))] if new_labels else None
    return AgentResponse(
        response_text=text,
        language=payload.language,
        tool_calls=calls,
        session_id=payload.session_id,
        saved_place=saved_place,
        cards=cards,
    )


async def _run_gemini(payload, session, tools):
    """Real ReAct path."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langgraph.prebuilt import create_react_agent

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0.2,
    )
    agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)

    history = [(m["role"], m["text"]) for m in session.conversation_history[-8:]]
    inputs = {
        "messages": history
        + [("user", f"[GPS {payload.current_location.lat},{payload.current_location.lng}] "
                    f"{payload.transcript}")]
    }
    result = await asyncio.wait_for(
        agent.ainvoke(inputs), timeout=settings.llm_timeout_s
    )
    msgs = result["messages"]
    calls = [
        tc["name"]
        for m in msgs
        for tc in getattr(m, "tool_calls", []) or []
    ]
    return _content_to_text(msgs[-1].content), calls


def _content_to_text(content) -> str:
    """Normalize an LLM message's content to a plain string.

    Gemini (and other multimodal models) may return content as a list of blocks,
    e.g. [{"type": "text", "text": "..."}], instead of a bare string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
        return " ".join(p for p in parts if p).strip()
    return str(content)


async def _run_heuristic(payload, session, tools):
    """Offline keyword router exercising the real tools with template responses."""
    q = payload.transcript.lower()
    tool = {t.name: t for t in tools}
    calls: list[str] = []

    async def call(name, **kw):
        calls.append(name)
        t = tool[name]
        return await t.ainvoke(kw) if t.coroutine else t.invoke(kw)

    # Save place: "save this as my office"
    if "save" in q and ("home" in q or "office" in q or "this as" in q):
        label = "home" if "home" in q else "office" if "office" in q else "this place"
        await call("save_place", label=label)
        return f"Saved this location as your {label}.", calls

    # On-route detour: "add a coffee stop on my way"
    if ("on my way" in q or "on the way" in q or ("add" in q and "stop" in q)):
        ptype = next((w for w in ("coffee", "petrol", "pharmacy", "restaurant", "atm") if w in q), "coffee")
        res = await call("find_on_route_places", place_type=ptype)
        if not res or "error" in res[0]:
            return "Set a destination first, then I can find a stop on your way.", calls
        best = min(res, key=lambda r: r["added_minutes"])
        return (f"{best['name']} adds {best['added_minutes']} minutes versus "
                f"{max(r['added_minutes'] for r in res)} for the other — want me to add it?"), calls

    # Weather
    if any(w in q for w in ("rain", "weather", "umbrella")):
        at_dest = any(w in q for w in ("home", "office", "airport", "reach", "destination"))
        if "home" in q or "office" in q:
            await call("get_session_context", key="home" if "home" in q else "office")
        res = await call("get_weather", at_destination=at_dest)
        return res.get("summary", "Weather unavailable."), calls

    # Nearby places
    if any(w in q for w in ("near me", "nearby", "find a", "is there a", "petrol", "pharmacy", "restaurant", "coffee", "atm")):
        ptype = next((w for w in ("petrol", "pharmacy", "restaurant", "coffee", "atm") if w in q), "petrol")
        res = await call("find_nearby_places", query=ptype)
        if not res:
            return f"No {ptype} found within 2 kilometres.", calls
        top = res[0]
        status = "open" if top["open_now"] else "closed"
        return (f"{top['name']} is about {top['distance_km']} kilometres "
                f"away, and it's {status}."), calls

    # Directions / ETA
    avoid = "highway" in q and ("avoid" in q or "service" in q)
    dest_name = session.destination["name"] if session.destination else None
    for known in ("koramangala", "indiranagar", "airport", "whitefield", "mg road", "electronic city", "home", "office"):
        if known in q:
            if known in ("home", "office"):
                ctx = await call("get_session_context", key=known)
                dest_name = ctx.get("name") if isinstance(ctx, dict) and "name" in ctx else known
            else:
                dest_name = known
            break
    if dest_name:
        res = await call("get_directions", destination=dest_name, avoid_highways=avoid)
        if "error" in res:
            return "Couldn't get route info right now.", calls
        return (f"About {res['duration_in_traffic_min']} minutes via {res['summary']}, "
                f"traffic is {res['traffic_level']}."), calls

    return "I didn't catch a place or request. Where would you like to go?", calls
