from datetime import timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_call_later
from homeassistant.util.dt import utcnow, parse_datetime

LOGGER = logging.getLogger(__name__)

class TennetCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api):
        super().__init__(hass, LOGGER, name="TenneT Balance Delta", update_interval=None)
        self.api = api
        self._remove_listener = None

    async def _async_update_data(self):
        data = await self.api.get_latest()
        point = data["Response"]["TimeSeries"][0]["Period"][0]["points"][-1]
        end_ts = parse_datetime(point["timeInterval_end"])
        delay = max((end_ts + timedelta(seconds=1) - utcnow()).total_seconds(), 1)
        if self._remove_listener:
            self._remove_listener()
        self._remove_listener = async_call_later(
            self.hass, delay,
            lambda _: self.hass.async_create_task(self.async_request_refresh())
        )
        return data
