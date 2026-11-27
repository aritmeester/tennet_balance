"""API contract tests against synthetic HTTP responses, without network access."""
import asyncio
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from test_coordinator_cache import fixture

ROOT = Path(__file__).resolve().parents[1] / "custom_components/tennet_balance"


def load_api():
    names = ("homeassistant", "homeassistant.helpers", "homeassistant.helpers.aiohttp_client", "aiohttp", "_tennet_api_test")
    stubs = {name: ModuleType(name) for name in names}
    for name, stub in stubs.items():
        stub.__path__ = []
        if "." in name:
            parent, child = name.rsplit(".", 1)
            setattr(stubs[parent], child, stub)
    stubs["aiohttp"].ClientError = type("ClientError", (Exception,), {})
    stubs["homeassistant.helpers.aiohttp_client"].async_get_clientsession = lambda hass: hass.session
    with patch.dict(sys.modules, stubs):
        for name in ("rate_limiter", "api"):
            spec = spec_from_file_location(f"_tennet_api_test.{name}", ROOT / f"{name}.py")
            module = module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
        return module


api = load_api()


class Response:
    def __init__(self, status, payload=None, headers=None):
        self.status, self.payload, self.headers = status, payload, headers or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def json(self, **kwargs):
        if isinstance(self.payload, BaseException):
            raise self.payload
        return self.payload


class Session:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = next(self.responses)
        if isinstance(response, BaseException):
            raise response
        return response


class ApiTests(unittest.IsolatedAsyncioTestCase):
    def client(self, *responses):
        hass = SimpleNamespace(data={}, session=Session(*responses))
        client = api.TennetApiClient(hass, "secret-key", "api")
        client._limiter = SimpleNamespace(acquire=AsyncMock(), defer=lambda seconds: self.cooldowns.append(seconds))
        return client, hass.session

    async def asyncSetUp(self):
        self.cooldowns = []
        self.sleep = patch.object(api.asyncio, "sleep", new=AsyncMock())
        self.sleep.start()
        self.addCleanup(self.sleep.stop)

    async def test_success_unchanged(self):
        data = fixture()
        c, s = self.client(Response(200, data))
        self.assertIs(await c.get_latest(), data)
        self.assertEqual(len(s.calls), 1)
        self.assertFalse(s.calls[0][1]["allow_redirects"])
        self.assertEqual(c.request_diagnostics["last_attempt_count"], 1)

    async def test_structured_and_non_json_retryable(self):
        c, s = self.client(Response(503, {"Error_message": "busy"}), Response(404, ValueError()), Response(200, fixture()))
        await c.get_latest()
        self.assertEqual(len(s.calls), 3)
        self.assertEqual(c._limiter.acquire.await_count, 3)

    async def test_auth_non_json_and_no_retry(self):
        for status in (401, 403):
            c, s = self.client(Response(status, ValueError()))
            with self.assertRaises(api.TennetApiAuthError) as error:
                await c.get_latest()
            self.assertEqual(error.exception.status, status)
            self.assertEqual(len(s.calls), 1)

    async def test_terminal_non_retryable_and_redaction(self):
        c, s = self.client(Response(400, {"Error_message": "bad secret-key", "apiKey": "another-secret"}))
        with self.assertRaises(api.TennetApiError) as error:
            await c.get_latest()
        self.assertEqual(len(s.calls), 1)
        self.assertNotIn("secret-key", str(error.exception.details))
        self.assertNotIn("another-secret", str(error.exception.details))

    async def test_no_data_and_invalid_success_retry(self):
        c, s = self.client(Response(200, {"error": "No data found"}), Response(200, {}), Response(200, fixture()))
        await c.get_latest()
        self.assertEqual(len(s.calls), 3)

    async def test_invalid_timestamp_rejected(self):
        data = fixture()
        data["Response"]["TimeSeries"][0]["Period"][0]["points"][0]["timeInterval_end"] = 123
        c, s = self.client(*[Response(200, data) for _ in range(3)])
        with self.assertRaises(api.TennetApiError):
            await c.get_latest()
        self.assertEqual(len(s.calls), 3)

    async def test_retry_after_and_429_fallback(self):
        c, s = self.client(Response(429, {}, {"Retry-After": "7"}), Response(429, {}), Response(200, fixture()))
        await c.get_latest()
        self.assertEqual(self.cooldowns, [7, 60])
        self.assertEqual(len(s.calls), 3)

    async def test_transport_failure_and_exhaustion(self):
        c, s = self.client(TimeoutError(), OSError("secret-key"), Response(503, {"Error_message": "busy", "Error_id": "42"}))
        with self.assertRaises(api.TennetApiError) as error:
            await c.get_latest()
        self.assertEqual(error.exception.error_id, "42")
        self.assertEqual(error.exception.status, 503)
        self.assertEqual(len(s.calls), 3)

    async def test_cancel_propagates(self):
        c, s = self.client(asyncio.CancelledError())
        with self.assertRaises(asyncio.CancelledError):
            await c.get_latest()
        self.assertEqual(len(s.calls), 1)

    async def test_budget_bounds_limiter_wait(self):
        c, s = self.client()
        c._limiter.acquire = AsyncMock(side_effect=lambda: None)
        async def blocked():
            await asyncio.Event().wait()
        c._limiter.acquire.side_effect = blocked
        with patch.object(api, "REFRESH_BUDGET_SECONDS", 0.01):
            with self.assertRaisesRegex(api.TennetApiError, "time budget"):
                await c.get_latest()
        self.assertEqual(len(s.calls), 0)

    async def test_environment_shared_across_clients(self):
        hass = SimpleNamespace(data={})
        a = api.TennetApiClient(hass, "a", "api")
        b = api.TennetApiClient(hass, "b", "api")
        c = api.TennetApiClient(hass, "a", "api.acc")
        self.assertIs(a._limiter, b._limiter)
        self.assertIsNot(a._limiter, c._limiter)

    def test_retry_after_parsing(self):
        self.assertEqual(api._retry_after_seconds("5"), 5)
        self.assertIsNone(api._retry_after_seconds("invalid"))
        self.assertEqual(api._retry_after_seconds("Wed, 21 Oct 2015 07:28:00 GMT"), 0)
