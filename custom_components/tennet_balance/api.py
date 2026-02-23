import asyncio
import logging

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

LOGGER = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 0.5

class TennetApiClient:
    def __init__(self, hass, api_key: str, environment: str):
        self._hass = hass
        self._api_key = api_key
        self._base_url = f"https://{environment}.tennet.eu"

    async def get_latest(self) -> dict:
        url = f"{self._base_url}/publications/v1/balance-delta-high-res/latest"
        headers = {"Accept": "application/json", "apikey": self._api_key}
        session = async_get_clientsession(self._hass)
        last_error = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                async with session.get(url, headers=headers, timeout=30) as resp:
                    if resp.status >= 400:
                        LOGGER.warning(
                            "TenneT API request failed with status %s (attempt %s/%s)",
                            resp.status,
                            attempt,
                            MAX_ATTEMPTS,
                        )
                    resp.raise_for_status()
                    return await resp.json()
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
        raise last_error
