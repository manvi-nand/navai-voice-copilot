"""Google Maps Directions API client — ETA, route, traffic.

Mock-first: returns realistic Bangalore-flavoured ETAs with traffic deltas.
"""
from __future__ import annotations

import math
from typing import Optional

import httpx

from app.config import settings


async def get_directions(
    origin: dict,
    destination: dict,
    avoid_highways: bool = False,
    depart_in_minutes: int = 0,
) -> dict:
    """Return a normalized directions summary.

    Shape: {
        duration_min, duration_in_traffic_min, distance_km,
        summary (route name), traffic_level, avoid_highways
    }
    """
    if settings.use_mocks:
        return _mock_directions(origin, destination, avoid_highways, depart_in_minutes)
    return await _real_directions(origin, destination, avoid_highways, depart_in_minutes)


def _decode_polyline(encoded: str) -> list[dict]:
    """Decode a Google encoded polyline into [{latitude, longitude}, ...]."""
    points: list[dict] = []
    index = lat = lng = 0
    while index < len(encoded):
        for unit in ("lat", "lng"):
            shift = result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else (result >> 1)
            if unit == "lat":
                lat += delta
            else:
                lng += delta
        points.append({"latitude": lat / 1e5, "longitude": lng / 1e5})
    return points


def _haversine_km(a: dict, b: dict) -> float:
    r = 6371.0
    dlat = math.radians(b["lat"] - a["lat"])
    dlng = math.radians(b["lng"] - a["lng"])
    x = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(a["lat"]))
        * math.cos(math.radians(b["lat"]))
        * math.sin(dlng / 2) ** 2
    )
    return r * 2 * math.asin(math.sqrt(x))


def _mock_directions(
    origin: dict, destination: dict, avoid_highways: bool, depart_in_minutes: int
) -> dict:
    dist = max(1.0, _haversine_km(origin, destination))
    # ~22 km/h effective Bangalore speed; highways a touch faster.
    base_speed = 26.0 if not avoid_highways else 20.0
    base_min = (dist / base_speed) * 60
    # Traffic surcharge eases the further out you leave.
    surcharge = max(0.0, 0.45 - depart_in_minutes * 0.01)
    in_traffic = base_min * (1 + surcharge)
    level = "heavy" if surcharge > 0.3 else "moderate" if surcharge > 0.1 else "light"
    summary = "service road" if avoid_highways else "Hosur Road"
    return {
        "duration_min": round(base_min),
        "duration_in_traffic_min": round(in_traffic),
        "distance_km": round(dist, 1),
        "summary": summary,
        "traffic_level": level,
        "avoid_highways": avoid_highways,
        # Straight line origin->dest for the mock map.
        "polyline": [
            {"latitude": origin["lat"], "longitude": origin["lng"]},
            {"latitude": destination["lat"], "longitude": destination["lng"]},
        ],
        "toll": ("around Rs 110 toll" if dist > 25 else None),
    }


async def plan_trip(origin: dict, stops: list[dict]) -> dict:
    """Multi-stop trip from origin through `stops` (ordered, each {name,lat,lng}).
    Returns {legs:[{to,minutes,km}], total_minutes, total_km}."""
    if settings.use_mocks:
        return _mock_plan(origin, stops)
    return await _real_plan(origin, stops)


def _mock_plan(origin: dict, stops: list[dict]) -> dict:
    legs = []
    prev = origin
    for s in stops:
        d = max(0.5, _haversine_km(prev, {"lat": s["lat"], "lng": s["lng"]}))
        legs.append({"to": s["name"], "minutes": round(d / 26 * 60 * 1.3), "km": round(d, 1)})
        prev = {"lat": s["lat"], "lng": s["lng"]}
    return {
        "legs": legs,
        "total_minutes": sum(l["minutes"] for l in legs),
        "total_km": round(sum(l["km"] for l in legs), 1),
    }


