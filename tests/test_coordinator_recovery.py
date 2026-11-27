"""Refresh-level failure, authentication and recovery regression tests."""
from datetime import datetime, timedelta, timezone
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from test_coordinator_cache import module, fixture, ApiError, AuthError, ConfigEntryAuthFailed, UpdateFailed


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.clock = datetime(2026, 11, 27, 9, 0, 30, tzinfo=timezone.utc)
        self.elapsed = 0.0
        self.api = AsyncMock()
        self.api.get_latest.return_value = fixture()
        for clock_patch in (
            patch.object(module.dt_util, "utcnow", side_effect=lambda: self.clock),
            patch.object(module, "monotonic", side_effect=lambda: self.elapsed),
        ):
            clock_patch.start()
            self.addCleanup(clock_patch.stop)
        self.c = module.TennetCoordinator(None, self.api)

    def advance(self, seconds):
        self.elapsed += seconds
        self.clock += timedelta(seconds=seconds)

    async def refresh(self, error=None):
        self.api.get_latest.side_effect = error
        self.c.data = await self.c._async_update_data()
        return self.c.data

    async def test_initial_auth_failure(self):
        with self.assertRaises(ConfigEntryAuthFailed):
            await self.refresh(AuthError("invalid"))
        self.assertEqual(self.c.api_consecutive_failures, 1)
        self.assertIsNone(self.c.api_last_success)

    async def test_auth_threshold_and_non_auth_reset(self):
        await self.refresh()
        self.advance(12)
        for _ in range(4):
            await self.refresh(AuthError("auth"))
        self.assertEqual(self.c._api_consecutive_auth_failures, 4)
        await self.refresh(ApiError("busy"))
        self.assertEqual(self.c._api_consecutive_auth_failures, 0)
        for _ in range(4):
            await self.refresh(AuthError("auth"))
        with self.assertRaises(ConfigEntryAuthFailed):
            await self.refresh(AuthError("auth"))
        self.assertEqual(self.c._api_consecutive_auth_failures, 5)

    async def test_grace_boundary_and_recovery(self):
        original = await self.refresh()
        success = self.c.api_last_success
        self.advance(179)
        self.assertIs(await self.refresh(ApiError("busy")), original)
        self.advance(1)
        self.assertIs(await self.refresh(ApiError("busy")), original)
        self.advance(0.1)
        with self.assertRaises(UpdateFailed):
            await self.refresh(ApiError("busy"))
        self.assertIs(self.c.data, original)
        self.assertEqual(self.c.api_last_success, success)
        self.assertEqual(self.c.api_consecutive_failures, 3)
        self.api.get_latest.return_value = fixture()
        self.assertIsNot(await self.refresh(), original)
        self.assertEqual(self.c.api_consecutive_failures, 0)
        self.assertIsNone(self.c.api_last_error_details)
        self.assertEqual(self.c.api_last_success, self.clock)

    async def test_no_false_recovery_from_coalescing(self):
        await self.refresh()
        self.advance(1)
        self.c.last_update_success = False  # simulate native HA failure
        before = self.api.get_latest.await_count
        await self.refresh(ApiError("busy"))
        self.assertEqual(self.api.get_latest.await_count, before + 1)
        # Even when HA sees the grace return as successful, failed refreshes
        # bypass the healthy coalescing guard.
        self.c.last_update_success = True
        await self.refresh(ApiError("busy"))
        self.assertEqual(self.api.get_latest.await_count, before + 2)
        self.assertEqual(self.c.api_consecutive_failures, 2)

    async def test_grace_uses_monotonic_clock(self):
        await self.refresh()
        self.advance(181)
        self.clock -= timedelta(hours=1)
        with self.assertRaises(UpdateFailed):
            await self.refresh(ApiError("busy"))

    async def test_cancelled_refresh_not_counted_as_api_failure(self):
        await self.refresh()
        self.advance(12)
        with self.assertRaises(asyncio.CancelledError):
            await self.refresh(asyncio.CancelledError())
        self.assertEqual(self.c.api_consecutive_failures, 0)
        self.assertFalse(self.c._update_lock.locked())

    async def test_initial_invalid_data_not_reported_successful(self):
        with self.assertRaises(UpdateFailed):
            await self.refresh(ApiError("Invalid payload"))
        self.assertIsNone(self.c.data)
        self.assertIsNone(self.c.api_last_success)
