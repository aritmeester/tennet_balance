from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import entity_registry as er
from .const import DOMAIN, SENSOR_DESCRIPTIONS, REGULATION_PRICE_KEYS

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    environment = entry.data["environment"]
    environment_slug = environment.replace(".", "_")
    entity_registry = er.async_get(hass)

    def _entry_owns_legacy_sensor(key: str) -> bool:
        legacy_unique_id = f"tennet_balance_{key}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, legacy_unique_id)
        if entity_id is None:
            return False
        registry_entry = entity_registry.async_get(entity_id)
        return registry_entry is not None and registry_entry.config_entry_id == entry.entry_id

    use_legacy_device_identifier = _entry_owns_legacy_sensor("mid_price")
    device_identifier = (
        "tennet_balance"
        if use_legacy_device_identifier
        else f"tennet_balance_{environment_slug}"
    )

    sensors = [
        TennetPointSensor(
            coordinator,
            k,
            v,
            environment_slug,
            device_identifier,
            _entry_owns_legacy_sensor(k),
        )
        for k, v in SENSOR_DESCRIPTIONS.items()
    ]
    async_add_entities(sensors, update_before_add=True)

class TennetPointSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    async def async_update(self):
        await self.coordinator.async_request_refresh()

    def __init__(
        self,
        coordinator,
        key,
        meta,
        environment_slug: str,
        device_identifier: str,
        use_legacy_unique_id: bool,
    ):
        super().__init__(coordinator)
        self.key = key
        self._attr_translation_key = key
        self._device_identifier = device_identifier
        self._attr_unique_id = (
            f"tennet_balance_{key}"
            if use_legacy_unique_id
            else f"tennet_balance_{environment_slug}_{key}"
        )
        self._attr_native_unit_of_measurement = meta.get("unit")
        self._attr_device_class = meta.get("device_class")
        self._attr_state_class = meta.get("state_class")
        self._attr_icon = meta.get("icon")
        if self._attr_device_class == SensorDeviceClass.MONETARY:
            self._attr_state_class = None

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_identifier)},
            name="TenneT Balance Delta High Resolution",
            manufacturer="TenneT"
        )

    @property
    def native_value(self):
        point = self.coordinator.latest_point
        if not point:
            return None
        value = point.get(self.key)
        if value is None:
            if (
                self.key in REGULATION_PRICE_KEYS
                and self.coordinator.keep_last_regulation_prices
                and self.coordinator.get_last_known_value(self.key) is not None
            ):
                return self.coordinator.get_last_known_value(self.key)
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
        
    @property
    def extra_state_attributes(self):
        point = self.coordinator.latest_point
        if not point:
            return {}
        attrs = {
            "start": point["timeInterval_start"],
            "end": point["timeInterval_end"],
        }
        return attrs