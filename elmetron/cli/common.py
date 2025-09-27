"""Shared CLI helpers for operator tooling."""
from __future__ import annotations

from argparse import Namespace
from typing import Optional

from ..config import DeviceConfig
from ..protocols.registry import (
    CommandDefinition,
    ProtocolProfile,
    ProtocolRegistry,
    DEFAULT_PROFILE_NAME,
)


def apply_device_overrides(device: DeviceConfig, args: Namespace) -> None:
    """Apply command-line overrides stored in *args* to *device*."""

    if getattr(args, "device_index", None) is not None:
        device.index = args.device_index
    if getattr(args, "device_serial", None):
        device.serial = args.device_serial
    if getattr(args, "profile", None):
        device.profile = args.profile
    if getattr(args, "no_profile_defaults", False):
        device.use_profile_defaults = False
    if getattr(args, "baud", None) is not None:
        device.baud = args.baud
    if getattr(args, "data_bits", None) is not None:
        device.data_bits = args.data_bits
    if getattr(args, "stop_bits", None) is not None:
        device.stop_bits = float(args.stop_bits)
    if getattr(args, "parity", None):
        device.parity = args.parity
    if getattr(args, "poll_hex", None):
        device.poll_hex = args.poll_hex
    if getattr(args, "poll_interval", None) is not None:
        device.poll_interval_s = float(args.poll_interval)
    if getattr(args, "latency", None) is not None:
        device.latency_timer_ms = int(args.latency)
    timeouts = getattr(args, "timeouts", None)
    if timeouts:
        read_ms, write_ms = timeouts
        device.read_timeout_ms = int(read_ms)
        device.write_timeout_ms = int(write_ms)


def resolve_profile(
    registry: ProtocolRegistry,
    device: DeviceConfig,
    *,
    default_profile: Optional[str] = None,
) -> ProtocolProfile:
    """Resolve the protocol profile requested by *device* and apply it."""

    if not device.profile and default_profile:
        device.profile = default_profile
    fallback = default_profile or DEFAULT_PROFILE_NAME
    try:
        return registry.apply_to_device(device)
    except KeyError as exc:
        name = device.profile or fallback
        available = ", ".join(sorted(registry._profiles))  # type: ignore[attr-defined]
        message = f"Profile '{name}' not found in registry"
        if available:
            message = f"{message}. Available profiles: {available}"
        raise ValueError(message) from exc


def find_command(profile: ProtocolProfile, command_name: str) -> CommandDefinition:
    """Locate a command named *command_name* within *profile*."""

    key = command_name.strip()
    if not key:
        raise ValueError("Command name must not be empty")
    try:
        return profile.commands[key]
    except KeyError as exc:
        available = ", ".join(sorted(profile.commands)) or "<none>"
        raise ValueError(
            f"Command '{key}' not defined for profile '{profile.name}'. Available: {available}"
        ) from exc
