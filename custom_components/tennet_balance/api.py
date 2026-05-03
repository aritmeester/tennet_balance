import asyncio
import datetime
import logging

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

LOGGER = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 0.5


def _fmt_date(d: datetime.date) -> str:
    return d.strftime("%d-%m-%Y 00:00:00")


class TennetApiAuthError(Exception):
    """Raised when authentication with the TenneT API fails."""


class TennetApiError(Exception):
    """Raised when the TenneT API returns an error payload or status."""

    def __init__(self, message: str, *, status: int | None = None, error_id: str | None = None, payload: dict | None = None):
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


class TennetApiNoDataError(TennetApiError):
    """Raised when the API returns a no-data payload."""


def _extract_payload_error(payload: dict) -> tuple[str | None, str | None]:
    error_message = payload.get("Error_message") or payload.get("error")
    error_id = payload.get("Error_id")
    return error_message, error_id


class TennetApiClient:
    def __init__(self, hass, api_key: str, environment: str):
        self._hass = hass
        self._api_key = api_key
        self._base_url = f"https://{environment}.tennet.eu"

    async def _get(self, url: str, params: dict | None = None) -> dict:
        headers = {"Accept": "application/json", "apikey": self._api_key}
        session = async_get_clientsession(self._hass)
        last_error = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                async with session.get(url, headers=headers, params=params, timeout=30) as resp:
                    payload = await resp.json(content_type=None)
                    if not isinstance(payload, dict):
                        raise TennetApiError(
                            f"Unexpected API response type: {type(payload).__name__}",
                            status=resp.status,
                        )

                    error_message, error_id = _extract_payload_error(payload)

                    if resp.status in (401, 403):
                        raise TennetApiAuthError(error_message or "Invalid API key or unauthorized environment")

                    if error_message == "No data found":
                        raise TennetApiNoDataError(
                            error_message,
                            status=resp.status,
                            error_id=error_id,
                            payload=payload,
                        )

                    if error_message:
                        raise TennetApiError(
                            error_message,
                            status=resp.status,
                            error_id=error_id,
                            payload=payload,
                        )

                    if resp.status >= 400:
                        raise TennetApiError(
                            f"HTTP {resp.status}",
                            status=resp.status,
                            payload=payload,
                        )
                    return payload
            except (asyncio.TimeoutError, OSError, aiohttp.ClientError) as err:
                last_error = err
                LOGGER.warning(
                    "TenneT API request error: %s (attempt %s/%s)",
                    err,
                    attempt,
                    MAX_ATTEMPTS,
                )
            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(BACKOFF_SECONDS * attempt)
        if last_error is not None:
            raise last_error
        raise RuntimeError("Unknown error while requesting TenneT API")

    async def get_latest(self) -> dict:
        url = f"{self._base_url}/publications/v1/balance-delta-high-res/latest"
        return await self._get(url)

    async def get_settlement_prices(self, date_from: str, date_to: str) -> dict:
        url = f"{self._base_url}/publications/v1/settlement-prices"
        return await self._get(url, params={"date_from": date_from, "date_to": date_to})

    async def get_reconciliation_prices_isp(self, date_from: str, date_to: str) -> dict:
        url = f"{self._base_url}/publications/v1/reconciliation-prices/isp"
        return await self._get(url, params={"date_from": date_from, "date_to": date_to})
