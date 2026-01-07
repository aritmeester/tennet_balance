DOMAIN = "tennet_balance"
PLATFORMS = ["sensor"]

from .generated_points import GENERATED_SENSOR_DESCRIPTIONS

SENSOR_META_OVERRIDES = {
    "mid_price": {"unit": "EUR", "device_class": "monetary", "state_class": "measurement"},
    "power_afrr_in": {"unit": "MW", "device_class": "power", "state_class": "measurement"},
    "power_afrr_out": {"unit": "MW", "device_class": "power", "state_class": "measurement"},
    "power_igcc_in": {"unit": "MW", "device_class": "power", "state_class": "measurement"},
    "power_igcc_out": {"unit": "MW", "device_class": "power", "state_class": "measurement"},
    "power_mari_in": {"unit": "MW", "device_class": "power", "state_class": "measurement"},
    "power_mari_out": {"unit": "MW", "device_class": "power", "state_class": "measurement"},
    "power_mfrrda_in": {"unit": "MW", "device_class": "power", "state_class": "measurement"},
    "power_mfrrda_out": {"unit": "MW", "device_class": "power", "state_class": "measurement"},
    "power_picasso_in": {"unit": "MW", "device_class": "power", "state_class": "measurement"},
    "power_picasso_out": {"unit": "MW", "device_class": "power", "state_class": "measurement"},
    "max_upw_regulation_price": {"unit": "EUR", "device_class": "monetary", "state_class": "measurement"},
    "min_downw_regulation_price": {"unit": "EUR", "device_class": "monetary", "state_class": "measurement"},
}

SENSOR_DESCRIPTIONS = {
    key: {"name": f"TenneT {meta['name']}", **SENSOR_META_OVERRIDES[key]}
    for key, meta in GENERATED_SENSOR_DESCRIPTIONS.items()
}
