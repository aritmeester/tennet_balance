import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import logging
from time import monotonic

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .rate_limiter import RequestRateLimiter

LOGGER = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 0.5
REQUEST_TIMEOUT_SECONDS = 15
REFRESH_BUDGET_SECONDS = 45
RETRYABLE_STATUSES = frozenset({404, 408, 429, 500, 502, 503, 504})
# Retain the budget across entry reloads and reauthentication in this HA instance.
_RATE_LIMITERS_KEY = "tennet_balance_http_rate_limiters"


class TennetApiError(Exception):
    """Raised when the TenneT API returns an error payload or status."""

    def __init__(self, message: str, *, status: int | None = None,
                 error_id: str | None = None, payload: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.error_id = error_id
        self.payload = payload or {}

    @property
    def details(self) -> dict:
        return {
            "type": self.__class__.__name__,
            "status": self.status,
            "error_id": self.error_id,
            "message": self.message,
            "payload": self.payload,
        }


class TennetApiAuthError(TennetApiError):
    """Raised when authentication with the TenneT API fails."""


class TennetApiNoDataError(TennetApiError):
    """Raised when the API returns a no-data payload."""


class _RetryableError(TennetApiError):
    """A transient failure eligible for another attempt."""


def _extract_payload_error(payload: dict) -> tuple[str | None, str | None]:
    error_message = payload.get("Error_message") or payload.get("error")
    error_id = payload.get("Error_id")
    return str(error_message) if error_message else None, str(error_id) if error_id is not None else None


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        # RFC delay-seconds is a non-negative integer, not a float.
        if value.strip().isascii() and value.strip().isdigit():
            return float(int(value))
        when = parsedate_to_datetime(value)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError, OverflowError):
        return None


