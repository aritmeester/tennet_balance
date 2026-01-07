DOMAIN = "tennet_balance"
PLATFORMS = ["sensor"]

from .generated_points import GENERATED_SENSOR_DESCRIPTIONS

SENSOR_META_OVERRIDES = {
    "mid_price": {"unit": "EUR", "device_class": "monetary", "state_class": "measurement"},
    "power_afrr_in": {"unit": "MW", "device_class": "power", "state_class": "measurement", "icon": "mdi:transmission-tower-import"},
    "power_afrr_out": {"unit": "MW", "device_class": "power", "state_class": "measurement", "icon": "mdi:transmission-tower-export"},
    "power_igcc_in": {"unit": "MW", "device_class": "power", "state_class": "measurement", "icon": "mdi:transmission-tower-import"},
    "power_igcc_out": {"unit": "MW", "device_class": "power", "state_class": "measurement", "icon": "mdi:transmission-tower-export"},
    "power_mari_in": {"unit": "MW", "device_class": "power", "state_class": "measurement", "icon": "mdi:transmission-tower-import"},
    "power_mari_out": {"unit": "MW", "device_class": "power", "state_class": "measurement", "icon": "mdi:transmission-tower-export"},
    "power_mfrrda_in": {"unit": "MW", "device_class": "power", "state_class": "measurement", "icon": "mdi:transmission-tower-import"},
    "power_mfrrda_out": {"unit": "MW", "device_class": "power", "state_class": "measurement", "icon": "mdi:transmission-tower-export"},
    "power_picasso_in": {"unit": "MW", "device_class": "power", "state_class": "measurement", "icon": "mdi:transmission-tower-import"},
    "power_picasso_out": {"unit": "MW", "device_class": "power", "state_class": "measurement", "icon": "mdi:transmission-tower-export"},
    "max_upw_regulation_price": {"unit": "EUR", "device_class": "monetary", "state_class": "measurement"},
    "min_downw_regulation_price": {"unit": "EUR", "device_class": "monetary", "state_class": "measurement"},
}

SENSOR_DESCRIPTIONS = {
    key: {"name": f"TenneT {meta['name']}", **SENSOR_META_OVERRIDES[key]}
    for key, meta in GENERATED_SENSOR_DESCRIPTIONS.items()
}
