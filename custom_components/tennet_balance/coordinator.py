from datetime import timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import homeassistant.util.dt as dt_util
import asyncio

LOGGER = logging.getLogger(__name__)

MIN_UPDATE_INTERVAL = 6  # minimum seconds between API calls

class TennetCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api):
        super().__init__(hass, LOGGER, name="TenneT Balance Delta", update_interval=timedelta(seconds=12))
        self.api = api
        self._last_request = dt_util.utcnow() - timedelta(seconds=MIN_UPDATE_INTERVAL)
        self._update_lock = asyncio.Lock()  # ensures only one fetch at a time

    @property
    def latest_point(self):
        LOGGER.debug("TennetCoordinator: Accessing latest_point")
        try:
            return self.data["Response"]["TimeSeries"][0]["Period"][0]["points"][-1]
        except (KeyError, IndexError, TypeError):
            return None

    async def _async_update_data(self):
        """Fetch data from API with throttling and single-update lock."""
        async with self._update_lock:
            now = dt_util.utcnow()
            seconds_since_last = (now - self._last_request).total_seconds()

            if seconds_since_last < MIN_UPDATE_INTERVAL:
                LOGGER.debug(f"TennetCoordinator: Returning cached data, {seconds_since_last:.2f}s since last request")
                return self.data  # use cached data if called too soon

            LOGGER.debug("TennetCoordinator: Fetching new data from API")
            data = await self.api.get_latest()
            self._last_request = dt_util.utcnow()
            return data
