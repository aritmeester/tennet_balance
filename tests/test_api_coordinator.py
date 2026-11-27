"""Test the actual API client and coordinator together with fake transport and clocks."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_api import api, Response, Session
from test_coordinator_cache import module, fixture, point, payload


class ApiCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_malformed_response_keeps_cache_and_valid_response_recovers(self):
        first = fixture()
        new = payload(point("2026-11-27T09:00:24Z", "2026-11-27T09:00:36Z", power_mfrrda_out=2))
        session = Session(Response(200, first), Response(200, {}),
                          Response(503, {"Error_message": "busy"}), Response(200, {}),
                          Response(200, new))
        hass = SimpleNamespace(data={}, session=session)
        client = api.TennetApiClient(hass, "secret-key", "api")
        elapsed = 0.0
        origin = datetime(2026, 11, 27, 9, 0, 30, tzinfo=timezone.utc)

        async def sleep(seconds):
            nonlocal elapsed
            elapsed += seconds

        client._limiter = api.RequestRateLimiter(clock=lambda: elapsed, sleep=sleep)
        patches = (
            patch.object(api.asyncio, "sleep", side_effect=sleep),
            patch.object(api, "monotonic", side_effect=lambda: elapsed),
            patch.object(module, "monotonic", side_effect=lambda: elapsed),
            patch.object(module.dt_util, "utcnow", side_effect=lambda: origin + timedelta(seconds=elapsed)),
            patch.object(module, "TennetApiError", api.TennetApiError),
            patch.object(module, "TennetApiAuthError", api.TennetApiAuthError),
        )
        for clock_patch in patches:
            clock_patch.start()
            self.addCleanup(clock_patch.stop)
        c = module.TennetCoordinator(hass, client)
        c.data = await c._async_update_data()
        success = c.api_last_success
        with patch.object(c, "_calculate_rule_state_2_window_analysis",
                          wraps=c._calculate_rule_state_2_window_analysis) as calculate:
            self.assertEqual(c.regulation_state_current_isp_prediction, 1)
            elapsed += 12
            c.data = await c._async_update_data()
            self.assertIs(c.data, first)
            self.assertEqual(c.api_last_success, success)
            self.assertEqual(c.api_consecutive_failures, 1)
            self.assertEqual(client.request_diagnostics["last_attempt_count"], 3)
            self.assertEqual(c.regulation_state_current_isp_prediction, 1)
            self.assertEqual(calculate.call_count, 1)
            elapsed += 12
            c.data = await c._async_update_data()
            self.assertIs(c.data, new)
            self.assertEqual(c.api_consecutive_failures, 0)
            self.assertEqual(c.regulation_state_current_isp_prediction, -1)
            self.assertEqual(calculate.call_count, 2)
            self.assertEqual(len(session.calls), 5)
