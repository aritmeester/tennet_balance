from datetime import timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_call_later
from homeassistant.util.dt import utcnow, parse_datetime

LOGGER = logging.getLogger(__name__)

class TennetCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api):
        super().__init__(hass, LOGGER, name="TenneT Balance Delta", update_interval=timedelta(seconds=12))
        self.api = api

    @property
    def latest_point(self):
        try:
            return self.data["Response"]["TimeSeries"][0]["Period"][0]["points"][-1]
        except (KeyError, IndexError, TypeError):
            return None

    async def _async_update_data(self):
        LOGGER.warning("TennetCoordinator: _async_update_data aangeroepen voor refresh!")
        data = await self.api.get_latest()
        return data
