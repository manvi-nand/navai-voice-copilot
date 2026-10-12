"""Google Maps Geocoding API client — place name -> coordinates.

Mock-first: a small Bangalore gazetteer covers common dev queries.
"""
from __future__ import annotations

from typing import Optional

import httpx

from app.config import settings

# Minimal Bangalore gazetteer for offline/mock development.
_BLR_PLACES: dict[str, dict] = {
    "koramangala": {"name": "Koramangala", "lat": 12.9352, "lng": 77.6245},
    "indiranagar": {"name": "Indiranagar", "lat": 12.9719, "lng": 77.6412},
    "silk board": {"name": "Silk Board", "lat": 12.9172, "lng": 77.6228},
    "hosur road": {"name": "Hosur Road", "lat": 12.8997, "lng": 77.6300},
    "airport": {"name": "Kempegowda Intl Airport", "lat": 13.1986, "lng": 77.7066},
    "whitefield": {"name": "Whitefield", "lat": 12.9698, "lng": 77.7500},
    "mg road": {"name": "MG Road", "lat": 12.9756, "lng": 77.6050},
    "electronic city": {"name": "Electronic City", "lat": 12.8452, "lng": 77.6602},
}


async def geocode_place(query: str) -> Optional[dict]:
    """Return {name, lat, lng} or None if not found."""
    if settings.use_mocks:
        return _mock_geocode(query)
    return await _real_geocode(query)


def _mock_geocode(query: str) -> Optional[dict]:
    q = query.strip().lower()
    for key, val in _BLR_PLACES.items():
        if key in q:
            return dict(val)
    # Unknown place: return a plausible central-BLR point so the pipeline flows.
    return {"name": query.title(), "lat": 12.9716, "lng": 77.5946}


async def _real_geocode(query: str) -> Optional[dict]:
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": query, "region": "in", "key": settings.maps_key()}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    if not data.get("results"):
        return None
    top = data["results"][0]
    loc = top["geometry"]["location"]
    return {"name": top["formatted_address"], "lat": loc["lat"], "lng": loc["lng"]}


async def reverse_geocode(lat: float, lng: float) -> dict:
    """Coordinates -> address. Returns {address, short} where `short` is a concise
    locality name suitable for a UI location bar."""
    if settings.use_mocks:
        return {"address": "Koramangala, Bengaluru, Karnataka", "short": "Koramangala"}
    return await _real_reverse(lat, lng)


async def _real_reverse(lat: float, lng: float) -> dict:
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"latlng": f"{lat},{lng}", "key": settings.maps_key()}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    results = data.get("results", [])
    if not results:
        return {"address": "Unknown location", "short": "Current location"}
    full = results[0]["formatted_address"]
    # Prefer a neighbourhood/sublocality/locality for the concise label.
    short = None
    wanted = ("sublocality_level_1", "sublocality", "neighborhood", "locality")
    for comp in results[0].get("address_components", []):
        if any(t in comp.get("types", []) for t in wanted):
            short = comp["long_name"]
            break
    return {"address": full, "short": short or full.split(",")[0]}
