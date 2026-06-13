"""Sensor platform for Balder Dev Sensors."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import BalderCoordinator
from .inverterpower import InverterPowerSensor

DOMAIN = "balder_dev_sensors"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BalderCoordinator = data["coordinator"]
    device_info: DeviceInfo = data["device_info"]
    async_add_entities([
        InverterPowerSensor(hass, coordinator, device_info),
    ], True)
