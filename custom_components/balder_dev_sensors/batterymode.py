"""Battery mode sensor — proxies live data from the Balder HA instance."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo

from .coordinator import BalderCoordinator

_LOGGER = logging.getLogger(__name__)


class BatteryModeSensor(SensorEntity):
    """Latest battery mode state polled from the remote Balder HA (e.g. 'Charge', 'Idle')."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_exclude_from_recording = True

    def __init__(self, hass: HomeAssistant, coordinator: BalderCoordinator, device_info: DeviceInfo) -> None:
        description = SensorEntityDescription(key="batterymode", translation_key="batterymode")
        self.entity_description = description
        self.entity_id = f"{SENSOR_DOMAIN}.balder_{description.key}"
        self._attr_unique_id = f"balder_dev_sensors_{description.key}"
        self._attr_device_info = device_info
        self._coordinator = coordinator

    async def async_added_to_hass(self) -> None:
        self._coordinator.register_battery_mode_callback(self._on_update)

    async def async_will_remove_from_hass(self) -> None:
        self._coordinator.unregister_battery_mode_callback(self._on_update)

    @callback
    def _on_update(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        return self._coordinator.latest_battery_mode

    @property
    def extra_state_attributes(self) -> dict:
        return self._coordinator.latest_battery_mode_attributes
