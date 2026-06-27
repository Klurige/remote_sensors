"""Tracked sensor catalog for Remote Sensors.

This file intentionally contains no secrets so it can be committed to git.
Put Home Assistant connection details in ``dev_secrets.py`` instead.
"""

# Some integrations get the values from their public sources:
## Nord pool
## Open Meteo Solar forecast (today and tomorrow)


SENSORS = {
    # Power coming from the solar panels. This will show the wrong value if
    # If grid export is not allowed, this value will be capped to household consumption (and eventual battery charge)
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
    # The live auto battery mode. Used for comparison only
    "batterymode": {
        "name": "Battery Mode",
        "entity_id": "sensor.batterilage",
        "poll_seconds": 300,
        "value_type": "string",
        "include_attributes": True,
        "icon": "mdi:battery-sync",
    },
    # Amount of power being exported to the grid
    "gridexport": {
        "name": "Grid Export",
        "entity_id": "sensor.elmatare_momentary_active_export",
        "native_unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
    },
    # Amount of power imported from the grid
    "gridimport": {
        "name": "Grid Import",
        "entity_id": "sensor.elmatare_momentary_active_import",
        "native_unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
    },
    # Power going to the battery
    "batterychargepower": {
        "name": "Battery Charge Power",
        "entity_id": "sensor.batteriladdeffekt",
        "native_unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
    },
    # Power coming from the battery
    "batterydischargepower": {
        "name": "Battery Discharge Power",
        "entity_id": "sensor.batteriurladdningseffekt",
        "native_unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
    },
    # Battery charge level
    "batterysoc": {
        "name": "Battery SoC",
        "entity_id": "sensor.batteries_state_of_capacity",
        "native_unit_of_measurement": "%",
        "device_class": "battery",
        "state_class": "measurement",
        "poll_seconds": 60,
        "value_type": "float",
    },
    # Power used by the pool pump
    "poolpumppower": {
        "name": "Pool Pump Power",
        "entity_id": "sensor.pool_julgran_power",
        "native_unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
    },
    # Power used by the water heater
    "waterheaterpower": {
        "name": "Water Heater Power",
        "entity_id": "sensor.varmvatten_effekt",
        "native_unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
    },
    # Bathroom air humidity. Used to detect shower events.
    "bathroomhumidity": {
        "name": "Bathroom Humidity",
        "entity_id": "sensor.badrum_klimat_humidity",
        "native_unit_of_measurement": "%",
        "device_class": "humidity",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
    },
    # Total cumulative household energy consumption from the smart meter.
    # Used by the battery optimizer for nightly base-load learning (Step 7).
    "powermeterconsumption": {
        "name": "Power Meter Consumption",
        "entity_id": "sensor.power_meter_consumption",
        "native_unit_of_measurement": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "poll_seconds": 60,
        "value_type": "float",
        "exclude_from_recording": False,
    },
    # On/off state of the water heater. Used to exclude noisy nights from
    # the base-load learning window (01:00–04:00).
    "waterheateractive": {
        "name": "Water Heater Active",
        "entity_id": "switch.varmvatten_brytare",
        "poll_seconds": 60,
        "value_type": "string",
    },
    # On/off state of the central heating. Same purpose as waterheateractive.
    "centralheatingactive": {
        "name": "Central Heating Active",
        "entity_id": "input_boolean.varme",
        "poll_seconds": 60,
        "value_type": "string",
    },
}
