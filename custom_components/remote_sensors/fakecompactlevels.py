"""Fake Compact Levels diagnostic sensor for Remote Sensors.

This entity behaves like Energy Advisor's real compact-levels sensor (same
``minutes:level_length:passed:future`` string format and the same 15-minute
level length) but fills a random levels array instead of reading real price
data, and advances through it much faster than real time. This lets
LevelIndicatorClock be exercised through many level transitions quickly, to
spot bugs without waiting for real 15-minute price changes.
"""

from __future__ import annotations

import logging
import random
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)

# Each fake level represents this many minutes. Kept identical to the real
# Nord Pool quarter-hour price levels so the compact format and the clock's
# handling of it stay realistic.
FAKE_LEVEL_LENGTH_MINUTES = 15

# How often (in real seconds) the fake sensor advances to the next level.
# A real sensor only changes level every FAKE_LEVEL_LENGTH_MINUTES minutes;
# advancing every minute instead makes the clock cycle through levels ~15x
# faster, so LevelIndicatorClock bugs surface much quicker.
FAKE_UPDATE_SECONDS = 60

# Characters used to fill the random levels array.
FAKE_LEVEL_CHARS = "LMH"

_MINUTES_PER_DAY = 24 * 60
_FAKE_LEVELS_COUNT = _MINUTES_PER_DAY // FAKE_LEVEL_LENGTH_MINUTES
_PASSED_LEVELS_COUNT = 60 // FAKE_LEVEL_LENGTH_MINUTES
_FUTURE_LEVELS_COUNT = (12 * 60) // FAKE_LEVEL_LENGTH_MINUTES


def _circular_slice(levels: str, start: int, count: int) -> str:
    """Return ``count`` characters from ``levels`` starting at ``start``.

    Wraps around the end of the (circular) levels array instead of raising
    or truncating.
    """
    length = len(levels)
    if length == 0 or count <= 0:
        return ""
    start %= length
    end = start + count
    if end <= length:
        return levels[start:end]
    return levels[start:] + levels[: end - length]


class FakeCompactLevelsSensor(SensorEntity):
    """Diagnostic sensor emitting fake compact level data at high speed."""

    _attr_has_entity_name = False
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False
    _attr_exclude_from_recording = True

    def __init__(
        self,
        hass: HomeAssistant,
        device_info: DeviceInfo,
        remote_name: str,
    ) -> None:
        self.hass = hass
        self.entity_id = "sensor.remote_fakecompactlevels"
        self._attr_unique_id = "remote_sensors_fakecompactlevels"
        self._attr_name = f"{remote_name} Fake Compact Levels".strip()
        self._attr_device_info = device_info
        self._levels = "".join(
            random.choice(FAKE_LEVEL_CHARS) for _ in range(_FAKE_LEVELS_COUNT)
        )
        self._index = 0
        self._minutes: int | None = None
        self._compact: dict[str, str] | None = None
        self._cancel_timer = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._refresh()
        self._cancel_timer = async_track_time_interval(
            self.hass,
            self._handle_tick,
            timedelta(seconds=FAKE_UPDATE_SECONDS),
        )
        self.async_on_remove(self._cancel_timer)

    @callback
    def _handle_tick(self, _now: Any) -> None:
        self._index = (self._index + 1) % _FAKE_LEVELS_COUNT
        self._refresh()
        self.async_write_ha_state()

    def _refresh(self) -> None:
        self._minutes = (self._index * FAKE_LEVEL_LENGTH_MINUTES) % _MINUTES_PER_DAY
        passed_levels = _circular_slice(
            self._levels, self._index - _PASSED_LEVELS_COUNT, _PASSED_LEVELS_COUNT
        )
        future_levels = _circular_slice(
            self._levels, self._index, _FUTURE_LEVELS_COUNT
        )
        compact = (
            f"{self._minutes}:{FAKE_LEVEL_LENGTH_MINUTES}:"
            f"{passed_levels}:{future_levels}"
        )
        self._compact = {"compact": compact}
        _LOGGER.debug(
            "Fake minutes: %s Compact: %s", self._minutes, self._compact
        )

    @property
    def native_value(self) -> int | None:
        return self._minutes

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return self._compact or {}
