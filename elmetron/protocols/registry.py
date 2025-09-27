"""Protocol registry utilities for Elmetron devices."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import DEFAULT_POLL_HEX, DeviceConfig

DEFAULT_PROFILE_NAME = "cx505"


@dataclass(slots=True)
class CommandDefinition:
    """Describes a single command/calibration sequence."""

    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    write_hex: Optional[str] = None
    write_ascii: Optional[str] = None
    post_delay_s: float = 0.0
    read_duration_s: Optional[float] = None
    expect_hex: Optional[str] = None
    default_max_retries: Optional[int] = None
    default_retry_backoff_s: Optional[float] = None
    calibration_label: Optional[str] = None


@dataclass(slots=True)
class ProtocolProfile:
    """Represents a single meter protocol definition."""

    name: str
    description: Optional[str] = None
    poll_hex: Optional[str] = None
    poll_interval_s: Optional[float] = None
    baud: Optional[int] = None
    data_bits: Optional[int] = None
    stop_bits: Optional[float] = None
    parity: Optional[str] = None
    latency_timer_ms: Optional[int] = None
    read_timeout_ms: Optional[int] = None
    write_timeout_ms: Optional[int] = None
    chunk_size: Optional[int] = None
    transport: Optional[str] = None
    handshake: Optional[str] = None
    ble_address: Optional[str] = None
    ble_read_characteristic: Optional[str] = None
    ble_write_characteristic: Optional[str] = None
    ble_notify_characteristic: Optional[str] = None
    commands: Dict[str, CommandDefinition] = field(default_factory=dict)


class ProtocolRegistry:
    """Container that maps profile names to protocol descriptions."""

    def __init__(self, profiles: Dict[str, ProtocolProfile]):
        self._profiles = profiles

    def get(self, name: str) -> Optional[ProtocolProfile]:
        return self._profiles.get(name.lower())

    def apply_to_device(self, device: DeviceConfig) -> ProtocolProfile:
        """Apply the profile referenced by *device* to the device config."""

        requested = (device.profile or DEFAULT_PROFILE_NAME).lower()
        profile = self.get(requested)
        if profile is None and requested != DEFAULT_PROFILE_NAME:
            profile = self.get(DEFAULT_PROFILE_NAME)
        if profile is None:
            raise KeyError(f"Protocol profile '{requested}' not found")
        device.apply_profile(profile)
        # Normalise the device profile name so downstream consumers see the resolved profile.
        device.profile = profile.name
        return profile

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ProtocolRegistry":
        profiles: Dict[str, ProtocolProfile] = {}
        for name, data in payload.items():
            if not isinstance(data, dict):
                continue
            command_defs: Dict[str, CommandDefinition] = {}
            commands_payload = data.get("commands")
            if isinstance(commands_payload, dict):
                for command_name, command_fields in commands_payload.items():
                    if not isinstance(command_fields, dict):
                        continue
                    post_delay = command_fields.get("post_delay_s", 0.0)
                    try:
                        post_delay_value = float(post_delay)
                    except (TypeError, ValueError):
                        post_delay_value = 0.0
                    read_duration = command_fields.get("read_duration_s")
                    if read_duration is not None:
                        try:
                            read_duration_value = float(read_duration)
                        except (TypeError, ValueError):
                            read_duration_value = None
                    else:
                        read_duration_value = None
                    command_defs[command_name] = CommandDefinition(
                    name=command_name,
                    description=command_fields.get("description"),
                    category=command_fields.get("category"),
                    write_hex=command_fields.get("write_hex"),
                    write_ascii=command_fields.get("write_ascii"),
                    post_delay_s=post_delay_value,
                    read_duration_s=read_duration_value,
                    expect_hex=command_fields.get("expect_hex"),
                    default_max_retries=command_fields.get("default_max_retries"),
                    default_retry_backoff_s=command_fields.get("default_retry_backoff_s"),
                    calibration_label=command_fields.get("calibration_label"),
                )
            profile = ProtocolProfile(
                name=name,
                description=data.get("description"),
                poll_hex=data.get("poll_hex"),
                poll_interval_s=data.get("poll_interval_s"),
                baud=data.get("baud"),
                data_bits=data.get("data_bits"),
                stop_bits=data.get("stop_bits"),
                parity=data.get("parity"),
                latency_timer_ms=data.get("latency_timer_ms"),
                read_timeout_ms=data.get("read_timeout_ms"),
                write_timeout_ms=data.get("write_timeout_ms"),
                chunk_size=data.get("chunk_size"),
                transport=data.get("transport"),
                handshake=data.get("handshake"),
                commands=command_defs,
            )
            profiles[name.lower()] = profile
        return cls(profiles)


DEFAULT_PROFILES: Dict[str, Dict[str, Any]] = {
    "cx505": {
        "description": "Default CX-505 handshake and transport parameters.",
        "transport": "ftdi",
        "poll_hex": DEFAULT_POLL_HEX,
        "poll_interval_s": 1.0,
        "baud": 115200,
        "data_bits": 8,
        "stop_bits": 2.0,
        "parity": "E",
        "latency_timer_ms": 2,
        "read_timeout_ms": 500,
        "write_timeout_ms": 500,
        "chunk_size": 256,
        "commands": {
            "calibrate_ph7": {
                "description": "Request pH 7 calibration (CX-505).",
                "category": "calibration",
                "write_hex": "02 43 41 4C 37 03",
                "post_delay_s": 0.5,
                "read_duration_s": 2.0,
                "expect_hex": "01",
                "default_max_retries": 2,
                "default_retry_backoff_s": 1.5,
                "calibration_label": "ph7_buffer"
            }
        },
    },
    "cx705": {
        "description": "CX-705 dissolved oxygen meter (FTDI).",
        "transport": "ftdi",
        "poll_hex": "01 23 31 23 31 23 31 23 03",
        "poll_interval_s": 2.0,
        "baud": 9600,
        "data_bits": 8,
        "stop_bits": 1.0,
        "parity": "N",
        "latency_timer_ms": 4,
        "read_timeout_ms": 750,
        "write_timeout_ms": 750,
        "chunk_size": 128,
        "commands": {
            "start_logging": {
                "description": "Begin streaming dissolved oxygen measurements.",
                "write_ascii": "START\r\n",
                "post_delay_s": 0.2,
                "read_duration_s": 3.0
            }
        },
    },
    "ph_ble_handheld": {
        "description": "Bluetooth LE bridge for handheld pH/ORP meters.",
        "transport": "ble",
        "handshake": "connect",
        "poll_interval_s": 5.0,
        "commands": {
            "sync_time": {
                "description": "Request BLE bridge to synchronise its clock.",
                "write_ascii": "SYNC\n",
                "read_duration_s": 1.0
            }
        },
    },
}





def load_registry(path: Optional[Path]) -> ProtocolRegistry:
    """Load protocol profiles from *path* or use built-in defaults."""

    if path is None:
        return ProtocolRegistry.from_dict(DEFAULT_PROFILES)
    resolved = path.expanduser()
    if not resolved.exists():
        raise FileNotFoundError(f"Protocol registry '{resolved}' not found")
    suffix = resolved.suffix.lower()
    if suffix in {".toml", ".tml"}:
        payload = _load_toml(resolved)
    elif suffix in {".json", ".jsn"}:
        payload = _load_json(resolved)
    elif suffix in {".yaml", ".yml"}:
        payload = _load_yaml(resolved)
    else:
        raise ValueError(f"Unsupported protocol registry format: {resolved.suffix}")
    profiles = payload.get("profiles") if isinstance(payload, dict) else None
    if not isinstance(profiles, dict):
        raise ValueError("Protocol registry must contain a 'profiles' mapping")
    return ProtocolRegistry.from_dict(profiles)


def _load_json(path: Path) -> Dict[str, Any]:
    import json

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_toml(path: Path) -> Dict[str, Any]:
    try:
        import tomllib
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime guard
        raise RuntimeError("tomllib is required to parse TOML protocol registries") from exc
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("PyYAML is required to parse YAML protocol registries") from exc
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}




