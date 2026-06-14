"""Battery state-of-charge sensor — proxies live data from the Balder HA instance."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo

from .coordinator import BalderCoordinator

_LOGGER = logging.getLogger(__name__)


class BatterySocSensor(SensorEntity):
    """Latest battery state-of-charge polled from the remote Balder HA (%)."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "%"
    _attr_should_poll = False
    _attr_exclude_from_recording = True

    def __init__(self, hass: HomeAssistant, coordinator: BalderCoordinator, device_info: DeviceInfo) -> None:
        description = SensorEntityDescription(key="batterysoc", translation_key="batterysoc")
        self.entity_description = description
        self.entity_id = f"{SENSOR_DOMAIN}.balder_{description.key}"
        self._attr_unique_id = f"balder_dev_sensors_{description.key}"
        self._attr_device_info = device_info
        self._coordinator = coordinator

    async def async_added_to_hass(self) -> None:
        self._coordinator.register_battery_soc_callback(self._on_update)

    async def async_will_remove_from_hass(self) -> None:
        self._coordinator.unregister_battery_soc_callback(self._on_update)

    @callback
    def _on_update(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        return self._coordinator.latest_battery_soc
