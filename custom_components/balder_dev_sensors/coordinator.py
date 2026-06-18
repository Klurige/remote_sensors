"""Polling coordinator for Balder Dev Sensors."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Callable

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .catalog import SensorSpec, load_remote_connection, load_sensor_specs

_LOGGER = logging.getLogger(__name__)

UNKNOWN_STATES = {"unknown", "unavailable"}


class BalderCoordinator:
    """Polls sensors from the remote Balder HA instance."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

        try:
            self._sensor_specs: tuple[SensorSpec, ...] = load_sensor_specs()
        except ValueError as err:
            _LOGGER.error("Invalid sensor configuration in dev_config.py: %s", err)
            self._sensor_specs = ()

        self._specs_by_key = {spec.key: spec for spec in self._sensor_specs}
        self._states: dict[str, float | str | None] = {
            spec.key: None for spec in self._sensor_specs
        }
        self._attributes: dict[str, dict[str, Any]] = {
            spec.key: {} for spec in self._sensor_specs
        }
        self._callbacks: dict[str, list[Callable[[], None]]] = {
            spec.key: [] for spec in self._sensor_specs
        }

        self._ha_url, self._ha_token = load_remote_connection()

        self._session: aiohttp.ClientSession | None = None
        self._cancel_handles: list[Callable[[], None]] = []

    @property
    def sensor_specs(self) -> tuple[SensorSpec, ...]:
        """Return the configured sensor specifications."""
        return self._sensor_specs

    async def async_setup(self) -> None:
        if not self._sensor_specs:
            _LOGGER.warning("No sensors configured in dev_config.py")
            return
        if not (self._ha_url and self._ha_token):
            _LOGGER.warning("dev_secrets.py missing or incomplete — no remote polling")
            return
        self._session = aiohttp.ClientSession()
        for spec in self._sensor_specs:
            await self._poll_sensor(spec.key)
        self._cancel_handles = [
            async_track_time_interval(
                self.hass,
                self._build_poll_handler(spec.key),
                timedelta(seconds=spec.poll_seconds),
            )
            for spec in self._sensor_specs
        ]
        _LOGGER.info("BalderCoordinator: polling started")

    async def async_shutdown(self) -> None:
        for cancel in self._cancel_handles:
            cancel()
        self._cancel_handles.clear()
        if self._session:
            await self._session.close()
            self._session = None

    async def _poll_sensor(self, sensor_key: str) -> None:
        spec = self._specs_by_key.get(sensor_key)
        if spec is None:
            return

        data = await self._fetch_state(spec.entity_id)
        if data is None:
            return

        value = self._parse_value(spec, data.get("state"))
        attributes = data.get("attributes", {}) if spec.include_attributes else {}

        if self._states.get(sensor_key) == value and self._attributes.get(sensor_key) == attributes:
            return

        self._states[sensor_key] = value
        self._attributes[sensor_key] = attributes
        self._notify(sensor_key)

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    async def _fetch_state(self, entity_id: str) -> dict | None:
        if not entity_id or not self._session:
            return None
        url = f"{self._ha_url}/api/states/{entity_id}"
        headers = {"Authorization": f"Bearer {self._ha_token}"}
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

    def _parse_value(self, spec: SensorSpec, raw_state: Any) -> float | str | None:
        if raw_state is None:
            return None
        state = str(raw_state)
        if state in UNKNOWN_STATES:
            return None
        if spec.value_type == "string":
            return state
        try:
            return float(state)
        except (TypeError, ValueError):
            _LOGGER.debug("Fetch %s returned non-numeric state %r", spec.entity_id, state)
            return None

    def get_state(self, sensor_key: str) -> float | str | None:
        """Return the latest known state for a configured sensor."""
        return self._states.get(sensor_key)

    def get_attributes(self, sensor_key: str) -> dict[str, Any]:
        """Return the latest attributes for a configured sensor."""
        return dict(self._attributes.get(sensor_key, {}))

    def register_callback(self, sensor_key: str, callback: Callable[[], None]) -> None:
        """Register a listener for a sensor key."""
        callbacks = self._callbacks.get(sensor_key)
        if callbacks is not None:
            callbacks.append(callback)

    def unregister_callback(self, sensor_key: str, callback: Callable[[], None]) -> None:
        """Unregister a listener for a sensor key."""
        callbacks = self._callbacks.get(sensor_key)
        if callbacks is not None:
            self._safe_remove(callbacks, callback)

    def _notify(self, sensor_key: str) -> None:
        for cb in self._callbacks.get(sensor_key, []):
            cb()

    def _build_poll_handler(self, sensor_key: str) -> Callable[[Any], Any]:
        async def _poll(_now) -> None:
            await self._poll_sensor(sensor_key)

        return _poll

    @staticmethod
    def _safe_remove(lst: list[Any], item: Any) -> None:
        try:
            lst.remove(item)
        except ValueError:
            pass
