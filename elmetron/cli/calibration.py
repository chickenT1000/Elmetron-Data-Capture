"""Helpers for interacting with calibration commands."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from ..protocols.registry import CommandDefinition, ProtocolProfile

CALIBRATION_CATEGORY = "calibration"


@dataclass(slots=True)
class CalibrationEntry:
    """Metadata describing a calibration-capable command."""

    name: str
    description: str | None
    calibration_label: str | None
    command: CommandDefinition

    def display_label(self) -> str:
        parts: List[str] = [self.name]
        if self.calibration_label:
            parts.append(f"[{self.calibration_label}]")
        if self.description:
            parts.append(f"- {self.description}")
        return " ".join(parts)


def is_calibration_command(definition: CommandDefinition) -> bool:
    """Return True if *definition* represents a calibration routine."""

    category = (definition.category or "").strip().lower()
    if category == CALIBRATION_CATEGORY:
        return True
    return bool(definition.calibration_label)


def collect_calibrations(profile: ProtocolProfile) -> List[CalibrationEntry]:
    """Extract calibration commands from *profile* sorted for display."""

    entries: List[CalibrationEntry] = []
    for name, command in profile.commands.items():
        if not is_calibration_command(command):
            continue
        entries.append(
            CalibrationEntry(
                name=name,
                description=command.description,
                calibration_label=command.calibration_label,
                command=command,
            )
        )
    entries.sort(key=lambda item: ((item.calibration_label or "").lower(), item.name.lower()))
    return entries


def format_calibration_list(entries: Sequence[CalibrationEntry]) -> str:
    """Return a human-readable list for *entries*."""

    lines: List[str] = []
    for index, entry in enumerate(entries, start=1):
        parts: List[str] = [f"{index}. {entry.name}"]
        if entry.calibration_label:
            parts.append(f"[{entry.calibration_label}]")
        if entry.description:
            parts.append(f"- {entry.description}")
        lines.append(" ".join(parts))
    return "\n".join(lines)


def find_by_index(entries: Sequence[CalibrationEntry], index: int) -> CalibrationEntry:
    if index < 1 or index > len(entries):
        raise IndexError(f"Calibration index {index} out of range (1-{len(entries)})")
    return entries[index - 1]


def find_by_name(entries: Sequence[CalibrationEntry], name: str) -> CalibrationEntry:
    target = name.strip().lower()
    for entry in entries:
        if entry.name.lower() == target:
            return entry
    raise KeyError(f"Calibration '{name}' not found")
