from datetime import timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed
import homeassistant.util.dt as dt_util
import asyncio

from .const import REGULATION_PRICE_KEYS
from .api import TennetApiAuthError

LOGGER = logging.getLogger(__name__)

MIN_UPDATE_INTERVAL = 6  # minimum seconds between API calls

class TennetCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, keep_last_regulation_prices: bool = False):
        super().__init__(hass, LOGGER, name="TenneT Balance Delta", update_interval=timedelta(seconds=12))
        self.api = api
        self._keep_last_regulation_prices = keep_last_regulation_prices
        self._last_request = dt_util.utcnow() - timedelta(seconds=MIN_UPDATE_INTERVAL)
        self._update_lock = asyncio.Lock()  # ensures only one fetch at a time
        self._last_known_values = {}

    def _extract_latest_point(self, data):
        try:
            return data["Response"]["TimeSeries"][0]["Period"][0]["points"][-1]
        except (KeyError, IndexError, TypeError):
            return None

    @property
    def latest_point(self):
        LOGGER.debug("TennetCoordinator: Accessing latest_point")
        return self._extract_latest_point(self.data)

    def get_last_known_value(self, key):
        return self._last_known_values.get(key)

    @property
    def keep_last_regulation_prices(self):
        return self._keep_last_regulation_prices

    async def _async_update_data(self):
        """Fetch data from API with throttling and single-update lock."""
        async with self._update_lock:
            now = dt_util.utcnow()
            seconds_since_last = (now - self._last_request).total_seconds()

            if seconds_since_last < MIN_UPDATE_INTERVAL:
                LOGGER.debug(f"TennetCoordinator: Returning cached data, {seconds_since_last:.2f}s since last request")
                return self.data  # use cached data if called too soon

            LOGGER.debug("TennetCoordinator: Fetching new data from API")
            try:
                data = await self.api.get_latest()
            except TennetApiAuthError as err:
                raise ConfigEntryAuthFailed("Invalid API key") from err
            except Exception as err:
                raise UpdateFailed(f"Error fetching TenneT data: {err}") from err
            self._last_request = dt_util.utcnow()
            if self._keep_last_regulation_prices:
                point = self._extract_latest_point(data)
                if point:
                    for key in REGULATION_PRICE_KEYS:
                        value = point.get(key)
                        if value is None:
                            continue
                        try:
                            self._last_known_values[key] = float(value)
                        except (TypeError, ValueError):
                            continue
            return data
