"""Test integration wiring; native Home Assistant scheduling requires runtime tests."""
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from test_coordinator_cache import module, fixture

ROOT = Path(__file__).resolve().parents[1] / "custom_components/tennet_balance"


def load_entry_module(api):
    names = ("homeassistant", "homeassistant.config_entries", "homeassistant.core",
             "_tennet_lifecycle", "_tennet_lifecycle.const", "_tennet_lifecycle.api",
             "_tennet_lifecycle.coordinator")
    stubs = {name: ModuleType(name) for name in names}
    for name, stub in stubs.items():
        stub.__path__ = []
        if "." in name:
            parent, child = name.rsplit(".", 1)
            setattr(stubs[parent], child, stub)
    stubs["homeassistant.config_entries"].ConfigEntry = object
    stubs["homeassistant.core"].HomeAssistant = object
    const = stubs["_tennet_lifecycle.const"]
    const.DOMAIN = "tennet_balance"
    const.PLATFORMS = ["sensor", "binary_sensor"]
    const.CONF_KEEP_LAST_REGULATION_PRICES = "keep_last_regulation_prices"
    stubs["_tennet_lifecycle.api"].TennetApiClient = lambda hass, key, env: api
    stubs["_tennet_lifecycle.coordinator"].TennetCoordinator = module.TennetCoordinator
    spec = spec_from_file_location("_tennet_lifecycle", ROOT / "__init__.py",
                                   submodule_search_locations=[str(ROOT)])
    integration = module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(integration)
    return integration


class Entry:
    def __init__(self):
        self.entry_id = "entry"
        self.data = {"api_key": "test", "environment": "api"}
        self.options = {}
        self.callbacks = []
        self.update_listener = None

    def async_on_unload(self, callback):
        self.callbacks.append(callback)

    def add_update_listener(self, listener):
        self.update_listener = listener
        return lambda: None


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.api = AsyncMock()
        self.api.get_latest.return_value = fixture()
        self.integration = load_entry_module(self.api)
        self.entry = Entry()
        self.hass = SimpleNamespace(data={}, config_entries=AsyncMock())
        self.hass.config_entries.async_unload_platforms.return_value = True

    async def test_setup_registers_native_shutdown_and_unload_removes_entry(self):
        await self.integration.async_setup_entry(self.hass, self.entry)
        c = self.hass.data["tennet_balance"]["entry"]
        self.assertIs(c.config_entry, self.entry)
        self.assertIn(c.async_shutdown, self.entry.callbacks)
        self.assertNotIn("async_shutdown", type(c).__dict__)
        self.assertEqual(self.api.get_latest.await_count, 1)
        self.assertTrue(await self.integration.async_unload_entry(self.hass, self.entry))
        self.assertNotIn("entry", self.hass.data["tennet_balance"])
        self.assertEqual(c.shutdown_count, 0)  # no duplicate explicit shutdown
        await c.async_shutdown()  # model the HA-registered unload callback
        self.assertEqual(c.shutdown_count, 1)

    async def test_failed_unload_keeps_coordinator(self):
        await self.integration.async_setup_entry(self.hass, self.entry)
        c = self.hass.data["tennet_balance"]["entry"]
        self.hass.config_entries.async_unload_platforms.return_value = False
        self.assertFalse(await self.integration.async_unload_entry(self.hass, self.entry))
        self.assertIs(self.hass.data["tennet_balance"]["entry"], c)
        self.assertEqual(c.shutdown_count, 0)

    async def test_config_entry_update_requests_reload(self):
        await self.integration.async_setup_entry(self.hass, self.entry)
        await self.entry.update_listener(self.hass, self.entry)
        self.hass.config_entries.async_reload.assert_awaited_once_with("entry")
