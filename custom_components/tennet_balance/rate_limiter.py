"""Limit actual HTTP request starts, including retries."""

import asyncio
from collections import deque
from time import monotonic


class RequestRateLimiter:
    """Enforce a rolling minute limit and minimum spacing on one event loop."""

    def __init__(self, *, clock=monotonic, sleep=asyncio.sleep):
        self._clock = clock
        self._sleep = sleep
        self._lock = asyncio.Lock()
        self._starts = deque()
        self._blocked_until = 0.0

    def defer(self, seconds: float) -> None:
        """Apply server-requested cooldown to subsequent attempts."""
        self._blocked_until = max(self._blocked_until, self._clock() + seconds)

    async def acquire(self) -> None:
        """Reserve an attempt; cancellation while waiting consumes no slot."""
        async with self._lock:
            while True:
                now = self._clock()
                while self._starts and now - self._starts[0] >= 60:
                    self._starts.popleft()
                ready = self._blocked_until
                if self._starts:
                    ready = max(ready, self._starts[-1] + 1)
                if len(self._starts) >= 10:
                    ready = max(ready, self._starts[0] + 60)
                if ready <= now:
                    self._starts.append(now)
                    return
                await self._sleep(ready - now)
