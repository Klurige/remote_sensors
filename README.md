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

| Entity ID | Unit | Remote entity | Poll interval | Description |
|---|---|---|---|---|
| `sensor.balder_inverterpower` | W | configured via `DEV_DEFAULTS["power_entity"]` | 30 s | Inverter AC output power |
| `sensor.balder_batterymode` | — (string) | `sensor.batterilage` | 300 s | Battery charge/discharge mode + all remote attributes |
| `sensor.balder_gridexport` | W | `sensor.elmatare_momentary_active_export` | 30 s | Grid export power |
| `sensor.balder_batterychargepower` | W | `sensor.batteriladdeffekt` | 30 s | Battery charge power |
| `sensor.balder_batterysoc` | % | `sensor.batteries_state_of_capacity` | 60 s | Battery state of charge |

---

## TODO

All sensors from the original list are now implemented.
