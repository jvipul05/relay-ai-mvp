"""Small sliding-window limiter for demo abuse/cost control.

This limiter is process-local. Production needs authentication and a distributed gateway
or limiter such as Redis/API Gateway.
"""
from collections import deque
from collections.abc import Hashable
from math import ceil
from time import monotonic


class SlidingWindowRateLimiter:
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = max(1, int(window_seconds))
        self._events: dict[Hashable, deque[float]] = {}

    def check(self, key: Hashable, limit: int, now: float | None = None) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        current = monotonic() if now is None else now
        threshold = current - self.window_seconds
        events = self._events.setdefault(key, deque())
        while events and events[0] <= threshold:
            events.popleft()
        if len(events) >= max(1, int(limit)):
            return False, max(1, ceil(self.window_seconds - (current - events[0])))
        events.append(current)
        if len(self._events) > 4096:
            for stale_key, stored in list(self._events.items()):
                if not stored or stored[-1] <= threshold:
                    self._events.pop(stale_key, None)
        return True, 0
