"""Command execution helpers."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional

import cx505_d2xx

from ..config import DeviceConfig
from ..hardware import DeviceInterface, create_interface
from ..protocols import CommandDefinition


@dataclass(slots=True)
class CommandResult:
    name: str
    written_bytes: int
    frames: List[bytes]
    bytes_read: int
    duration_s: float
    expected_hex: Optional[str] = None
    matched_expectation: Optional[bool] = None

    @property
    def frames_as_hex(self) -> List[str]:
        return [frame.hex(" ") for frame in self.frames]


def _prepare_payloads(definition: CommandDefinition) -> List[bytes]:
    payloads: List[bytes] = []
    if definition.write_hex:
        payloads.extend(cx505_d2xx._prepare_payloads(None, definition.write_hex))  # type: ignore[attr-defined]
    if definition.write_ascii:
        payloads.append(definition.write_ascii.encode("ascii"))
    if not payloads:
        raise ValueError(f"Command '{definition.name}' does not define write_hex or write_ascii payloads")
    return payloads


def _decode_expectation(expect_hex: Optional[str]) -> Optional[bytes]:
    if not expect_hex:
        return None
    parts = [part for part in expect_hex.replace(',', ' ').split() if part]
    try:
        return bytes(int(part, 16) for part in parts)
    except ValueError:
        return None


def execute_command(
    interface: DeviceInterface,
    definition: CommandDefinition,
    read_duration_override: Optional[float] = None,
) -> CommandResult:
    payloads = _prepare_payloads(definition)
    start = time.perf_counter()
    written = interface.write(payloads)
    if definition.post_delay_s > 0:
        time.sleep(definition.post_delay_s)
    duration = read_duration_override if read_duration_override is not None else (definition.read_duration_s or 0.0)
    frames: List[bytes] = []
    bytes_read = 0
    if duration > 0:
        def _handle_frame(frame_bytes: bytes) -> None:
            frames.append(frame_bytes)
        bytes_read = interface.run_window(duration, frame_handler=_handle_frame, print_raw=False)
    expected_bytes = _decode_expectation(definition.expect_hex)
    matched = None
    if expected_bytes is not None:
        matched = bool(frames and frames[0].startswith(expected_bytes))
    elapsed = time.perf_counter() - start
    return CommandResult(
        name=definition.name,
        written_bytes=written,
        frames=frames,
        bytes_read=bytes_read,
        duration_s=elapsed,
        expected_hex=definition.expect_hex,
        matched_expectation=matched,
    )


def run_command(
    device_config: DeviceConfig,
    definition: CommandDefinition,
    read_duration_override: Optional[float] = None,
) -> CommandResult:
    interface = create_interface(device_config)
    with interface as active_interface:
        return execute_command(active_interface, definition, read_duration_override)
