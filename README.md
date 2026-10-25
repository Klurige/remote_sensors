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

## Fake Compact Levels (diagnostic)

A `Fake Compact Levels` diagnostic sensor is always created alongside the configured
sensors. It emits the same `minutes:level_length:passed:future` compact string format
as Energy Advisor's real compact-levels sensor, using the same 15-minute level length,
but fills the levels with random data and advances through it once per real minute
instead of once per real 15 minutes. This cycles through many level transitions
quickly, making it useful for finding bugs in LevelIndicatorClock without waiting for
real price data to change.

It is disabled by default (enable it in the entity registry when needed). The level
length and update speed can be tuned via the `FAKE_LEVEL_LENGTH_MINUTES` and
`FAKE_UPDATE_SECONDS` constants in `custom_components/remote_sensors/fakecompactlevels.py`.

## Simulated Battery

A `Simulated Battery SoC` sensor (`sensor.remote_simulatedbatterysoc`) and a
`Simulated Battery Mode` sensor (`sensor.simulated_battery_mode`) are always
created. They stand in for a real battery so that Energy Advisor's battery charge
mode schedule can be tried out on a live system: point Energy Advisor's
`battery_soc_entity` at it and feed it the schedule's mode.

- **Input:** the action `remote_sensors.set_simulated_battery_mode` with the
  field `mode`, targeting the sensor. It accepts all of Energy Advisor's battery
  modes: `standby`, `charge`, `discharge`, `maxuse`, `pvcharge` and `sell`. The
  mode stays in force until the next action.
- **Output:** the state of charge as a whole percent, updated every 15 seconds
  and also at every mode change. The simulation keeps the fraction, so slow
  charging still adds up between the rounded values; after a restart it continues
  from the whole percent that was shown. The sensor has the attribute `mode` with
  the mode in force. The history is recorded.
- **Mode output:** the sensor `sensor.simulated_battery_mode` shows the mode in
  force as its state, e.g. `charge` after the action was called with
  `mode: charge`. It starts as `standby` and follows the mode restored after a
  restart.
- **Behaviour:** a 15 kWh battery that starts at 5 %. Conversion losses are not
  simulated. The SoC and the mode survive a restart.
- **Self-consumption:** the battery itself consumes 100 W in every mode, on top
  of the effect of the mode below, so the SoC also falls slowly in `standby`
  (2/3 % per hour) and charging is 100 W slower.

  | Mode | Effect on the SoC |
  |------|-------------------|
  | `charge` | Rises as if charged with 5 kW, up to 100 % |
  | `discharge` | Falls as if the battery supplied 1.5 kW, down to 5 % |
  | `maxuse` | Same as `discharge` |
  | `sell` | Falls as if the battery supplied 5 kW, down to 5 % |
  | `standby` | No effect (only the self-consumption) |
  | `pvcharge` | Rises as if charged with the power of the `Solar Power` sensor (`sensor.remote_solarpower`, in W or kW), at most 5 kW, up to 100 %. No effect while that sensor is missing, unavailable or negative |

  The solar power is read at every update (and at every mode change) and is
  taken to have been constant since the previous one, so with the `solarpower`
  entry in `dev_config.py` polled every 30 seconds the SoC follows the sun
  closely.

An automation that makes the simulated battery follow the schedule:

```yaml
triggers:
  - trigger: state
    entity_id: sensor.energy_advisor_battery_charge_mode
actions:
  - action: remote_sensors.set_simulated_battery_mode
    target:
      entity_id: sensor.remote_simulatedbatterysoc
    data:
      mode: "{{ trigger.to_state.state }}"
```

Capacity, powers, self-consumption, SoC limits and update interval are the constants at the top of
`custom_components/remote_sensors/simulatedbattery.py`.

## Tests

The tests need `pytest-homeassistant-custom-component`. Energy Advisor's virtual
environment has it: `../energyadvisor/venv/bin/python -m pytest`.

## Notes

- `dev_config.py` is intended to be committed.
- `dev_secrets.py` must stay local and is ignored by git.
- The integration is designed for development convenience and should not be used in production environments.