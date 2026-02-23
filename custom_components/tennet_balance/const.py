from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import CURRENCY_EURO, Platform, UnitOfPower

DOMAIN = "tennet_balance"
PLATFORMS = (Platform.SENSOR, Platform.BINARY_SENSOR)

CONF_KEEP_LAST_REGULATION_PRICES = "keep_last_regulation_prices"

REGULATION_PRICE_KEYS = {
    "max_upw_regulation_price",
    "min_downw_regulation_price",
}

from .generated_points import GENERATED_SENSOR_DESCRIPTIONS

SENSOR_META_OVERRIDES = {
    "mid_price": {"unit": CURRENCY_EURO, "device_class": SensorDeviceClass.MONETARY},
    "power_afrr_in": {"unit": UnitOfPower.MEGA_WATT, "device_class": SensorDeviceClass.POWER, "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:transmission-tower-import"},
    "power_afrr_out": {"unit": UnitOfPower.MEGA_WATT, "device_class": SensorDeviceClass.POWER, "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:transmission-tower-export"},
    "power_igcc_in": {"unit": UnitOfPower.MEGA_WATT, "device_class": SensorDeviceClass.POWER, "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:transmission-tower-import"},
    "power_igcc_out": {"unit": UnitOfPower.MEGA_WATT, "device_class": SensorDeviceClass.POWER, "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:transmission-tower-export"},
    "power_mari_in": {"unit": UnitOfPower.MEGA_WATT, "device_class": SensorDeviceClass.POWER, "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:transmission-tower-import"},
    "power_mari_out": {"unit": UnitOfPower.MEGA_WATT, "device_class": SensorDeviceClass.POWER, "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:transmission-tower-export"},
    "power_mfrrda_in": {"unit": UnitOfPower.MEGA_WATT, "device_class": SensorDeviceClass.POWER, "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:transmission-tower-import"},
    "power_mfrrda_out": {"unit": UnitOfPower.MEGA_WATT, "device_class": SensorDeviceClass.POWER, "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:transmission-tower-export"},
    "power_picasso_in": {"unit": UnitOfPower.MEGA_WATT, "device_class": SensorDeviceClass.POWER, "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:transmission-tower-import"},
    "power_picasso_out": {"unit": UnitOfPower.MEGA_WATT, "device_class": SensorDeviceClass.POWER, "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:transmission-tower-export"},
    "max_upw_regulation_price": {"unit": CURRENCY_EURO, "device_class": SensorDeviceClass.MONETARY},
    "min_downw_regulation_price": {"unit": CURRENCY_EURO, "device_class": SensorDeviceClass.MONETARY},
}

SENSOR_DESCRIPTIONS = {
    key: {"name": f"TenneT {meta['name']}", **SENSOR_META_OVERRIDES[key]}
    for key, meta in GENERATED_SENSOR_DESCRIPTIONS.items()
}
