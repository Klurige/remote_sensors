"""Sensor platform for Balder Dev Sensors."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    async_add_entities([CounterSensor(hass)], True)


class CounterSensor(SensorEntity):
    """A sensor that increments its value by 1 every second."""

    _attr_name = "Balder Counter"
    _attr_unique_id = "balder_dev_sensors_counter"
    _attr_native_unit_of_measurement = "count"
    _attr_should_poll = False
    _attr_exclude_from_recording = True

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._count: int = 0
        self._cancel = None

    async def async_added_to_hass(self) -> None:
        self._cancel = async_track_time_interval(
            self._hass, self._increment, timedelta(seconds=1)
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._cancel:
            self._cancel()

    async def _increment(self, _now=None) -> None:
        self._count += 1
        self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        return self._count
