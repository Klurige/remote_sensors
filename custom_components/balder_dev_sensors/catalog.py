"""Configuration loading helpers for Balder Dev Sensors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping

SensorValueType = Literal["float", "string"]
_ALLOWED_VALUE_TYPES = {"float", "string"}


@dataclass(frozen=True, slots=True)
class SensorSpec:
    """Runtime description of a configured proxy sensor."""

    key: str
    name: str
    entity_id: str
    poll_seconds: int
    value_type: SensorValueType
    native_unit_of_measurement: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    include_attributes: bool = False
    exclude_from_recording: bool = True
    icon: str | None = None


def load_sensor_specs() -> tuple[SensorSpec, ...]:
    """Load the tracked sensor catalog from ``dev_config.py``."""
    try:
        from . import dev_config as _cfg  # type: ignore[import]
    except ImportError:
        return ()

    raw_sensors = getattr(_cfg, "SENSORS", {})
    if not isinstance(raw_sensors, Mapping):
        raise ValueError("SENSORS must be a mapping of sensor keys to configuration")

    specs: list[SensorSpec] = []
    for key, raw_sensor in raw_sensors.items():
        if not isinstance(key, str) or not key:
            raise ValueError("Each sensor key must be a non-empty string")
        if not isinstance(raw_sensor, Mapping):
            raise ValueError(f"Sensor '{key}' must be configured as a mapping")

        name = _require_string(raw_sensor, key, "name")
        entity_id = _require_string(raw_sensor, key, "entity_id")
        poll_seconds = _require_positive_int(raw_sensor, key, "poll_seconds")
        value_type = _require_value_type(raw_sensor, key, "value_type")

        specs.append(
            SensorSpec(
                key=key,
                name=name,
                entity_id=entity_id,
                poll_seconds=poll_seconds,
                value_type=value_type,
                native_unit_of_measurement=_optional_string(
                    raw_sensor, key, "native_unit_of_measurement"
                ),
                device_class=_optional_string(raw_sensor, key, "device_class"),
                state_class=_optional_string(raw_sensor, key, "state_class"),
                include_attributes=_optional_bool(raw_sensor, "include_attributes", False),
                exclude_from_recording=_optional_bool(
                    raw_sensor, "exclude_from_recording", True
                ),
                icon=_optional_string(raw_sensor, key, "icon"),
            )
        )

    return tuple(specs)


def load_remote_connection() -> tuple[str, str]:
    """Load the local-only Home Assistant URL and token."""
    try:
        from . import dev_secrets as _secrets  # type: ignore[import]
    except ImportError:
        return "", ""

    ha_url = getattr(_secrets, "HA_URL", "")
    ha_token = getattr(_secrets, "HA_TOKEN", "")
    return str(ha_url), str(ha_token)


def _require_string(raw_sensor: Mapping[str, Any], key: str, field: str) -> str:
    value = raw_sensor.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Sensor '{key}' field '{field}' must be a non-empty string")
    return value


def _optional_string(raw_sensor: Mapping[str, Any], key: str, field: str) -> str | None:
    value = raw_sensor.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"Sensor '{key}' field '{field}' must be a non-empty string")
    return value


def _require_positive_int(raw_sensor: Mapping[str, Any], key: str, field: str) -> int:
    value = raw_sensor.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"Sensor '{key}' field '{field}' must be a positive integer")
    return value


def _require_value_type(
    raw_sensor: Mapping[str, Any], key: str, field: str
) -> SensorValueType:
    value = _require_string(raw_sensor, key, field)
    if value not in _ALLOWED_VALUE_TYPES:
        allowed = ", ".join(sorted(_ALLOWED_VALUE_TYPES))
        raise ValueError(
            f"Sensor '{key}' field '{field}' must be one of: {allowed}"
        )
    return value


def _optional_bool(raw_sensor: Mapping[str, Any], field: str, default: bool) -> bool:
    value = raw_sensor.get(field, default)
    if not isinstance(value, bool):
        raise ValueError(f"Field '{field}' must be a boolean when provided")
    return value

