# Balder Dev Sensors

A Home Assistant custom integration that proxies a set of sensors from the remote **Balder** HA instance into the local development instance. This avoids needing the `remote_homeassistant` integration to be active during development.

---

## Purpose

When developing features that depend on live data from Balder (e.g. inverter power, battery state), this integration polls the Balder HA REST API directly using a long-lived access token. Sensors appear locally and update every 30 seconds, making them available to other integrations such as `electricitypricelevels`.

The integration is **not intended for production use**. All configuration (URL, token, entity IDs) lives in a gitignored `dev_config.py` file.

---

## Configuration

Create `custom_components/balder_dev_sensors/dev_config.py` (gitignored — never commit this):

```python
HA_URL = "http://<balder-ip>:8123"
HA_TOKEN = "<long-lived-access-token>"

DEV_DEFAULTS = {
    "power_entity": "sensor.<inverter_power_entity_id>",
}
```

If the file is absent the integration loads without errors but all sensors remain `None`.

---

## Implemented sensors

| Entity ID | Unit | Remote entity | Description |
|---|---|---|---|
| `sensor.balder_inverterpower` | W | configured via `DEV_DEFAULTS["power_entity"]` | Inverter AC output power |

---

## TODO — sensors still to implement

These sensors exist in the `cleanup` branch of `electricitypricelevels` and should be migrated here:

| Sensor | Unit | Remote entity ID | Description |
|---|---|---|---|
| `sensor.balderbatterymode` | — (string) | `sensor.batterilage` | Battery charge/discharge mode; includes all remote attributes |
| `sensor.baldergridexport` | W | `sensor.elmatare_momentary_active_export` | Grid export power |
| `sensor.balderbatterychargepower` | W | `sensor.batteriladdeffekt` | Battery charge power |
| `sensor.balderbatterysoc` | % | `sensor.batteries_state_of_capacity` | Battery state of charge |

For each sensor: add a fetch call in `coordinator.py`, a callback pair (register/unregister/notify), and a sensor class following the pattern of `inverterpower.py`.
