import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import DOMAIN, PLATFORMS, CONF_KEEP_LAST_REGULATION_PRICES
from .api import TennetApiClient
from .coordinator import TennetCoordinator, TennetSettlementCoordinator, TennetReconciliationCoordinator

LOGGER = logging.getLogger(__name__)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = TennetApiClient(hass, entry.data["api_key"], entry.data["environment"])
    keep_last_regulation_prices = entry.options.get(
        CONF_KEEP_LAST_REGULATION_PRICES,
        entry.data.get(CONF_KEEP_LAST_REGULATION_PRICES, False),
    )
    coordinator = TennetCoordinator(hass, api, keep_last_regulation_prices)
    await coordinator.async_config_entry_first_refresh()

    settlement_coordinator = TennetSettlementCoordinator(hass, api)
    try:
        await settlement_coordinator.async_config_entry_first_refresh()
    except Exception as err:
        LOGGER.warning("TenneT settlement prices initial fetch failed (will retry): %s", err)

    reconciliation_coordinator = TennetReconciliationCoordinator(hass, api)
    try:
        await reconciliation_coordinator.async_config_entry_first_refresh()
    except Exception as err:
        LOGGER.warning("TenneT reconciliation prices initial fetch failed (will retry): %s", err)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "main": coordinator,
        "settlement": settlement_coordinator,
        "reconciliation": reconciliation_coordinator,
    }
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if entry_data is not None:
            await entry_data["main"].async_shutdown()
    return unload_ok