async def _real_plan(origin: dict, stops: list[dict]) -> dict:
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.maps_key(),
        "X-Goog-FieldMask": "routes.legs.duration,routes.legs.distanceMeters",
    }

    def _pt(p: dict) -> dict:
        return {"location": {"latLng": {"latitude": p["lat"], "longitude": p["lng"]}}}

    body = {
        "origin": _pt(origin),
        "destination": _pt(stops[-1]),
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
    }
    if len(stops) > 1:
        body["intermediates"] = [_pt(s) for s in stops[:-1]]
    async with httpx.AsyncClient(timeout=12.0) as client:
        r = await client.post(url, headers=headers, json=body)
        r.raise_for_status()
        route = r.json()["routes"][0]
    legs = []
    for i, leg in enumerate(route.get("legs", [])):
        secs = float(str(leg.get("duration", "0s")).rstrip("s") or 0)
        legs.append(
            {
                "to": stops[i]["name"] if i < len(stops) else "stop",
                "minutes": round(secs / 60),
                "km": round(leg.get("distanceMeters", 0) / 1000, 1),
            }
        )
    return {
        "legs": legs,
        "total_minutes": sum(l["minutes"] for l in legs),
        "total_km": round(sum(l["km"] for l in legs), 1),
    }


async def _real_directions(
    origin: dict, destination: dict, avoid_highways: bool, depart_in_minutes: int
) -> dict:
    # Routes API (the legacy Directions API is blocked for new projects).
    # https://developers.google.com/maps/documentation/routes/compute_route_directions
    from datetime import datetime, timedelta, timezone

    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.maps_key(),
        # duration = traffic-aware; staticDuration = free-flow (no traffic).
        "X-Goog-FieldMask": (
            "routes.duration,routes.staticDuration,routes.distanceMeters,"
            "routes.description,routes.polyline.encodedPolyline,"
            "routes.travelAdvisory.tollInfo"
        ),
    }
    body: dict = {
        "origin": {"location": {"latLng": {"latitude": origin["lat"], "longitude": origin["lng"]}}},
        "destination": {"location": {"latLng": {"latitude": destination["lat"], "longitude": destination["lng"]}}},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
        "extraComputations": ["TOLLS"],
    }
    if avoid_highways:
        body["routeModifiers"] = {"avoidHighways": True}
    if depart_in_minutes > 0:
        depart = datetime.now(timezone.utc) + timedelta(minutes=depart_in_minutes)
        body["departureTime"] = depart.isoformat()
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(url, headers=headers, json=body)
        r.raise_for_status()
        route = r.json()["routes"][0]

    def _secs(v: str) -> float:
        return float(str(v).rstrip("s") or 0)

    dur_traffic = _secs(route["duration"]) / 60
    dur = _secs(route.get("staticDuration", route["duration"])) / 60
    encoded = route.get("polyline", {}).get("encodedPolyline", "")
    return {
        "duration_min": round(dur),
        "duration_in_traffic_min": round(dur_traffic),
        "distance_km": round(route["distanceMeters"] / 1000, 1),
        "summary": route.get("description") or ("service road" if avoid_highways else "fastest route"),
        "traffic_level": "heavy" if dur_traffic > dur * 1.3 else "moderate" if dur_traffic > dur * 1.1 else "light",
        "avoid_highways": avoid_highways,
        "polyline": _decode_polyline(encoded) if encoded else [],
        "toll": _toll_label(route.get("travelAdvisory", {}).get("tollInfo")),
    }


def _toll_label(toll_info: Optional[dict]) -> Optional[str]:
    """Turn Routes API tollInfo into a short spoken label like 'around Rs 110 toll'."""
    if not toll_info:
        return None
    prices = toll_info.get("estimatedPrice") or []
    if not prices:
        return None
    p = prices[0]
    units = int(p.get("units", 0))
    if units <= 0:
        return None
    cur = "Rs" if p.get("currencyCode") == "INR" else p.get("currencyCode", "")
    return f"around {cur} {units} toll"
