"""Standalone coordinator regression tests; no live API or HA installation needed.

Run from the repository root:
    python -m unittest discover -s tests -p test_coordinator_cache.py -v

These stubs test coordinator logic, not Home Assistant's scheduling/lifecycle.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import AsyncMock, patch


class StubCoordinator:
    def __init__(self, hass, logger, *, name, update_interval):
        self.data = None
        self.last_update_success = True
        self.update_interval = update_interval


class ApiError(Exception):
    @property
    def details(self):
        return {"message": str(self)}


class AuthError(ApiError):
    pass


class ConfigEntryAuthFailed(Exception):
    pass


class UpdateFailed(Exception):
    pass


def load_coordinator(path):
    """Import the actual source with only its external dependencies stubbed."""
    names = (
        "homeassistant", "homeassistant.helpers",
        "homeassistant.helpers.update_coordinator", "homeassistant.exceptions",
        "homeassistant.util", "homeassistant.util.dt", "_tennet_test",
        "_tennet_test.const", "_tennet_test.api",
    )
    modules = {name: ModuleType(name) for name in names}
    for name, module in modules.items():
        module.__path__ = []
        if "." in name:
            parent, child = name.rsplit(".", 1)
            setattr(modules[parent], child, module)
    update = modules["homeassistant.helpers.update_coordinator"]
    update.DataUpdateCoordinator = StubCoordinator
    update.UpdateFailed = UpdateFailed
    modules["homeassistant.exceptions"].ConfigEntryAuthFailed = ConfigEntryAuthFailed
    dt = modules["homeassistant.util.dt"]
    dt.UTC = timezone.utc
    dt.utcnow = lambda: datetime.now(timezone.utc)
    dt.parse_datetime = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
    modules["_tennet_test.const"].REGULATION_PRICE_KEYS = {
        "max_upw_regulation_price", "min_downw_regulation_price"
    }
    modules["_tennet_test.api"].TennetApiError = ApiError
    modules["_tennet_test.api"].TennetApiAuthError = AuthError
    spec = importlib.util.spec_from_file_location("_tennet_test.coordinator", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module


SOURCE = Path(__file__).resolve().parents[1] / "custom_components/tennet_balance/coordinator.py"
module = load_coordinator(SOURCE)


def point(start, end, **values):
    return {"timeInterval_start": start, "timeInterval_end": end, **values}


def payload(*points):
    return {"Response": {"TimeSeries": [{"Period": [{"points": list(points)}]}]}}


def fixture():
    return payload(
        point("2026-11-27T08:59:48Z", "2026-11-27T09:00:00Z", power_mfrrda_out=3),
        point("2026-11-27T09:00:00Z", "2026-11-27T09:00:12Z", power_afrr_in=5,
              max_upw_regulation_price=10),
        point("2026-11-27T09:00:12Z", "2026-11-27T09:00:24Z", power_afrr_out=9),
    )


class CacheTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.api = AsyncMock()
        self.clock = datetime(2026, 11, 27, 9, 0, 30, tzinfo=timezone.utc)
        self.clock_patch = patch.object(module.dt_util, "utcnow", side_effect=lambda: self.clock)
        self.clock_patch.start()
        self.addCleanup(self.clock_patch.stop)
        self.monotonic = patch.object(module, "monotonic", side_effect=lambda: self.clock.timestamp())
        self.monotonic.start()
        self.addCleanup(self.monotonic.stop)
        self.coordinator = module.TennetCoordinator(None, self.api, True)

    async def test_single_analysis_per_payload(self):
        c = self.coordinator
        c.data = fixture()
        with patch.object(c, "_calculate_rule_state_2_window_analysis", wraps=c._calculate_rule_state_2_window_analysis) as calc:
            for _ in range(8):
                self.assertEqual(c.regulation_state_previous_isp, -1)
                self.assertEqual(c.regulation_state_current_isp_prediction, 1)
                self.assertFalse(c.rule_state_2_previous_isp)
                self.assertFalse(c.rule_state_2_current_isp_prediction)
                self.assertEqual(c.rule_state_2_analysis["latest_interval_end"], "2026-11-27T10:00:24+01:00")
                self.assertEqual(c.api_data_delay_seconds, 6)
            self.assertEqual(calc.call_count, 1)
            c.data = deepcopy(c.data)
            self.assertEqual(c.regulation_state_current_isp_prediction, 1)
            self.assertEqual(calc.call_count, 2)

    async def test_latest_point_is_lazy_and_invalidated(self):
        c = self.coordinator
        c.data = fixture()
        with patch.object(c, "_extract_latest_point", wraps=c._extract_latest_point) as extract, patch.object(c, "_calculate_rule_state_2_window_analysis", wraps=c._calculate_rule_state_2_window_analysis) as calc:
            for _ in range(20):
                self.assertEqual(c.latest_point["power_afrr_out"], 9)
            self.assertEqual(extract.call_count, 1)
            self.assertEqual(calc.call_count, 0)
            c.data = payload(point("2026-11-27T09:00:24Z", "2026-11-27T09:00:36Z", power_mfrrda_in=2))
            self.assertEqual(c.latest_point["power_mfrrda_in"], 2)
            self.assertEqual(extract.call_count, 2)
            self.assertEqual(c.regulation_state_current_isp_prediction, 1)
            self.assertEqual(calc.call_count, 1)

    async def test_empty_payload_and_recovery(self):
        c = self.coordinator
        with patch.object(c, "_calculate_rule_state_2_window_analysis", wraps=c._calculate_rule_state_2_window_analysis) as calc, patch.object(c, "_extract_latest_point", wraps=c._extract_latest_point) as extract:
            for empty in (None, {}, payload()):
                c.data = empty
                for _ in range(3):
                    self.assertIsNone(c.rule_state_2_analysis)
                    self.assertIsNone(c.latest_point)
                    self.assertIsNone(c.api_data_delay_seconds)
            self.assertEqual(calc.call_count, 3)
            self.assertEqual(extract.call_count, 3)
            c.data = fixture()
            self.assertEqual(c.regulation_state_previous_isp, -1)
            self.assertEqual(c.latest_point["power_afrr_out"], 9)
            self.assertEqual(calc.call_count, 4)
            self.assertEqual(extract.call_count, 4)

    async def test_public_analysis_cannot_mutate_cache(self):
        c = self.coordinator
        c.data = fixture()
        result = c.rule_state_2_analysis
        result["current_isp_prediction"]["regulation_state"] = 99
        self.assertEqual(c.regulation_state_current_isp_prediction, 1)
        self.assertEqual(c.rule_state_2_analysis["current_isp_prediction"]["regulation_state"], 1)

    async def test_throttling_grace_recovery_and_dynamic_delay(self):
        c = self.coordinator
        self.api.get_latest.return_value = fixture()
        c.data = await c._async_update_data()
        original = c.data
        with patch.object(c, "_calculate_rule_state_2_window_analysis", wraps=c._calculate_rule_state_2_window_analysis) as calc:
            self.assertEqual(c.api_data_delay_seconds, 6)
            self.clock += timedelta(seconds=3)
            c.data = await c._async_update_data()
            self.assertIs(c.data, original)
            self.assertEqual(self.api.get_latest.await_count, 1)
            self.assertEqual(c.api_data_delay_seconds, 9)
            self.clock += timedelta(seconds=9)
            self.api.get_latest.side_effect = ApiError("transient")
            c.data = await c._async_update_data()
            self.assertIs(c.data, original)
            self.assertEqual(c.api_consecutive_failures, 1)
            self.assertEqual(c.api_data_delay_seconds, 18)
            self.assertEqual(calc.call_count, 1)
            self.clock += timedelta(seconds=180)
            with self.assertRaises(UpdateFailed):
                await c._async_update_data()
            self.assertEqual(c.api_consecutive_failures, 2)
            self.api.get_latest.side_effect = None
            self.api.get_latest.return_value = payload(point("2026-11-27T09:03:36Z", "2026-11-27T09:03:48Z", power_mfrrda_out=4))
            c.data = await c._async_update_data()
            self.assertEqual(c.regulation_state_current_isp_prediction, -1)
            self.assertEqual(c.api_consecutive_failures, 0)
            self.assertEqual(calc.call_count, 2)

    async def test_price_retention_unchanged(self):
        c = self.coordinator
        self.api.get_latest.return_value = payload(point("2026-11-27T09:00:12Z", "2026-11-27T09:00:24Z", max_upw_regulation_price=42))
        c.data = await c._async_update_data()
        self.assertEqual(c.get_last_known_value("max_upw_regulation_price"), 42)
        self.clock += timedelta(seconds=12)
        self.api.get_latest.return_value = payload(point("2026-11-27T09:00:24Z", "2026-11-27T09:00:36Z", max_upw_regulation_price=None))
        c.data = await c._async_update_data()
        self.assertIsNone(c.latest_point["max_upw_regulation_price"])
        self.assertEqual(c.get_last_known_value("max_upw_regulation_price"), 42)

    async def test_cache_is_per_coordinator(self):
        c = self.coordinator
        other = module.TennetCoordinator(None, self.api)
        c.data = fixture()
        other.data = payload(point("2026-11-27T09:00:12Z", "2026-11-27T09:00:24Z", power_mfrrda_in=1, power_mfrrda_out=2))
        self.assertEqual(c.regulation_state_current_isp_prediction, 1)
        self.assertEqual(other.regulation_state_current_isp_prediction, 2)
        self.assertEqual(c.latest_point["power_afrr_out"], 9)
        self.assertEqual(other.latest_point["power_mfrrda_in"], 1)


if __name__ == "__main__":
    unittest.main()
