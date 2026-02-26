import logging

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    environment_slug = entry.data["environment"].replace(".", "_")
    entity_registry = er.async_get(hass)

    legacy_sensor_entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "tennet_balance_mid_price"
    )
    legacy_sensor_entry = (
        entity_registry.async_get(legacy_sensor_entity_id)
        if legacy_sensor_entity_id is not None
        else None
    )
    use_legacy_device_identifier = (
        legacy_sensor_entry is not None
        and legacy_sensor_entry.config_entry_id == entry.entry_id
    )
    device_identifier = (
        "tennet_balance"
        if use_legacy_device_identifier
        else f"tennet_balance_{environment_slug}"
    )

    legacy_unique_id = "tennet_balance_emergency_power_activated"
    legacy_entity_id = entity_registry.async_get_entity_id(
        "binary_sensor", DOMAIN, legacy_unique_id
    )
    legacy_entry = entity_registry.async_get(legacy_entity_id) if legacy_entity_id else None
    use_legacy_unique_id = legacy_entry is not None and legacy_entry.config_entry_id == entry.entry_id

    async_add_entities(
        [
            EmergencyPowerActivatedSensor(
                coordinator,
                environment_slug,
                device_identifier,
                use_legacy_unique_id,
                "Noodvermogen",
            ),
        ],
        update_before_add=True,
    )


class EmergencyPowerActivatedSensor(CoordinatorEntity, BinarySensorEntity):
    _attr_entity_registry_enabled_default = True
    _attr_has_entity_name = False
    _attr_translation_key = "emergency_power_activated"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator,
        environment_slug: str,
        device_identifier: str,
        use_legacy_unique_id: bool,
        name: str | None,
    ):
        super().__init__(coordinator)
        self._attr_name = name
        self._device_identifier = device_identifier
        self._attr_unique_id = (
            "tennet_balance_emergency_power_activated"
            if use_legacy_unique_id
            else f"tennet_balance_{environment_slug}_emergency_power_activated"
        )
        LOGGER.debug("EmergencyPowerActivatedSensor initialized")

    @property
    def available(self):
        return super().available and self.coordinator.latest_point is not None

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
            identifiers={(DOMAIN, self._device_identifier)},
            name="Balance Delta High Resolution",
            manufacturer="TenneT",
        )
