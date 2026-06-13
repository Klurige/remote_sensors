"""Balder Dev Sensors integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .coordinator import BalderCoordinator

DOMAIN = "balder_dev_sensors"
PLATFORMS = ["sensor"]


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, entry.entry_id)},
        name="Balder Dev Sensors",
        manufacturer="Klurige",
        model="Remote sensor proxy",
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Balder Dev Sensors from a config entry."""
    coordinator = BalderCoordinator(hass)
    await coordinator.async_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "device_info": _device_info(entry),
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: BalderCoordinator = hass.data[DOMAIN].pop(entry.entry_id)["coordinator"]
    await coordinator.async_shutdown()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
