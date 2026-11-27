"""Deterministic rate limiter tests using a controllable monotonic clock."""
import asyncio
import unittest
from test_api import api


class RateLimiterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = 0.0
        async def sleep(seconds):
            self.now += seconds
        self.limiter = api.RequestRateLimiter(clock=lambda: self.now, sleep=sleep)

    async def test_normal_polling_never_delayed(self):
        for index in range(30):
            self.now = index * 12.0
            await self.limiter.acquire()
            self.assertEqual(self.now, index * 12.0)

    async def test_spacing_and_rolling_limit(self):
        starts = []
        for _ in range(25):
            await self.limiter.acquire()
            starts.append(self.now)
        self.assertEqual(starts[:11], list(range(10)) + [60.0])
        self.assertTrue(all(b - a >= 1 for a, b in zip(starts, starts[1:])))
        self.assertTrue(all(starts[i+10] - starts[i] >= 60 for i in range(len(starts)-10)))

    async def test_server_cooldown(self):
        await self.limiter.acquire()
        self.limiter.defer(20)
        self.limiter.defer(5)
        await self.limiter.acquire()
        self.assertEqual(self.now, 20)

    async def test_cancel_wait_does_not_consume_slot(self):
        await self.limiter.acquire()
        async def block(_):
            await asyncio.Event().wait()
        self.limiter._sleep = block
        task = asyncio.create_task(self.limiter.acquire())
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(list(self.limiter._starts), [0])
        self.assertFalse(self.limiter._lock.locked())
