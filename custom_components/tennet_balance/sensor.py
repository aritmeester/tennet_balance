from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers import entity_registry as er
from .const import DOMAIN, SENSOR_DESCRIPTIONS, REGULATION_PRICE_KEYS


REGULATION_STATE_ENUM_MAP = {
    -1: "down",
    0: "neutral",
    1: "up",
    2: "both",
}

REGULATION_STATE_ICON_MAP = {
    "down": "mdi:arrow-bottom-left-thin",
    "neutral": "mdi:arrow-right-thin",
    "up": "mdi:arrow-top-right-thin",
    "both": "mdi:arrow-top-right-bottom-left",
}

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
    sensors.extend(
        [
            RegulationStateEnumSensor(
                coordinator,
                environment_slug,
                device_identifier,
                "regulation_state_previous_isp",
                is_current_prediction=False,
            ),
            RegulationStateEnumSensor(
                coordinator,
                environment_slug,
                device_identifier,
                "regulation_state_current_isp_prediction",
                is_current_prediction=True,
            ),
            ApiLastSuccessSensor(
                coordinator,
                environment_slug,
                device_identifier,
            ),
            ApiResponseTimeSensor(
                coordinator,
                environment_slug,
                device_identifier,
            ),
            ApiConsecutiveFailuresSensor(
                coordinator,
                environment_slug,
                device_identifier,
            ),
        ]
    )
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
        self._attr_entity_registry_enabled_default = not self.key.startswith("power_mari_")
        if self._attr_device_class == SensorDeviceClass.MONETARY:
            self._attr_state_class = None

    @property
    def available(self):
        return super().available and self.coordinator.latest_point is not None

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


class _BaseRegulationStateSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        environment_slug: str,
        device_identifier: str,
        translation_key: str,
        is_current_prediction: bool,
    ):
        super().__init__(coordinator)
        self._device_identifier = device_identifier
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"tennet_balance_{environment_slug}_{translation_key}"
        self._is_current_prediction = is_current_prediction

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_identifier)},
            name="TenneT Balance Delta High Resolution",
            manufacturer="TenneT",
        )

    @property
    def available(self):
        return super().available and self.coordinator.rule_state_2_analysis is not None

    @property
    def _regulation_state(self):
        if self._is_current_prediction:
            return self.coordinator.regulation_state_current_isp_prediction
        return self.coordinator.regulation_state_previous_isp

    @property
    def extra_state_attributes(self):
        analysis = self.coordinator.rule_state_2_analysis or {}
        return {
            "current_isp_start": analysis.get("current_isp_start"),
            "previous_isp_start": analysis.get("previous_isp_start"),
        }


class RegulationStateEnumSensor(_BaseRegulationStateSensor):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(REGULATION_STATE_ENUM_MAP.values())

    @property
    def native_value(self):
        state = self._regulation_state
        if state is None:
            return None
        return REGULATION_STATE_ENUM_MAP.get(state, "neutral")

    @property
    def icon(self):
        value = self.native_value
        if value is None:
            return "mdi:arrow-right-thin"
        return REGULATION_STATE_ICON_MAP.get(value, "mdi:arrow-right-thin")


class _BaseApiDiagnosticSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, environment_slug: str, device_identifier: str, translation_key: str):
        super().__init__(coordinator)
        self._device_identifier = device_identifier
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"tennet_balance_{environment_slug}_{translation_key}"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_identifier)},
            name="TenneT Balance Delta High Resolution",
            manufacturer="TenneT",
        )


class ApiLastSuccessSensor(_BaseApiDiagnosticSensor):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, coordinator, environment_slug: str, device_identifier: str):
        super().__init__(coordinator, environment_slug, device_identifier, "api_last_success")

    @property
    def native_value(self):
        return self.coordinator.api_last_success


class ApiResponseTimeSensor(_BaseApiDiagnosticSensor):
    _attr_native_unit_of_measurement = "ms"
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator, environment_slug: str, device_identifier: str):
        super().__init__(coordinator, environment_slug, device_identifier, "api_response_time")

    @property
    def native_value(self):
        return self.coordinator.api_response_time_ms


class ApiConsecutiveFailuresSensor(_BaseApiDiagnosticSensor):
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator, environment_slug: str, device_identifier: str):
        super().__init__(coordinator, environment_slug, device_identifier, "api_consecutive_failures")

    @property
    def native_value(self):
        return self.coordinator.api_consecutive_failures

    @property
    def extra_state_attributes(self):
        return {
            "last_error": self.coordinator.api_last_error,
            "last_error_details": self.coordinator.api_last_error_details,
        }