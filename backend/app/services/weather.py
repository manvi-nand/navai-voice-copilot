"""Google Maps Platform Weather API client — current conditions + hourly forecast.

Uses the same Google key as Routes/Places (enable "Weather API" in Cloud Console),
so no separate weather provider is needed.

Mock-first: deterministic pseudo-forecast so "will it rain before I reach
home?" style queries flow without a key.
"""
from __future__ import annotations

import httpx

from app.config import settings


async def get_weather(location: dict, hours: int = 2) -> dict:
    """Return {current, rain_expected, rain_in_minutes, summary}."""
    if settings.use_mocks:
        return _mock_weather(location, hours)
    return await _real_weather(location, hours)


def _mock_weather(location: dict, hours: int) -> dict:
    # Deterministic-ish: use latitude fraction to decide rain.
    frac = abs(location["lat"] * 1000) % 100
    rain_soon = frac < 45
    rain_in = int(frac) if rain_soon else None
    return {
        "current": "partly cloudy, 27C",
        "rain_expected": rain_soon,
        "rain_in_minutes": rain_in,
        "summary": (
            f"Light rain expected in about {rain_in} minutes"
            if rain_soon
            else "Clear for the next couple of hours"
        ),
    }


async def _real_weather(location: dict, hours: int) -> dict:
    # Google Weather API. https://developers.google.com/maps/documentation/weather
    base = "https://weather.googleapis.com/v1"
    key = settings.maps_key()
    loc = {"location.latitude": location["lat"], "location.longitude": location["lng"]}
    async with httpx.AsyncClient(timeout=10.0) as client:
        cur = await client.get(f"{base}/currentConditions:lookup", params={"key": key, **loc})
        cur.raise_for_status()
        c = cur.json()
        fc = await client.get(
            f"{base}/forecast/hours:lookup", params={"key": key, "hours": max(1, hours), **loc}
        )
        fc.raise_for_status()
        f = fc.json()

    temp = c.get("temperature", {}).get("degrees")
    desc = c.get("weatherCondition", {}).get("description", {}).get("text", "unknown")
    current = f"{desc.lower()}, {round(temp)}C" if temp is not None else desc

    # First hour with a high precipitation probability (hourly granularity).
    rain_in = None
    for i, h in enumerate(f.get("forecastHours", [])):
        prob = h.get("precipitation", {}).get("probability", {}).get("percent", 0)
        if prob >= 50:
            rain_in = i * 60
            break
    rain_expected = rain_in is not None
    return {
        "current": current,
        "rain_expected": rain_expected,
        "rain_in_minutes": rain_in,
        "summary": (
            f"Light rain expected in about {rain_in} minutes"
            if rain_expected
            else "Clear for the next couple of hours"
        ),
    }
