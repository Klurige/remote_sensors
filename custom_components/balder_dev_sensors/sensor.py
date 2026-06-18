"""Sensor platform for Balder Dev Sensors."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .catalog import SensorSpec
from .coordinator import BalderCoordinator

DOMAIN = "balder_dev_sensors"

_LOGGER = logging.getLogger(__name__)


class BalderRemoteSensor(SensorEntity):
    """Generic remote sensor entity backed by the Balder coordinator."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: BalderCoordinator,
        device_info: DeviceInfo,
        spec: SensorSpec,
    ) -> None:
        self._coordinator = coordinator
        self._spec = spec

        self.entity_id = f"{SENSOR_DOMAIN}.balder_{spec.key}"
        self._attr_unique_id = f"balder_dev_sensors_{spec.key}"
        self._attr_device_info = device_info
        self._attr_name = spec.name
        self._attr_exclude_from_recording = spec.exclude_from_recording

        if spec.native_unit_of_measurement is not None:
            self._attr_native_unit_of_measurement = spec.native_unit_of_measurement
        if spec.device_class is not None:
            self._attr_device_class = SensorDeviceClass(spec.device_class)
        if spec.state_class is not None:
            self._attr_state_class = SensorStateClass(spec.state_class)
        if spec.icon is not None:
            self._attr_icon = spec.icon

    async def async_added_to_hass(self) -> None:
        self._coordinator.register_callback(self._spec.key, self._on_update)

    async def async_will_remove_from_hass(self) -> None:
        self._coordinator.unregister_callback(self._spec.key, self._on_update)

    @callback
    def _on_update(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | str | None:
        return self._coordinator.get_state(self._spec.key)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self._spec.include_attributes:
            return None
        return self._coordinator.get_attributes(self._spec.key)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BalderCoordinator = data["coordinator"]
    device_info: DeviceInfo = data["device_info"]

    async_add_entities(
        [
            BalderRemoteSensor(coordinator, device_info, spec)
            for spec in coordinator.sensor_specs
        ],
        True,
    )
