"""Tests for the simulated battery."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    mock_restore_cache,
)

from custom_components.remote_sensors.simulatedbattery import (
    MAX_SOC_PCT,
    MIN_SOC_PCT,
    SELF_CONSUMPTION_W,
    advance_soc,
)

DOMAIN = "remote_sensors"
ENTITY_ID = "sensor.remote_simulatedbatterysoc"
MODE_ENTITY_ID = "sensor.simulated_battery_mode"
SOLAR_ENTITY_ID = "sensor.remote_solarpower"
SERVICE = "set_simulated_battery_mode"

# 5 kW into 15 kWh is a third of the capacity per hour, 1.5 kW out is 10 %.
CHARGE_PCT_PER_MINUTE = 100 / 3 / 60
DISCHARGE_PCT_PER_MINUTE = 10 / 60
SELL_PCT_PER_MINUTE = 100 / 3 / 60
# The self-consumption of 100 W is 2/3 % per hour, in every mode.
SELF_PCT_PER_HOUR = 2 / 3
SELF_PCT_PER_MINUTE = SELF_PCT_PER_HOUR / 60

# The change of the SoC per minute in each mode, self-consumption included.
PCT_PER_MINUTE = {
    "standby": -SELF_PCT_PER_MINUTE,
    "charge": CHARGE_PCT_PER_MINUTE - SELF_PCT_PER_MINUTE,
    "discharge": -DISCHARGE_PCT_PER_MINUTE - SELF_PCT_PER_MINUTE,
    "maxuse": -DISCHARGE_PCT_PER_MINUTE - SELF_PCT_PER_MINUTE,
    "pvcharge": -SELF_PCT_PER_MINUTE,
    "sell": -SELL_PCT_PER_MINUTE - SELF_PCT_PER_MINUTE,
}


async def _setup(hass: HomeAssistant) -> None:
    """Set up Remote Sensors without any remote polling."""
    coordinator = MagicMock(sensor_specs=())
    coordinator.async_setup = AsyncMock()
    coordinator.async_shutdown = AsyncMock()
    entry = MockConfigEntry(domain=DOMAIN, data={"remote_name": "Remote"})
    entry.add_to_hass(hass)
    with patch(
        "custom_components.remote_sensors.RemoteCoordinator",
        return_value=coordinator,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


@pytest.fixture
async def integration(hass: HomeAssistant) -> None:
    await _setup(hass)


async def _set_mode(hass: HomeAssistant, mode: str) -> None:
    await hass.services.async_call(
        DOMAIN, SERVICE, {"entity_id": ENTITY_ID, "mode": mode}, blocking=True
    )


async def _tick(hass: HomeAssistant, freezer, **delta) -> None:
    """Let time pass and fire the time listeners."""
    freezer.tick(timedelta(**delta))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def _soc(hass: HomeAssistant) -> int:
    """The SoC shown; fails when the state is not a whole number."""
    return int(hass.states.get(ENTITY_ID).state)


@pytest.mark.parametrize("mode", list(PCT_PER_MINUTE))
def test_advance_soc_rate_of_every_mode(mode: str) -> None:
    assert advance_soc(50.0, mode, 60) == pytest.approx(50 + PCT_PER_MINUTE[mode])


def test_self_consumption_is_100_w() -> None:
    assert SELF_CONSUMPTION_W == 100.0


def test_maxuse_is_discharge_and_pvcharge_without_solar_is_standby() -> None:
    assert advance_soc(50.0, "maxuse", 600) == advance_soc(50.0, "discharge", 600)
    assert advance_soc(50.0, "pvcharge", 600) == advance_soc(50.0, "standby", 600)
    assert advance_soc(50.0, "pvcharge", 600, 0.0) == advance_soc(50.0, "standby", 600)


def test_pvcharge_charges_with_the_solar_power() -> None:
    # 3 kW into 15 kWh is a fifth of the capacity per hour.
    assert advance_soc(50.0, "pvcharge", 3600, 3.0) == pytest.approx(
        70.0 - SELF_PCT_PER_HOUR
    )
    assert advance_soc(50.0, "pvcharge", 60, 1.5) == pytest.approx(
        50 + 10 / 60 - SELF_PCT_PER_MINUTE
    )


def test_pvcharge_is_limited_to_the_charge_power() -> None:
    assert advance_soc(50.0, "pvcharge", 3600, 12.0) == advance_soc(
        50.0, "charge", 3600
    )


def test_pvcharge_ignores_negative_solar_power() -> None:
    assert advance_soc(50.0, "pvcharge", 3600, -2.0) == advance_soc(
        50.0, "standby", 3600
    )


@pytest.mark.parametrize("mode", ["standby", "charge", "discharge", "maxuse", "sell"])
def test_solar_power_only_matters_in_pvcharge(mode: str) -> None:
    assert advance_soc(50.0, mode, 600, 4.0) == advance_soc(50.0, mode, 600)


def test_sell_empties_the_battery_at_5_kw() -> None:
    # 14.25 kWh at 5.1 kW (with the self-consumption) takes 2h48m.
    assert advance_soc(100.0, "sell", 2.8 * 3600) == pytest.approx(MIN_SOC_PCT)
    assert advance_soc(100.0, "sell", 2.7 * 3600) > MIN_SOC_PCT


def test_advance_soc_charge_and_discharge_rates() -> None:
    assert advance_soc(50.0, "charge", 60) == pytest.approx(
        50 + CHARGE_PCT_PER_MINUTE - SELF_PCT_PER_MINUTE
    )
    assert advance_soc(50.0, "discharge", 60) == pytest.approx(
        50 - DISCHARGE_PCT_PER_MINUTE - SELF_PCT_PER_MINUTE
    )


@pytest.mark.parametrize("mode", ["standby", "pvcharge", "", "unknown"])
def test_advance_soc_idle_modes_only_self_consume(mode: str) -> None:
    assert advance_soc(50.0, mode, 3600) == pytest.approx(50 - SELF_PCT_PER_HOUR)


def test_self_consumption_does_not_go_below_the_minimum() -> None:
    assert advance_soc(MIN_SOC_PCT, "standby", 3600) == MIN_SOC_PCT


def test_advance_soc_is_limited_to_the_soc_window() -> None:
    assert advance_soc(99.9, "charge", 3600) == MAX_SOC_PCT
    assert advance_soc(5.1, "discharge", 3600) == MIN_SOC_PCT
    assert advance_soc(120.0, "standby", 0) == MAX_SOC_PCT


def test_advance_soc_ignores_negative_elapsed_time() -> None:
    assert advance_soc(50.0, "charge", -60) == 50.0


def test_full_charge_from_the_minimum_takes_2h55m() -> None:
    # 14.25 kWh at 4.9 kW (with the self-consumption) takes 2h54.5m.
    assert advance_soc(MIN_SOC_PCT, "charge", 2.92 * 3600) == pytest.approx(100.0)
    assert advance_soc(MIN_SOC_PCT, "charge", 2.9 * 3600) < 100.0


async def test_entity_starts_at_min_soc_in_standby(hass, integration) -> None:
    state = hass.states.get(ENTITY_ID)

    assert state.state == "5"
    assert state.attributes["mode"] == "standby"
    assert state.attributes["unit_of_measurement"] == "%"
    assert state.attributes["device_class"] == "battery"
    assert state.attributes["friendly_name"] == "Remote Simulated Battery SoC"


async def test_soc_is_shown_as_a_whole_percent(hass, freezer, integration) -> None:
    await _set_mode(hass, "charge")
    await _tick(hass, freezer, hours=1)

    # 5 + 33.33 - 0.67 = 37.67
    assert hass.states.get(ENTITY_ID).state == "38"


async def test_the_fraction_is_kept_between_updates(hass, freezer) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "50", {"mode": "standby"})])
    await _setup(hass)
    await _set_mode(hass, "charge")

    # Every update adds 0.14 %, which would vanish if each one was rounded.
    for _ in range(8):
        await _tick(hass, freezer, seconds=15)

    assert _soc(hass) == 51


async def test_charge_raises_soc_every_15_seconds(hass, freezer) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "50.4", {"mode": "standby"})])
    await _setup(hass)
    await _set_mode(hass, "charge")
    assert hass.states.get(ENTITY_ID).attributes["mode"] == "charge"

    # 50.4 + 0.14 rounds up to 51.
    await _tick(hass, freezer, seconds=14)
    assert _soc(hass) == 50

    await _tick(hass, freezer, seconds=1)
    assert _soc(hass) == 51


@pytest.mark.parametrize("mode", list(PCT_PER_MINUTE))
async def test_every_mode_is_accepted_and_moves_the_soc(
    hass, freezer, mode: str
) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "50", {"mode": "standby"})])
    await _setup(hass)

    await _set_mode(hass, mode)
    assert hass.states.get(ENTITY_ID).attributes["mode"] == mode

    await _tick(hass, freezer, minutes=10)
    assert _soc(hass) == round(50 + 10 * PCT_PER_MINUTE[mode])


def _set_solar(hass: HomeAssistant, state: str, unit: str | None = "W") -> None:
    attributes = {} if unit is None else {"unit_of_measurement": unit}
    hass.states.async_set(SOLAR_ENTITY_ID, state, attributes)


async def test_pvcharge_raises_soc_with_the_solar_power(hass, freezer) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "50", {"mode": "standby"})])
    await _setup(hass)
    _set_solar(hass, "3000")
    await _set_mode(hass, "pvcharge")

    await _tick(hass, freezer, hours=1)

    # 3 kW into 15 kWh is 20 % per hour: 50 + 20 - 0.67 = 69.33
    assert _soc(hass) == 69


async def test_pvcharge_follows_changes_of_the_solar_power(hass, freezer) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "50", {"mode": "standby"})])
    await _setup(hass)
    await _set_mode(hass, "pvcharge")

    _set_solar(hass, "1500")
    await _tick(hass, freezer, hours=1)
    # 50 + 10 - 0.67 = 59.33
    assert _soc(hass) == 59

    _set_solar(hass, "0")
    await _tick(hass, freezer, hours=1)
    # 59.33 - 0.67 = 58.67
    assert _soc(hass) == 59

    _set_solar(hass, "4500")
    await _tick(hass, freezer, hours=1)
    # 58.67 + 30 - 0.67 = 88
    assert _soc(hass) == 88


async def test_pvcharge_accepts_a_solar_power_in_kw(hass, freezer) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "50", {"mode": "standby"})])
    await _setup(hass)
    _set_solar(hass, "3", "kW")
    await _set_mode(hass, "pvcharge")

    await _tick(hass, freezer, hours=1)

    assert _soc(hass) == 69


async def test_pvcharge_is_limited_to_the_charge_power(hass, freezer) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "50", {"mode": "standby"})])
    await _setup(hass)
    _set_solar(hass, "9000")
    await _set_mode(hass, "pvcharge")

    await _tick(hass, freezer, hours=1)

    # 5 kW into 15 kWh is 33.33 % per hour: 50 + 33.33 - 0.67 = 82.67
    assert _soc(hass) == 83


async def test_pvcharge_stops_at_100_percent(hass, freezer) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "95", {"mode": "standby"})])
    await _setup(hass)
    _set_solar(hass, "5000")
    await _set_mode(hass, "pvcharge")

    await _tick(hass, freezer, hours=2)

    assert _soc(hass) == 100


@pytest.mark.parametrize("solar", ["unavailable", "unknown", "nan", "oops", "-800"])
async def test_pvcharge_only_self_consumes_when_the_solar_power_is_unusable(
    hass, freezer, solar: str
) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "50", {"mode": "standby"})])
    await _setup(hass)
    _set_solar(hass, solar)
    await _set_mode(hass, "pvcharge")

    await _tick(hass, freezer, hours=3)

    # 50 - 2 = 48
    assert _soc(hass) == 48


async def test_pvcharge_only_self_consumes_without_a_solar_power_sensor(
    hass, freezer
) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "50", {"mode": "standby"})])
    await _setup(hass)
    await _set_mode(hass, "pvcharge")

    await _tick(hass, freezer, hours=3)

    assert _soc(hass) == 48


@pytest.mark.parametrize("mode", ["standby", "discharge"])
async def test_solar_power_does_not_charge_in_other_modes(
    hass, freezer, mode: str
) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "50", {"mode": "standby"})])
    await _setup(hass)
    _set_solar(hass, "5000")
    await _set_mode(hass, mode)

    await _tick(hass, freezer, hours=1)

    assert _soc(hass) == round(50 + PCT_PER_MINUTE[mode] * 60)


async def test_mode_change_counts_the_solar_charge_before_it(hass, freezer) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "50", {"mode": "standby"})])
    await _setup(hass)
    _set_solar(hass, "3000")
    await _set_mode(hass, "pvcharge")

    freezer.tick(timedelta(minutes=30))
    await _set_mode(hass, "standby")

    # 50 + 10 - 0.33 = 59.67
    assert _soc(hass) == 60

    await _tick(hass, freezer, hours=1)
    # 59.67 - 0.67 = 59
    assert _soc(hass) == 59


async def test_charge_stops_at_100_percent(hass, freezer, integration) -> None:
    await _set_mode(hass, "charge")

    for _ in range(3):
        await _tick(hass, freezer, hours=1)

    assert _soc(hass) == 100


async def test_discharge_lowers_soc_down_to_the_minimum(
    hass, freezer, integration
) -> None:
    await _set_mode(hass, "charge")
    await _tick(hass, freezer, hours=1)

    await _set_mode(hass, "discharge")
    await _tick(hass, freezer, minutes=10)
    # 5 + 33.33 - 0.67 - 1.78 = 35.89
    assert _soc(hass) == 36

    await _tick(hass, freezer, hours=10)
    assert _soc(hass) == 5


async def test_standby_only_self_consumes(hass, freezer, integration) -> None:
    await _set_mode(hass, "charge")
    await _tick(hass, freezer, minutes=30)
    charged = _soc(hass)

    await _set_mode(hass, "standby")
    await _tick(hass, freezer, hours=3)

    # 5 + 16.67 - 0.33 = 21.33
    assert charged == 21
    # 21.33 - 2 = 19.33
    assert _soc(hass) == 19


async def test_mode_change_between_ticks_counts_the_time_in_the_old_mode(
    hass, freezer
) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "50", {"mode": "standby"})])
    await _setup(hass)

    await _set_mode(hass, "charge")
    freezer.tick(timedelta(minutes=10))
    await _set_mode(hass, "discharge")

    # 50 + 5.56 - 0.11 = 55.44
    assert _soc(hass) == 55

    await _tick(hass, freezer, minutes=20)
    # 55.44 - 3.33 - 0.22 = 51.89
    assert _soc(hass) == 52


async def test_unknown_mode_is_rejected(hass, integration) -> None:
    with pytest.raises(vol.Invalid):
        await _set_mode(hass, "fly")

    assert hass.states.get(ENTITY_ID).attributes["mode"] == "standby"


async def test_soc_and_mode_are_restored(hass, freezer) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "42", {"mode": "discharge"})])
    await _setup(hass)

    state = hass.states.get(ENTITY_ID)
    assert state.state == "42"
    assert state.attributes["mode"] == "discharge"

    await _tick(hass, freezer, minutes=10)
    # 42 - 1.67 - 0.11 = 40.22
    assert _soc(hass) == 40


async def test_restored_soc_is_limited_to_the_soc_window(hass) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "140", {"mode": "standby"})])
    await _setup(hass)

    assert _soc(hass) == 100


@pytest.mark.parametrize(
    "restored",
    [
        State(ENTITY_ID, "unavailable", {}),
        State(ENTITY_ID, "nan", {"mode": "nonsense"}),
        State(ENTITY_ID, "oops", {}),
    ],
)
async def test_unusable_restored_state_gives_the_defaults(hass, restored) -> None:
    mock_restore_cache(hass, [restored])
    await _setup(hass)

    state = hass.states.get(ENTITY_ID)
    assert state.state == "5"
    assert state.attributes["mode"] == "standby"


async def test_mode_sensor_starts_in_standby(hass, integration) -> None:
    state = hass.states.get(MODE_ENTITY_ID)

    assert state.state == "standby"
    assert state.attributes["device_class"] == "enum"
    assert state.attributes["friendly_name"] == "Remote Simulated Battery Mode"


@pytest.mark.parametrize("mode", list(PCT_PER_MINUTE))
async def test_mode_sensor_shows_the_mode_that_was_set(
    hass, integration, mode: str
) -> None:
    await _set_mode(hass, mode)

    assert hass.states.get(MODE_ENTITY_ID).state == mode


async def test_mode_sensor_follows_every_mode_change(hass, integration) -> None:
    await _set_mode(hass, "charge")
    assert hass.states.get(MODE_ENTITY_ID).state == "charge"

    await _set_mode(hass, "sell")
    assert hass.states.get(MODE_ENTITY_ID).state == "sell"


async def test_mode_sensor_keeps_the_mode_when_the_mode_is_rejected(
    hass, integration
) -> None:
    await _set_mode(hass, "charge")
    with pytest.raises(vol.Invalid):
        await _set_mode(hass, "fly")

    assert hass.states.get(MODE_ENTITY_ID).state == "charge"


async def test_mode_sensor_shows_the_restored_mode(hass) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "42", {"mode": "discharge"})])
    await _setup(hass)

    assert hass.states.get(MODE_ENTITY_ID).state == "discharge"


async def test_mode_sensor_is_standby_when_the_restored_mode_is_unusable(
    hass,
) -> None:
    mock_restore_cache(hass, [State(ENTITY_ID, "42", {"mode": "nonsense"})])
    await _setup(hass)

    assert hass.states.get(MODE_ENTITY_ID).state == "standby"
