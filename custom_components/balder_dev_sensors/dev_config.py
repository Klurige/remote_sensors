"""Tracked sensor catalog for Balder Dev Sensors.

This file intentionally contains no secrets so it can be committed to git.
Put Home Assistant connection details in ``dev_secrets.py`` instead.
"""

# Set to True to pre-fill config flow with development defaults.
DEV_DEFAULTS_ENABLED = True

SENSORS = {
    "inverterpower": {
        "name": "Inverter Power",
        "entity_id": "sensor.inverter_active_power",
        "native_unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
        "exclude_from_recording": False,
    },
    "batterymode": {
        "name": "Battery Mode",
        "entity_id": "sensor.batterilage",
        "poll_seconds": 300,
        "value_type": "string",
        "include_attributes": True,
        "icon": "mdi:battery-sync",
    },
    "gridexport": {
        "name": "Grid Export",
        "entity_id": "sensor.elmatare_momentary_active_export",
        "native_unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
    },
    "gridimport": {
        "name": "Grid Import",
        "entity_id": "sensor.elmatare_momentary_active_import",
        "native_unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
    },
    "batterychargepower": {
        "name": "Battery Charge Power",
        "entity_id": "sensor.batteriladdeffekt",
        "native_unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
    },
    "batterydischargepower": {
        "name": "Battery Discharge Power",
        "entity_id": "sensor.batteriurladdeffekt",
        "native_unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
    },
    "batterysoc": {
        "name": "Battery SoC",
        "entity_id": "sensor.batteries_state_of_capacity",
        "native_unit_of_measurement": "%",
        "device_class": "battery",
        "state_class": "measurement",
        "poll_seconds": 60,
        "value_type": "float",
    },
    "photovoltaics": {
        "name": "Photovoltaics",
        "entity_id": "sensors.power_photovoltaics",
        "native_unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
    },
    "poolpumppower": {
        "name": "Pool Pump Power",
        "entity_id": "sensor.pool_julgran_power",
        "native_unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
    },
    "waterheaterpower": {
        "name": "Water Heater Power",
        "entity_id": "sensor.varmvatten_effekt",
        "native_unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
    },
    "dehumidifierpower": {
        "name": "Dehumidifier Power",
        "entity_id": "sensor.krypgrund_effekt",
        "native_unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
    },
    "forecast": {
        "name": "Forecast",
        "entity_id": "sensor.home_energy_production_today",
        "poll_seconds": 300,
        "value_type": "float",
        "icon": "mdi:solar-power-variant",
    },
    "forecasttomorrow": {
        "name": "Forecast Tomorrow",
        "entity_id": "sensor.home_energy_production_tomorrow",
        "poll_seconds": 300,
        "value_type": "float",
        "icon": "mdi:weather-sunny-alert",
    },
}
