"""Sensor platform for Remote Sensors."""

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
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import voluptuous as vol

from .catalog import SensorSpec
from .coordinator import RemoteCoordinator
from .fakecompactlevels import FakeCompactLevelsSensor
from .simulatedbattery import (
    ATTR_MODE,
    MODES,
    SERVICE_SET_MODE,
    SimulatedBatteryModeSensor,
    SimulatedBatterySensor,
)

DOMAIN = "remote_sensors"

_LOGGER = logging.getLogger(__name__)


class RemoteSensorEntity(SensorEntity):
    """Generic remote sensor entity backed by the coordinator."""

    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: RemoteCoordinator,
        device_info: DeviceInfo,
        remote_name: str,
        spec: SensorSpec,
    ) -> None:
        self._coordinator = coordinator
        self._spec = spec

        self.entity_id = f"{SENSOR_DOMAIN}.remote_{spec.key}"
        self._attr_unique_id = f"remote_sensors_{spec.key}"
        self._attr_device_info = device_info
        self._attr_name = f"{remote_name} {spec.name}".strip()
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
    coordinator: RemoteCoordinator = data["coordinator"]
    device_info: DeviceInfo = data["device_info"]
    remote_name: str = data.get("remote_name", "Remote")

    entities: list[SensorEntity] = [
        RemoteSensorEntity(coordinator, device_info, remote_name, spec)
        for spec in coordinator.sensor_specs
    ]
    entities.append(FakeCompactLevelsSensor(hass, device_info, remote_name))
    battery = SimulatedBatterySensor(hass, device_info, remote_name)
    entities.append(battery)
    entities.append(SimulatedBatteryModeSensor(battery, device_info, remote_name))

    async_add_entities(entities, True)

    entity_platform.async_get_current_platform().async_register_entity_service(
        SERVICE_SET_MODE,
        {vol.Required(ATTR_MODE): vol.In(MODES)},
        "async_set_mode",
    )
