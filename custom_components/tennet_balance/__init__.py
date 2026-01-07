from .const import DOMAIN, PLATFORMS
from .api import TennetApiClient
from .coordinator import TennetCoordinator

async def async_setup_entry(hass, entry):
    api = TennetApiClient(entry.data["api_key"], entry.data["environment"])
    coordinator = TennetCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True
