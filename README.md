# Balder Dev Sensors

A Home Assistant custom integration that proxies a set of sensors from the remote **Balder** HA instance into the local development instance. This avoids needing the `remote_homeassistant` integration to be active during development.

---

## Purpose

When developing features that depend on live data from Balder (e.g. inverter power, battery state), this integration polls the Balder HA REST API directly using a long-lived access token. Sensors appear locally and update based on their configured polling intervals, making them available to other integrations such as `electricitypricelevels`.

The integration is **not intended for production use**. The sensor catalog lives in tracked `custom_components/balder_dev_sensors/dev_config.py`, while secrets live in gitignored `custom_components/balder_dev_sensors/dev_secrets.py`.

---

## Configuration

Keep the tracked sensor catalog in `custom_components/balder_dev_sensors/dev_config.py`:

```python
SENSORS = {
    "inverterpower": {
        "name": "Inverter Power",
        "entity_id": "sensor.inverter_active_power",
        "native_unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "poll_seconds": 30,
        "value_type": "float",
    },
}
```

Create a local-only `custom_components/balder_dev_sensors/dev_secrets.py`:

```python
HA_URL = "http://<balder-ip>:8123"
HA_TOKEN = "<long-lived-access-token>"
```

If `dev_secrets.py` is absent the integration loads without errors but all sensors remain `None`.

---

## Implemented sensors

All sensors are declared in one place: `custom_components/balder_dev_sensors/dev_config.py`.

Each entry defines the remote entity id, polling interval, data type, and optional Home Assistant fields such as unit, device class, state class, icon, and whether remote attributes should be exposed.

---

## Notes

- `dev_config.py` is intended to be committed.
- `dev_secrets.py` must stay local and is ignored by git.
- The integration is designed for development convenience and should not be used in production environments.