def _valid_timestamp(value) -> bool:
    if not isinstance(value, str) or ("T" not in value and " " not in value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _validate_measurements(payload: dict) -> None:
    """Validate the shape consumed by the existing coordinator, not market semantics."""
    response = payload.get("Response")
    series = response.get("TimeSeries") if isinstance(response, dict) else None
    if not isinstance(series, list) or not series:
        raise _RetryableError("Missing or invalid TimeSeries", status=200)
    all_points = []
    for item in series:
        periods = item.get("Period") if isinstance(item, dict) else None
        if not isinstance(periods, list):
            raise _RetryableError("Invalid Period structure", status=200)
        for period in periods:
            points = period.get("points") if isinstance(period, dict) else None
            if not isinstance(points, list) or any(not isinstance(p, dict) for p in points):
                raise _RetryableError("Invalid measurement points", status=200)
            all_points.extend(points)
    # The existing point sensor contract uses the last point of the first period.
    first_periods = series[0]["Period"]
    if not first_periods or not first_periods[0]["points"]:
        raise _RetryableError("Missing primary measurement points", status=200)
    latest = first_periods[0]["points"][-1]
    if not any(_valid_timestamp(latest.get(key)) for key in ("timeInterval_start", "timeInterval_end")):
        raise _RetryableError("Missing usable primary measurement timestamp", status=200)
    if not any(_valid_timestamp(p.get("timeInterval_end")) for p in all_points):
        raise _RetryableError("Missing usable interval end", status=200)
    # The coordinator passes truthy timestamps directly to its datetime parser.
    if any(p.get(key) and not _valid_timestamp(p[key]) for p in all_points
           for key in ("timeInterval_start", "timeInterval_end")):
        raise _RetryableError("Invalid measurement timestamp", status=200)


class TennetApiClient:
    def __init__(self, hass, api_key: str, environment: str):
        self._hass = hass
        self._api_key = api_key
        self._base_url = f"https://{environment}.tennet.eu"
        limiters = hass.data.setdefault(_RATE_LIMITERS_KEY, {})
        self._limiter = limiters.setdefault(environment, RequestRateLimiter())
        self._last_attempt_count = 0
        self._last_http_status = None
        self._last_retry_reason = None
        self._rate_limit_wait_seconds = 0.0

    def redact(self, value):
        """Remove credentials from upstream diagnostic values, including strings."""
        if isinstance(value, dict):
            return {
                self.redact(k): "**REDACTED**" if isinstance(k, str) and k.lower().replace("_", "").replace("-", "") == "apikey" else self.redact(v)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [self.redact(v) for v in value]
        if isinstance(value, str) and self._api_key:
            return value.replace(self._api_key, "**REDACTED**")
        return value

    @property
    def request_diagnostics(self) -> dict:
        return {
            "last_attempt_count": self._last_attempt_count,
            "last_http_status": self._last_http_status,
            "last_retry_reason": self._last_retry_reason,
            "rate_limit_wait_seconds": round(self._rate_limit_wait_seconds, 3),
        }

    async def _request(self, session, url, headers) -> dict:
        async with session.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS,
                               allow_redirects=False) as resp:
            status = self._last_http_status = resp.status
            retry_after = _retry_after_seconds(resp.headers.get("Retry-After"))
            if status in RETRYABLE_STATUSES and retry_after is not None:
                self._limiter.defer(retry_after)
            elif status == 429:
                # A missing header gives no reliable reset time; cool down for one minute.
                self._limiter.defer(60)
            try:
                decoded = await resp.json(content_type=None)
            except (ValueError, UnicodeError, TimeoutError, aiohttp.ClientError):
                decoded = None
            payload = self.redact(decoded) if isinstance(decoded, dict) else {}
            message, error_id = _extract_payload_error(payload)
            context = dict(status=status, error_id=error_id, payload=payload)
            if status in (401, 403):
                raise TennetApiAuthError(message or "Invalid API key or unauthorized environment", **context)
            if status in RETRYABLE_STATUSES:
                raise _RetryableError(message or f"HTTP {status}", **context)
            if not 200 <= status < 300:
                raise TennetApiError(message or f"HTTP {status}", **context)
            if not isinstance(decoded, dict):
                raise _RetryableError("Invalid JSON response", status=status)
            if message == "No data found":
                # Retry within the same bounded budget; preserve the final error type.
                raise TennetApiNoDataError(message, **context)
            if message:
                raise TennetApiError(message, **context)
            _validate_measurements(decoded)
            # Do not mutate the live measurement payload or its field values.
            return decoded

    async def get_latest(self) -> dict:
        url = f"{self._base_url}/publications/v1/balance-delta-high-res/latest"
        headers = {"Accept": "application/json", "apikey": self._api_key}
        session = async_get_clientsession(self._hass)
        self._last_attempt_count = 0
        self._last_http_status = None
        self._last_retry_reason = None
        self._rate_limit_wait_seconds = 0.0
        last_error = None
        try:
            async with asyncio.timeout(REFRESH_BUDGET_SECONDS):
                for attempt in range(1, MAX_ATTEMPTS + 1):
                    started = monotonic()
                    try:
                        await self._limiter.acquire()
                    finally:
                        self._rate_limit_wait_seconds += monotonic() - started
                    self._last_attempt_count = attempt
                    try:
                        return await self._request(session, url, headers)
                    except (_RetryableError, TennetApiNoDataError) as err:
                        last_error = err
                    except (TimeoutError, OSError, aiohttp.ClientError) as err:
                        # Avoid logging exception text that could contain request headers.
                        last_error = _RetryableError(f"HTTP request failed: {type(err).__name__}")
                    self._last_retry_reason = str(last_error)
                    LOGGER.debug("TenneT API attempt %s/%s failed: %s", attempt, MAX_ATTEMPTS, last_error)
                    if attempt < MAX_ATTEMPTS:
                        await asyncio.sleep(BACKOFF_SECONDS * attempt)
        except TimeoutError as err:
            if last_error is not None:
                raise last_error from err
            raise TennetApiError("API refresh time budget exhausted") from err
        if last_error is not None:
            raise last_error
        raise RuntimeError("Unknown error while requesting TenneT API")
