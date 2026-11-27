"""Preserve diagnostic fields and redact credentials, including echoed strings."""
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from test_api import api
from test_coordinator_cache import fixture

ROOT = Path(__file__).resolve().parents[1] / "custom_components/tennet_balance"


def load_diagnostics():
    names = ("homeassistant", "homeassistant.config_entries", "homeassistant.const", "homeassistant.core",
             "homeassistant.components", "homeassistant.components.diagnostics", "_tennet_diag", "_tennet_diag.const")
    stubs = {name: ModuleType(name) for name in names}
    for name, stub in stubs.items():
        stub.__path__ = []
        if "." in name:
            parent, child = name.rsplit(".", 1)
            setattr(stubs[parent], child, stub)
    stubs["homeassistant.config_entries"].ConfigEntry = object
    stubs["homeassistant.core"].HomeAssistant = object
    stubs["homeassistant.const"].CONF_API_KEY = "api_key"
    stubs["homeassistant.components.diagnostics"].async_redact_data = lambda value, keys: value
    stubs["_tennet_diag.const"].DOMAIN = "tennet_balance"
    spec = spec_from_file_location("_tennet_diag.diagnostics", ROOT / "diagnostics.py")
    result = module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(result)
    return result


class DiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def test_additive_fields_and_credentials_redacted(self):
        hass = SimpleNamespace(data={})
        key = "secret-key"
        client = api.TennetApiClient(hass, key, "api")
        payload = fixture()
        payload["echo"] = f"echoed {key}"
        c = SimpleNamespace(
            api=client, data=payload, last_update_success=True,
            api_last_success=None, api_last_failure=None, api_response_time_ms=12,
            api_data_delay_seconds=10, api_consecutive_failures=1,
            api_consecutive_auth_failures=1, api_grace_active=True,
            api_last_error=f"error {key}", api_last_error_details={"apiKey": key},
        )
        hass.data["tennet_balance"] = {"entry": c}
        entry = SimpleNamespace(entry_id="entry", data={"api_key": key}, options={"api_key": key})
        d = await load_diagnostics().async_get_config_entry_diagnostics(hass, entry)
        self.assertNotIn(key, str(d))
        self.assertEqual(d["coordinator"]["api_last_response"]["Response"], payload["Response"])
        self.assertTrue(d["coordinator"]["api_grace_active"])
        self.assertIn("http_requests", d["coordinator"])
        self.assertEqual(d["coordinator"]["api_consecutive_auth_failures"], 1)
        self.assertEqual(payload["echo"], f"echoed {key}")  # live response untouched
