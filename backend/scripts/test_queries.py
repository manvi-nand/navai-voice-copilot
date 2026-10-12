"""Week-2 smoke test: fire text queries at the agent and print responses + tools.

Run the server first:
    uvicorn app.main:app --reload
Then:
    python scripts/test_queries.py

Exercises the agent + 5 tools end-to-end with mocks (no keys, no audio, no phone).
"""
from __future__ import annotations

import asyncio
import uuid

import httpx

BASE = "http://localhost:8000"
SESSION = str(uuid.uuid4())
GPS = {"lat": 12.9716, "lng": 77.5946}  # central Bangalore

# (query, expectation note). Multi-turn: later queries lean on earlier context.
QUERIES = [
    "How long to Koramangala in this traffic?",
    "What about avoiding the highway?",          # follow-up: same destination
    "Is there a petrol bunk near me?",
    "Will it rain before I reach the airport?",
    "Find a pharmacy nearby",
]


async def main() -> None:
    async with httpx.AsyncClient(timeout=20.0) as client:
        for q in QUERIES:
            r = await client.post(
                f"{BASE}/query",
                json={
                    "transcript": q,
                    "current_location": GPS,
                    "session_id": SESSION,
                    "language": "en-IN",
                },
            )
            data = r.json()
            print(f"\nQ: {q}")
            print(f"A: {data['response_text']}")
            print(f"   tools: {data['tool_calls']}")


if __name__ == "__main__":
    asyncio.run(main())
