# Remote Sensors

A Home Assistant custom integration that proxies selected sensors from a remote HA instance into the local instance.

---

## Purpose

This integration polls the remote HA REST API with a long-lived access token. Sensors appear locally and update based on their configured polling intervals.

The integration is intended for development/testing convenience. The sensor catalog lives in tracked `custom_components/remote_sensors/dev_config.py`, while secrets live in gitignored `custom_components/remote_sensors/dev_secrets.py`.

---

## Configuration

When adding the integration in Home Assistant, enter **Remote Name** (for example `Balder`). Sensor friendly names are prefixed with this value. You can later change it in the integration options.

Keep the tracked sensor catalog in `custom_components/remote_sensors/dev_config.py`:

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

Create a local-only `custom_components/remote_sensors/dev_secrets.py`:

```python
HA_URL = "http://<remote-ha-host>:8123"
HA_TOKEN = "<long-lived-access-token>"
```

If `dev_secrets.py` is absent the integration loads without errors but all sensors remain `None`.

---

## Implemented sensors

All sensors are declared in one place: `custom_components/remote_sensors/dev_config.py`.

Each entry defines the remote entity id, polling interval, data type, and optional Home Assistant fields such as unit, device class, state class, icon, and whether remote attributes should be exposed.

---

## Notes

- `dev_config.py` is intended to be committed.
- `dev_secrets.py` must stay local and is ignored by git.
- The integration is designed for development convenience and should not be used in production environments.