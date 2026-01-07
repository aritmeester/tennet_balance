from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN, SENSOR_DESCRIPTIONS

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TennetPointSensor(coordinator, k, v) for k, v in SENSOR_DESCRIPTIONS.items()])

class TennetPointSensor(CoordinatorEntity, SensorEntity):
    async def async_update(self):
        await self.coordinator.async_request_refresh()

    def __init__(self, coordinator, key, meta):
        super().__init__(coordinator)
        self.key = key
        self._attr_name = meta["name"]
        self._attr_unique_id = f"tennet_balance_{key}"
        self._attr_native_unit_of_measurement = meta.get("unit")
        self._attr_device_class = meta.get("device_class")
        self._attr_state_class = meta.get("state_class")

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, "tennet_balance")},
            name="TenneT Balance Delta High Resolution",
            manufacturer="TenneT"
        )

    @property
    def native_value(self):
        point = self.coordinator.data["Response"]["TimeSeries"][0]["Period"][0]["points"][-1]
        value = point.get(self.key)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
