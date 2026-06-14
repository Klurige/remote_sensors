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

# Remote entity IDs — hardcoded, not in dev_config (they are stable Balder entity names)
_BATTERY_MODE_ENTITY = "sensor.batterilage"
_GRID_EXPORT_ENTITY = "sensor.elmatare_momentary_active_export"
_BATTERY_CHARGE_POWER_ENTITY = "sensor.batteriladdeffekt"
_BATTERY_SOC_ENTITY = "sensor.batteries_state_of_capacity"

try:
    from . import dev_config as _cfg  # type: ignore[import]
    _HA_URL = getattr(_cfg, "HA_URL", "")
    _HA_TOKEN = getattr(_cfg, "HA_TOKEN", "")
    _POWER_ENTITY = getattr(_cfg, "DEV_DEFAULTS", {}).get("power_entity", "")
except ImportError:
    pass

POLL_INTERVAL_FAST = timedelta(seconds=30)   # power, grid export, battery charge power
POLL_INTERVAL_SLOW = timedelta(seconds=60)   # battery SoC
POLL_INTERVAL_VERY_SLOW = timedelta(seconds=300)  # battery mode (string state)


class BalderCoordinator:
    """Polls sensors from the remote Balder HA instance."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

        self.latest_inverter_power_w: float | None = None
        self.latest_battery_mode: str | None = None
        self.latest_battery_mode_attributes: dict = {}
        self.latest_grid_export_w: float | None = None
        self.latest_battery_charge_power_w: float | None = None
        self.latest_battery_soc: float | None = None

        self._inverter_power_callbacks: list[Callable] = []
        self._battery_mode_callbacks: list[Callable] = []
        self._grid_export_callbacks: list[Callable] = []
        self._battery_charge_power_callbacks: list[Callable] = []
        self._battery_soc_callbacks: list[Callable] = []

        self._session: aiohttp.ClientSession | None = None
        self._cancel_handles: list[Callable] = []

    async def async_setup(self) -> None:
        if not (_HA_URL and _HA_TOKEN):
            _LOGGER.warning("dev_config.py missing or incomplete — no remote polling")
            return
        self._session = aiohttp.ClientSession()
        # Initial polls
        await self._poll_power(None)
        await self._poll_battery_mode(None)
        await self._poll_grid_export(None)
        await self._poll_battery_charge_power(None)
        await self._poll_battery_soc(None)
        # Scheduled polls
        self._cancel_handles = [
            async_track_time_interval(self.hass, self._poll_power, POLL_INTERVAL_FAST),
            async_track_time_interval(self.hass, self._poll_grid_export, POLL_INTERVAL_FAST),
            async_track_time_interval(self.hass, self._poll_battery_charge_power, POLL_INTERVAL_FAST),
            async_track_time_interval(self.hass, self._poll_battery_soc, POLL_INTERVAL_SLOW),
            async_track_time_interval(self.hass, self._poll_battery_mode, POLL_INTERVAL_VERY_SLOW),
        ]
        _LOGGER.info("BalderCoordinator: polling started")

    async def async_shutdown(self) -> None:
        for cancel in self._cancel_handles:
            cancel()
        self._cancel_handles.clear()
        if self._session:
            await self._session.close()
            self._session = None

    # ── Poll methods ──────────────────────────────────────────────────────────

    async def _poll_power(self, _now) -> None:
        if _POWER_ENTITY:
            val = await self._fetch_float(_POWER_ENTITY)
            if val is not None:
                self.latest_inverter_power_w = val
                self._notify(self._inverter_power_callbacks)

    async def _poll_battery_mode(self, _now) -> None:
        data = await self._fetch_state(_BATTERY_MODE_ENTITY)
        if data is not None:
            self.latest_battery_mode = data.get("state")
            self.latest_battery_mode_attributes = data.get("attributes", {})
            self._notify(self._battery_mode_callbacks)

    async def _poll_grid_export(self, _now) -> None:
        val = await self._fetch_float(_GRID_EXPORT_ENTITY)
        if val is not None:
            self.latest_grid_export_w = val
            self._notify(self._grid_export_callbacks)

    async def _poll_battery_charge_power(self, _now) -> None:
        val = await self._fetch_float(_BATTERY_CHARGE_POWER_ENTITY)
        if val is not None:
            self.latest_battery_charge_power_w = val
            self._notify(self._battery_charge_power_callbacks)

    async def _poll_battery_soc(self, _now) -> None:
        val = await self._fetch_float(_BATTERY_SOC_ENTITY)
        if val is not None:
            self.latest_battery_soc = val
            self._notify(self._battery_soc_callbacks)

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    async def _fetch_state(self, entity_id: str) -> dict | None:
        url = f"{_HA_URL}/api/states/{entity_id}"
        headers = {"Authorization": f"Bearer {_HA_TOKEN}"}
        try:
            async with self._session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                _LOGGER.debug("Fetch %s: HTTP %d", entity_id, resp.status)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Fetch %s failed: %s", entity_id, err)
        return None

    async def _fetch_float(self, entity_id: str) -> float | None:
        data = await self._fetch_state(entity_id)
        if data is None:
            return None
        state = data.get("state", "")
        if state in ("unknown", "unavailable"):
            return None
        try:
            return float(state)
        except ValueError:
            return None

    @staticmethod
    def _notify(callbacks: list[Callable]) -> None:
        for cb in callbacks:
            cb()

    # ── Callback registration ─────────────────────────────────────────────────

    def register_inverter_power_callback(self, cb: Callable) -> None:
        self._inverter_power_callbacks.append(cb)

    def unregister_inverter_power_callback(self, cb: Callable) -> None:
        self._inverter_power_callbacks.discard(cb) if hasattr(self._inverter_power_callbacks, 'discard') else self._inverter_power_callbacks.remove(cb) if cb in self._inverter_power_callbacks else None

    def register_battery_mode_callback(self, cb: Callable) -> None:
        self._battery_mode_callbacks.append(cb)

    def unregister_battery_mode_callback(self, cb: Callable) -> None:
        self._safe_remove(self._battery_mode_callbacks, cb)

    def register_grid_export_callback(self, cb: Callable) -> None:
        self._grid_export_callbacks.append(cb)

    def unregister_grid_export_callback(self, cb: Callable) -> None:
        self._safe_remove(self._grid_export_callbacks, cb)

    def register_battery_charge_power_callback(self, cb: Callable) -> None:
        self._battery_charge_power_callbacks.append(cb)

    def unregister_battery_charge_power_callback(self, cb: Callable) -> None:
        self._safe_remove(self._battery_charge_power_callbacks, cb)

    def register_battery_soc_callback(self, cb: Callable) -> None:
        self._battery_soc_callbacks.append(cb)

    def unregister_battery_soc_callback(self, cb: Callable) -> None:
        self._safe_remove(self._battery_soc_callbacks, cb)

    @staticmethod
    def _safe_remove(lst: list, item) -> None:
        try:
            lst.remove(item)
        except ValueError:
            pass
