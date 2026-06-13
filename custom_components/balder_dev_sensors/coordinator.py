"""Polling coordinator for Balder Dev Sensors.

Reads HA_URL, HA_TOKEN, and sensor entity IDs from dev_config.py (gitignored).
Polls each configured remote sensor on a fixed interval and notifies
registered sensor entities via callbacks.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Callable

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)

_HA_URL: str = ""
_HA_TOKEN: str = ""
_POWER_ENTITY: str = ""

try:
    from . import dev_config as _cfg  # type: ignore[import]
    _HA_URL = getattr(_cfg, "HA_URL", "")
    _HA_TOKEN = getattr(_cfg, "HA_TOKEN", "")
    _POWER_ENTITY = getattr(_cfg, "DEV_DEFAULTS", {}).get("power_entity", "")
except ImportError:
    pass

POLL_INTERVAL = timedelta(seconds=30)


class BalderCoordinator:
    """Polls sensors from the remote Balder HA instance."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.latest_inverter_power_w: float | None = None

        self._inverter_power_callbacks: list[Callable] = []
        self._session: aiohttp.ClientSession | None = None
        self._cancel = None

    async def async_setup(self) -> None:
        if not (_HA_URL and _HA_TOKEN):
            _LOGGER.warning("dev_config.py missing or incomplete — no remote polling")
            return
        self._session = aiohttp.ClientSession()
        await self._poll(None)
        self._cancel = async_track_time_interval(self.hass, self._poll, POLL_INTERVAL)
        _LOGGER.info("BalderCoordinator polling every %s", POLL_INTERVAL)

    async def async_shutdown(self) -> None:
        if self._cancel:
            self._cancel()
            self._cancel = None
        if self._session:
            await self._session.close()
            self._session = None

    async def _poll(self, _now) -> None:
        if _POWER_ENTITY:
            val = await self._fetch(_POWER_ENTITY)
            if val is not None:
                self.latest_inverter_power_w = val
                for cb in self._inverter_power_callbacks:
                    cb()

    async def _fetch(self, entity_id: str) -> float | None:
        url = f"{_HA_URL}/api/states/{entity_id}"
        headers = {"Authorization": f"Bearer {_HA_TOKEN}"}
        try:
            async with self._session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    state = data.get("state", "")
                    if state not in ("unknown", "unavailable"):
                        return float(state)
                else:
                    _LOGGER.debug("Fetch %s: HTTP %d", entity_id, resp.status)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Fetch %s failed: %s", entity_id, err)
        return None

    def register_inverter_power_callback(self, cb: Callable) -> None:
        self._inverter_power_callbacks.append(cb)

    def unregister_inverter_power_callback(self, cb: Callable) -> None:
        try:
            self._inverter_power_callbacks.remove(cb)
        except ValueError:
            pass
