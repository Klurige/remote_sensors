"""Simulated battery for Remote Sensors.

A stand-in for a real home battery, used to try out Energy Advisor's battery
charge mode schedule on a live system. The input is the action
``remote_sensors.set_simulated_battery_mode`` with any of Energy Advisor's
battery modes; the output is the state of charge (SoC) in percent. The mode in
force is also shown by its own sensor, ``sensor.simulated_battery_mode``.

The mode stays in force until the next action. Every ``UPDATE_SECONDS`` the SoC
moves by the power of the mode (``MODE_POWER_KW``): ``charge`` charges, while
``discharge``, ``maxuse`` and ``sell`` drain the battery. ``standby`` adds
nothing. ``pvcharge`` charges with the power that the solar power sensor
(``SOLAR_POWER_ENTITY_ID``) shows, up to ``CHARGE_POWER_KW``, and adds nothing
while that sensor is unavailable. In every mode the battery also consumes
``SELF_CONSUMPTION_W`` itself, so it slowly drains even in ``standby``. The SoC
is limited to ``MIN_SOC_PCT``..``MAX_SOC_PCT``. Conversion losses are not
simulated. The sensor shows the SoC rounded to a whole percent, while the
simulation keeps the fraction. The SoC and the mode are restored after a
restart (from the whole percent that was shown).
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

BATTERY_CAPACITY_KWH = 15.0
CHARGE_POWER_KW = 5.0
DISCHARGE_POWER_KW = 1.5
SELL_POWER_KW = 5.0
MIN_SOC_PCT = 5.0
MAX_SOC_PCT = 100.0

# What the battery itself consumes, in every mode (also ``standby``).
SELF_CONSUMPTION_W = 100.0

# How often (in real seconds) the SoC is brought up to date.
UPDATE_SECONDS = 15

# The sensor with the power of the solar panels, which ``pvcharge`` charges with.
SOLAR_POWER_ENTITY_ID = "sensor.remote_solarpower"

MODE_STANDBY = "standby"
MODE_CHARGE = "charge"
MODE_DISCHARGE = "discharge"
MODE_MAXUSE = "maxuse"
MODE_PVCHARGE = "pvcharge"
MODE_SELL = "sell"

# Power into (positive) or out of (negative) the battery in each mode. In
# ``pvcharge`` it is the solar power, see ``mode_power_kw``.
MODE_POWER_KW = {
    MODE_STANDBY: 0.0,
    MODE_CHARGE: CHARGE_POWER_KW,
    MODE_DISCHARGE: -DISCHARGE_POWER_KW,
    MODE_MAXUSE: -DISCHARGE_POWER_KW,
    MODE_PVCHARGE: 0.0,
    MODE_SELL: -SELL_POWER_KW,
}
MODES = tuple(MODE_POWER_KW)

ATTR_MODE = "mode"
SERVICE_SET_MODE = "set_simulated_battery_mode"


def mode_power_kw(mode: str, solar_power_kw: float = 0.0) -> float:
    """Return the power into (positive) or out of (negative) the battery.

    Inputs:
        - The mode (an unknown mode leaves the battery idle) and the power of
          the solar panels in kW, which only ``pvcharge`` uses.
    Outputs:
        - The power in kW. ``pvcharge`` gives the solar power, limited to
          ``0``..``CHARGE_POWER_KW``.
    """
    if mode == MODE_PVCHARGE:
        return min(max(solar_power_kw, 0.0), CHARGE_POWER_KW)
    return MODE_POWER_KW.get(mode, 0.0)


def advance_soc(
    soc_pct: float,
    mode: str,
    elapsed_seconds: float,
    solar_power_kw: float = 0.0,
) -> float:
    """Return the SoC after ``elapsed_seconds`` in ``mode``.

    Inputs:
        - The SoC in percent, the mode (see ``mode_power_kw``), the elapsed
          time in seconds and the solar power in kW (used by ``pvcharge``).
    Outputs:
        - The new SoC in percent, limited to ``MIN_SOC_PCT``..``MAX_SOC_PCT``.
          The self-consumption (``SELF_CONSUMPTION_W``) is drawn from the
          battery in every mode, on top of the power of the mode.
    """
    hours = max(elapsed_seconds, 0.0) / 3600
    power_kw = mode_power_kw(mode, solar_power_kw) - SELF_CONSUMPTION_W / 1000
    energy_kwh = power_kw * hours
    soc_pct += energy_kwh / BATTERY_CAPACITY_KWH * 100
    return min(max(soc_pct, MIN_SOC_PCT), MAX_SOC_PCT)


class SimulatedBatterySensor(RestoreEntity, SensorEntity):
    """The SoC of a simulated battery, driven by the set mode action."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(
        self,
        hass: HomeAssistant,
        device_info: DeviceInfo,
        remote_name: str,
    ) -> None:
        self.hass = hass
        self.entity_id = "sensor.remote_simulatedbatterysoc"
        self._attr_unique_id = "remote_sensors_simulatedbatterysoc"
        self._attr_name = f"{remote_name} Simulated Battery SoC".strip()
        self._attr_device_info = device_info
        self._soc_pct = MIN_SOC_PCT
        self._mode = MODE_STANDBY
        self._mode_listeners: list[Callable[[], None]] = []
        self._last_update: datetime = dt_util.utcnow()

    @property
    def mode(self) -> str:
        """The mode in force."""
        return self._mode

    @callback
    def async_add_mode_listener(
        self, listener: Callable[[], None]
    ) -> Callable[[], None]:
        """Call ``listener`` whenever the mode is set; returns a remover."""
        self._mode_listeners.append(listener)

        @callback
        def remove() -> None:
            self._mode_listeners.remove(listener)

        return remove

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            soc = _parse_number(last_state.state)
            if soc is not None:
                self._soc_pct = min(max(soc, MIN_SOC_PCT), MAX_SOC_PCT)
            mode = last_state.attributes.get(ATTR_MODE)
            if mode in MODES:
                self._mode = mode
                self._notify_mode_listeners()
        # Time spent switched off is not simulated.
        self._last_update = dt_util.utcnow()
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._handle_tick, timedelta(seconds=UPDATE_SECONDS)
            )
        )

    @callback
    def _handle_tick(self, _now: Any) -> None:
        self._advance(dt_util.utcnow())
        self.async_write_ha_state()

    def _advance(self, now: datetime) -> None:
        """Move the SoC forward to ``now`` in the current mode."""
        elapsed = (now - self._last_update).total_seconds()
        self._soc_pct = advance_soc(
            self._soc_pct, self._mode, elapsed, self._solar_power_kw()
        )
        self._last_update = now

    def _solar_power_kw(self) -> float:
        """The solar power now in kW; 0 while the sensor is missing or unusable."""
        state = self.hass.states.get(SOLAR_POWER_ENTITY_ID)
        if state is None:
            return 0.0
        power = _parse_number(state.state)
        if power is None:
            return 0.0
        if state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfPower.KILO_WATT:
            return power
        return power / 1000

    async def async_set_mode(self, mode: str) -> None:
        """Entity service: use ``mode`` from now on.

        The time since the last update is simulated in the old mode first, so
        the SoC is right whenever the mode changes.
        """
        self._advance(dt_util.utcnow())
        _LOGGER.debug("Simulated battery mode %s -> %s", self._mode, mode)
        self._mode = mode
        self._notify_mode_listeners()
        self.async_write_ha_state()

    def _notify_mode_listeners(self) -> None:
        for listener in list(self._mode_listeners):
            listener()

    @property
    def native_value(self) -> int:
        """The SoC as a whole percent; ``_soc_pct`` keeps the fraction."""
        return round(self._soc_pct)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {ATTR_MODE: self._mode}


class SimulatedBatteryModeSensor(SensorEntity):
    """The mode in force in the simulated battery, as the state."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(MODES)

    def __init__(
        self,
        battery: SimulatedBatterySensor,
        device_info: DeviceInfo,
        remote_name: str,
    ) -> None:
        self._battery = battery
        self.entity_id = "sensor.simulated_battery_mode"
        self._attr_unique_id = "remote_sensors_simulatedbatterymode"
        self._attr_name = f"{remote_name} Simulated Battery Mode".strip()
        self._attr_device_info = device_info

    async def async_added_to_hass(self) -> None:
        # The battery restores the mode, so this sensor does not keep its own.
        self.async_on_remove(
            self._battery.async_add_mode_listener(self.async_write_ha_state)
        )

    @property
    def native_value(self) -> str:
        return self._battery.mode


def _parse_number(value: str) -> float | None:
    """Return a state as a float, or ``None`` if it is not a number."""
    if value in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None
