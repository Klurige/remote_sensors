"""Balder Dev Sensors integration."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.discovery import async_load_platform

DOMAIN = "balder_dev_sensors"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Balder Dev Sensors integration."""
    hass.async_create_task(
        async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )
    return True
