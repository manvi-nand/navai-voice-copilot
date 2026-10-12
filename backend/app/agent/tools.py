"""The five LangChain tools (doc §3.3).

Tools are built per-request via `build_tools` so the current GPS location and the
drive's session state are captured in closures — this is the "injected into state
automatically with every query" behaviour from the doc, without an extra LLM step
to fetch location.
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool

from app.services import geocode as geocode_svc
from app.services import maps as maps_svc
from app.services import places as places_svc
from app.services import weather as weather_svc
from app.session.store import SessionState


def build_tools(
    current_location: dict, session: SessionState, cards: list[dict] | None = None
) -> list[StructuredTool]:
    """Return the tools bound to this request's location + session.

    `cards` (if provided) collects structured tool results so the client can render
    rich cards (route/weather/places) in addition to the spoken answer.
    """
    sink = cards if cards is not None else []

    def emit(card_type: str, data: Any) -> None:
        sink.append({"type": card_type, "data": data})

    async def get_directions(
        destination: str, avoid_highways: bool = False, depart_in_minutes: int = 0
    ) -> dict:
        """Get ETA, distance and traffic for driving from the user's current location
        to a destination. Use for any travel-time, route, or traffic question. If the
        destination is a chain with several branches, this routes to the nearest one."""
        # Prefer a location-biased lookup so chains resolve to the NEAREST branch;
        # fall back to plain geocoding (and use the spoken name as the label).
        dest = await places_svc.resolve_nearest(destination, current_location)
        if dest and dest.get("name"):
            label = dest["name"]
        else:
            dest = await geocode_svc.geocode_place(destination)
            if not dest:
                return {"error": f"Could not find {destination}"}
            label = destination.strip().title()
        result = await maps_svc.get_directions(
            current_location, dest, avoid_highways, depart_in_minutes
        )
        session.destination = dest  # remember for follow-ups
        emit(
            "directions",
            {
                **result,
                "destination_name": label,
                "dest_lat": dest.get("lat"),
                "dest_lng": dest.get("lng"),
            },
        )
        return {**result, "destination_name": label}

    async def find_nearby_places(query: str) -> list[dict]:
        """Find places near the user's current location. `query` can be a category
        (petrol bunk, pharmacy, restaurant, coffee, atm) OR a specific name or brand
        ("Bob's Bar", "Starbucks", "Apollo Pharmacy"). Pass whatever the user asked for."""
        results = await places_svc.find_nearby_places(current_location, query)
        if results:
            session.last_place = results[0]  # remember for "is it open?"
            emit("places", {"place_type": query, "results": results})
        return results

    async def find_on_route_places(place_type: str) -> list[dict]:
        """Find places of a type that are genuinely ON THE WAY to the active
        destination, ranked by added detour time. Use for 'add a coffee stop on my
        way' style requests (doc §2.9). Requires an active destination."""
        if not session.destination:
            return [{"error": "no active destination to route through"}]
        results = await places_svc.find_on_route_places(
            current_location, session.destination, place_type
        )
        emit("on_route", {"place_type": place_type, "results": results})
        return results

    def save_place(label: str) -> dict:
        """Save the user's current location under a label like 'home' or 'office'
        ('save this as my office'). The app persists it to device storage."""
        place = {"name": label, "lat": current_location["lat"], "lng": current_location["lng"]}
        session.saved_places[label] = place
        return place

    async def get_weather(at_destination: bool = False, hours: int = 2) -> dict:
        """Get weather and short-term rain forecast at the user's current location, or
        at the active destination if at_destination is true."""
        loc = current_location
        place = "your destination" if at_destination and session.destination else "here"
        if at_destination and session.destination:
            loc = session.destination
            place = session.destination.get("name", "your destination")
        result = await weather_svc.get_weather(loc, hours)
        emit("weather", {**result, "place": place})
        return result

    async def geocode_place(query: str) -> dict:
        """Convert a place name into coordinates. Call before other tools when you only
        have a name."""
        result = await geocode_svc.geocode_place(query)
        return result or {"error": f"Could not find {query}"}

    async def get_current_address() -> dict:
        """Get the human-readable address of where the user currently is (reverse
        geocode of their GPS). Use for 'where am I', and to name the starting point
        when giving directions."""
        return await geocode_svc.reverse_geocode(
            current_location["lat"], current_location["lng"]
        )

    async def when_to_leave(destination: str, arrive_by: str) -> dict:
        """Work out when to leave to reach `destination` by a target time. `arrive_by`
        must be a 24-hour clock time like "18:00" or "09:30"."""
        from datetime import datetime, timedelta

        dest = await places_svc.resolve_nearest(destination, current_location) or (
            await geocode_svc.geocode_place(destination)
        )
        if not dest:
            return {"error": f"Could not find {destination}"}
        d = await maps_svc.get_directions(current_location, dest)
        travel = d["duration_in_traffic_min"]
        try:
            hh, mm = (int(x) for x in arrive_by.replace(".", ":").split(":"))
            now = datetime.now()
            arrive = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if arrive < now:
                arrive += timedelta(days=1)
        except Exception:
            return {"error": "Give the arrival time as HH:MM, e.g. 18:00"}
        leave = arrive - timedelta(minutes=travel)
        data = {
            "destination_name": dest.get("name") or destination,
            "arrive_by": arrive.strftime("%H:%M"),
            "leave_by": leave.strftime("%H:%M"),
            "travel_minutes": travel,
            "traffic_level": d["traffic_level"],
        }
        emit("leave_by", data)
        return data

    async def plan_trip(stops: list[str]) -> dict:
        """Plan a multi-stop drive from the current location through several stops in
        order. `stops` is an ordered list of place names, e.g. ['pharmacy', 'home']."""
        resolved = []
        for s in stops:
            p = await places_svc.resolve_nearest(s, current_location) or (
                await geocode_svc.geocode_place(s)
            )
            if p:
                resolved.append({"name": p.get("name") or s, "lat": p["lat"], "lng": p["lng"]})
        if not resolved:
            return {"error": "Couldn't find those stops"}
        trip = await maps_svc.plan_trip(current_location, resolved)
        session.destination = resolved[-1]  # final stop becomes the destination
        emit("trip", trip)
        return trip

    async def find_parking(near: str = "") -> list[dict]:
        """Find parking near a place by name, or near the active destination / current
        location if `near` is empty."""
        loc = current_location
        label = "here"
        if near:
            p = await places_svc.resolve_nearest(near, current_location)
            if p:
                loc, label = {"lat": p["lat"], "lng": p["lng"]}, p.get("name") or near
        elif session.destination:
            loc = {"lat": session.destination["lat"], "lng": session.destination["lng"]}
            label = session.destination.get("name", "your destination")
        results = await places_svc.find_nearby_places(loc, "parking")
        if results:
            emit("places", {"place_type": f"parking near {label}", "results": results})
        return results

    async def compare_routes(destination: str) -> dict:
        """Compare the fastest route vs avoiding highways to a destination, with the
        time difference. Use for 'highway or service road?' questions."""
        dest = await places_svc.resolve_nearest(destination, current_location) or (
            await geocode_svc.geocode_place(destination)
        )
        if not dest:
            return {"error": f"Could not find {destination}"}
        fast = await maps_svc.get_directions(current_location, dest, avoid_highways=False)
        alt = await maps_svc.get_directions(current_location, dest, avoid_highways=True)
        session.destination = dest
        data = {"destination_name": dest.get("name") or destination, "fastest": fast, "no_highway": alt}
        emit("route_compare", data)
        return data

    def get_session_context(key: str) -> Any:
        """Resolve context from earlier in the drive: 'home', 'office', a saved place,
        'destination' (last routed-to place), or 'last_place' (last place mentioned)."""
        if key in ("home", "office") or key in session.saved_places:
            return session.saved_places.get(key) or {"error": f"{key} not set"}
        if key in ("destination", "there"):
            return session.destination or {"error": "no active destination"}
        if key in ("last_place", "it"):
            return session.last_place or {"error": "no recent place"}
        return {"error": f"unknown context key {key}"}

    return [
        StructuredTool.from_function(coroutine=get_directions, name="get_directions"),
        StructuredTool.from_function(coroutine=find_nearby_places, name="find_nearby_places"),
        StructuredTool.from_function(coroutine=find_on_route_places, name="find_on_route_places"),
        StructuredTool.from_function(coroutine=get_weather, name="get_weather"),
        StructuredTool.from_function(coroutine=geocode_place, name="geocode_place"),
        StructuredTool.from_function(coroutine=get_current_address, name="get_current_address"),
        StructuredTool.from_function(coroutine=when_to_leave, name="when_to_leave"),
        StructuredTool.from_function(coroutine=plan_trip, name="plan_trip"),
        StructuredTool.from_function(coroutine=find_parking, name="find_parking"),
        StructuredTool.from_function(coroutine=compare_routes, name="compare_routes"),
        StructuredTool.from_function(func=save_place, name="save_place"),
        StructuredTool.from_function(func=get_session_context, name="get_session_context"),
    ]
