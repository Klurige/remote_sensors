"""Remote Sensors integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .coordinator import RemoteCoordinator

DOMAIN = "remote_sensors"
CONF_REMOTE_NAME = "remote_name"
DEFAULT_REMOTE_NAME = "Remote"
PLATFORMS = ["sensor"]


def _device_info(entry: ConfigEntry, remote_name: str) -> DeviceInfo:
    return DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, entry.entry_id)},
        name=remote_name,
        manufacturer="",
        model="Remote sensor proxy",
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Remote Sensors from a config entry."""
    remote_name = str(
        entry.options.get(CONF_REMOTE_NAME, entry.data.get(CONF_REMOTE_NAME, DEFAULT_REMOTE_NAME))
    ).strip() or DEFAULT_REMOTE_NAME
    coordinator = RemoteCoordinator(hass)
    await coordinator.async_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "device_info": _device_info(entry, remote_name),
        "remote_name": remote_name,
    }
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry_on_update))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: RemoteCoordinator = hass.data[DOMAIN].pop(entry.entry_id)["coordinator"]
    await coordinator.async_shutdown()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry_on_update(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)

