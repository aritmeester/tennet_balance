from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.components.diagnostics import async_redact_data

from .const import DOMAIN

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    api_last_response = coordinator.data

    if isinstance(api_last_response, (dict, list)):
        api_last_response = async_redact_data(api_last_response, TO_REDACT)

    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "api_last_success": coordinator.api_last_success,
            "api_response_time_ms": coordinator.api_response_time_ms,
            "api_data_delay_seconds": coordinator.api_data_delay_seconds,
            "api_consecutive_failures": coordinator.api_consecutive_failures,
            "api_last_error": coordinator.api_last_error,
            "api_last_error_details": coordinator.api_last_error_details,
            "api_last_response": api_last_response,
        },
    }
