import logging

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EmergencyPowerActivatedSensor(coordinator)], update_before_add=True)


class EmergencyPowerActivatedSensor(CoordinatorEntity, BinarySensorEntity):
    _attr_entity_registry_enabled_default = True
    _attr_has_entity_name = True
    _attr_translation_key = "emergency_power_activated"
    _attr_unique_id = "tennet_balance_emergency_power_activated"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator):
        super().__init__(coordinator)
        LOGGER.debug("EmergencyPowerActivatedSensor initialized")

    @property
    def available(self):
        return self.coordinator.latest_point is not None

    @property
    def is_on(self):
        point = self.coordinator.latest_point or {}
        LOGGER.debug("EmergencyPowerActivatedSensor point: %s", point)

        in_val = point.get("power_mfrrda_in") or 0
        out_val = point.get("power_mfrrda_out") or 0

        try:
            in_val = float(in_val)
        except (TypeError, ValueError):
            in_val = 0

        try:
            out_val = float(out_val)
        except (TypeError, ValueError):
            out_val = 0

        return in_val > 0 or out_val > 0

    @property
    def icon(self):
        point = self.coordinator.latest_point or {}
        try:
            in_val = float(point.get("power_mfrrda_in") or 0)
            out_val = float(point.get("power_mfrrda_out") or 0)
        except (TypeError, ValueError):
            in_val = out_val = 0

        if in_val > 0 and out_val > 0:
            return "mdi:transmission-tower"
        if out_val > 0:
            return "mdi:transmission-tower-export"
        if in_val > 0:
            return "mdi:transmission-tower-import"
        return "mdi:transmission-tower-off"

    @property
    def extra_state_attributes(self):
        point = self.coordinator.latest_point or {}
        return {
            "in": point.get("power_mfrrda_in", 0),
            "out": point.get("power_mfrrda_out", 0),
        }

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, "tennet_balance")},
            name="TenneT Balance Delta High Resolution",
            manufacturer="TenneT",
        )
