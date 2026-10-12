"""Proactive traffic alerts (doc §2.8).

When a drive has an active destination, a monitor polls the route in the background
and emits a spoken alert when traffic worsens past a configurable threshold, or when
a faster alternate appears. Each session has at most one monitor.

The monitor is transport-agnostic: it pushes alert dicts onto an asyncio.Queue that
the /ws/voice connection (or a dedicated alerts socket) drains and speaks via TTS.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from app.services import maps as maps_svc
from app.session.store import SessionState

logger = logging.getLogger(__name__)


@dataclass
class Monitor:
    session: SessionState
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    # Alert when in-traffic ETA grows by at least this fraction vs the baseline.
    sensitivity: float = 0.20
    interval_s: float = 60.0
    _task: asyncio.Task | None = None
    _baseline_min: float | None = None

    def start(self, current_location: dict) -> None:
        if self._task and not self._task.done():
            return
        self._loc = current_location
        self._task = asyncio.create_task(self._run())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None

    async def _run(self) -> None:
        try:
            while self.session.destination:
                await self._check()
                await asyncio.sleep(self.interval_s)
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: BLE001
            logger.exception("proactive monitor error")

    async def _check(self) -> None:
        dest = self.session.destination
        if not dest:
            return
        direct = await maps_svc.get_directions(self._loc, dest)
        eta = direct["duration_in_traffic_min"]
        if self._baseline_min is None:
            self._baseline_min = eta
            return
        worsened = (eta - self._baseline_min) / max(1.0, self._baseline_min)
        if worsened >= self.sensitivity:
            alt = await maps_svc.get_directions(self._loc, dest, avoid_highways=True)
            saved = eta - alt["duration_in_traffic_min"]
            if saved > 0:
                msg = (
                    f"Traffic building on your route — alternate via {alt['summary']} "
                    f"saves {round(saved)} minutes."
                )
            else:
                msg = f"Traffic building on your route — about {round(eta)} minutes now."
            await self.queue.put({"type": "proactive", "text": msg})
            self._baseline_min = eta  # avoid repeating until it worsens again


class MonitorRegistry:
    def __init__(self) -> None:
        self._monitors: dict[str, Monitor] = {}

    def ensure(self, session: SessionState, current_location: dict) -> Monitor:
        m = self._monitors.get(session.session_id)
        if m is None:
            m = Monitor(session=session)
            self._monitors[session.session_id] = m
        if session.destination:
            m.start(current_location)
        return m

    def get(self, session_id: str) -> Monitor | None:
        return self._monitors.get(session_id)

    def stop(self, session_id: str) -> None:
        m = self._monitors.pop(session_id, None)
        if m:
            m.stop()


registry = MonitorRegistry()
