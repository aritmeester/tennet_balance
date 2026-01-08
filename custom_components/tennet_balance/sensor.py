import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN, SENSOR_DESCRIPTIONS

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = [TennetPointSensor(coordinator, k, v) for k, v in SENSOR_DESCRIPTIONS.items()]
    sensors.append(EmergencyPowerActivatedSensor(coordinator))
    async_add_entities(sensors, update_before_add=True)


class EmergencyPowerActivatedSensor(CoordinatorEntity, BinarySensorEntity):
    _attr_entity_registry_enabled_default = True
    _attr_name = "TenneT Emergency Power Activated"
    _attr_unique_id = "tennet_balance_emergency_power_activated"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    
    def __init__(self, coordinator):
        super().__init__(coordinator)
        LOGGER.debug("EmergencyPowerActivatedSensor initialized")

    @property
    def native_value(self):
        point = getattr(self.coordinator, "latest_point", None)
        LOGGER.debug("EmergencyPowerActivatedSensor latest_point: %s", point)

        if not point:
            return False

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
        point = getattr(self.coordinator, "latest_point", None)
        in_val = out_val = 0
        if point:
            try:
                in_val = float(point.get("power_mfrrda_in") or 0)
                out_val = float(point.get("power_mfrrda_out") or 0)
            except (TypeError, ValueError):
                pass

        if in_val > 0 and out_val > 0:
            return "mdi:transmission-tower-tower"
        if out_val > 0:
            return "mdi:transmission-tower-export"
        if in_val > 0:
            return "mdi:transmission-tower-import"
        return "mdi:transmission-tower-off"

    @property
    def extra_state_attributes(self):
        point = getattr(self.coordinator, "latest_point", None)
        if not point:
            return {}
        return {
            "in": point.get("power_mfrrda_in", 0),
            "out": point.get("power_mfrrda_out", 0),
        }

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, "tennet_balance")},
            name="TenneT Balance Delta High Resolution",
            manufacturer="TenneT"
        )

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
        self._attr_icon = meta.get("icon")

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, "tennet_balance")},
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