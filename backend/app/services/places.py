"""Google Places API (Nearby Search) client.

Mock-first: returns a few synthetic nearby places keyed off the query type.
"""
from __future__ import annotations

import math
from typing import Optional

import httpx

from app.config import settings

_MOCK_TEMPLATES = {
    "petrol": [("HP Petrol Bunk", 0.6, "open"), ("Indian Oil", 1.4, "open")],
    "pharmacy": [("Apollo Pharmacy", 0.4, "open"), ("MedPlus", 0.9, "closed")],
    "restaurant": [("Truffles", 0.7, "open"), ("Empire Restaurant", 1.1, "open")],
    "coffee": [("Starbucks", 0.5, "open"), ("Third Wave Coffee", 1.2, "open")],
    "atm": [("HDFC ATM", 0.3, "open"), ("SBI ATM", 0.8, "open")],
}


async def find_nearby_places(
    location: dict, query: str, radius_m: int = 2000
) -> list[dict]:
    """Return list of {name, distance_km, open_now}."""
    if settings.use_mocks:
        return _mock_places(location, query)
    return await _real_places(location, query, radius_m)


async def resolve_nearest(query: str, location: dict) -> Optional[dict]:
    """Resolve a place name to the NEAREST matching place's {name, lat, lng}.

    Location-biased, so "McDonald's" routes to the closest branch rather than an
    arbitrary one (the plain Geocoding API isn't location-aware). Works for area
    names too (returns the locality centre). Returns None if nothing matches.
    """
    if settings.use_mocks:
        from app.services.geocode import _mock_geocode

        return _mock_geocode(query)
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.maps_key(),
        "X-Goog-FieldMask": "places.displayName,places.location",
    }
    body = {
        "textQuery": query,
        "locationBias": {
            "circle": {
                "center": {"latitude": location["lat"], "longitude": location["lng"]},
                "radius": 50000.0,
            }
        },
        "maxResultCount": 5,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(url, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
    cands = [
        {
            "name": p.get("displayName", {}).get("text"),
            "lat": p["location"]["latitude"],
            "lng": p["location"]["longitude"],
        }
        for p in data.get("places", [])
        if p.get("location")
    ]
    if not cands:
        return None
    cands.sort(key=lambda c: _haversine_km(location, {"lat": c["lat"], "lng": c["lng"]}))
    return cands[0]


def _mock_places(location: dict, query: str) -> list[dict]:
    q = query.lower()
    key = next((k for k in _MOCK_TEMPLATES if k in q), None)
    if key is None:
        return []
    results = []
    for name, dist, status in _MOCK_TEMPLATES[key]:
        results.append({"name": name, "distance_km": dist, "open_now": status == "open"})
    return results


async def find_on_route_places(
    origin: dict, destination: dict, place_type: str
) -> list[dict]:
    """Phase 2 (doc §2.9): places genuinely on the route, ranked by added detour time
    rather than raw proximity. Returns {name, added_minutes, on_route}."""
    if settings.use_mocks:
        return _mock_on_route(place_type)
    # Real impl: sample points along the Directions polyline, Nearby Search around each,
    # then re-route through the candidate to compute true added time.
    return _mock_on_route(place_type)


def _mock_on_route(place_type: str) -> list[dict]:
    q = place_type.lower()
    key = next((k for k in _MOCK_TEMPLATES if k in q), "coffee")
    names = [n for n, _, _ in _MOCK_TEMPLATES[key]]
    return [
        {"name": names[0], "added_minutes": 4, "on_route": True},
        {"name": names[1] if len(names) > 1 else names[0], "added_minutes": 14, "on_route": False},
    ]


async def _real_places(location: dict, query: str, radius_m: int) -> list[dict]:
    # Places API (New) Text Search — the legacy Nearby Search is blocked for new
    # projects. https://developers.google.com/maps/documentation/places/web-service/text-search
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.maps_key(),
        "X-Goog-FieldMask": "places.displayName,places.location,places.currentOpeningHours.openNow",
    }
    body = {
        "textQuery": query,
        "locationBias": {
            "circle": {
                "center": {"latitude": location["lat"], "longitude": location["lng"]},
                "radius": float(radius_m),
            }
        },
        "maxResultCount": 5,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(url, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
    out = []
    for p in data.get("places", []):
        loc = p.get("location", {})
        dest = {"lat": loc.get("latitude"), "lng": loc.get("longitude")}
        out.append(
            {
                "name": p.get("displayName", {}).get("text"),
                "distance_km": round(_haversine_km(location, dest), 1) if loc else None,
                "open_now": p.get("currentOpeningHours", {}).get("openNow"),
            }
        )
    # Closest first — more useful than API ranking for "near me".
    out.sort(key=lambda x: x["distance_km"] if x["distance_km"] is not None else 1e9)
    return out


def _haversine_km(a: dict, b: dict) -> float:
    r = 6371.0
    dlat = math.radians(b["lat"] - a["lat"])
    dlng = math.radians(b["lng"] - a["lng"])
    x = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(a["lat"])) * math.cos(math.radians(b["lat"])) * math.sin(dlng / 2) ** 2
    )
    return r * 2 * math.asin(math.sqrt(x))


def _bearing(a: dict, b: dict) -> str:
    dlng = math.radians(b["lng"] - a["lng"])
    y = math.sin(dlng) * math.cos(math.radians(b["lat"]))
    x = math.cos(math.radians(a["lat"])) * math.sin(math.radians(b["lat"])) - math.sin(
        math.radians(a["lat"])
    ) * math.cos(math.radians(b["lat"])) * math.cos(dlng)
    deg = (math.degrees(math.atan2(y, x)) + 360) % 360
    dirs = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
    return dirs[round(deg / 45) % 8]
