from __future__ import annotations

import pytest

from elmetron.cli.calibration import collect_calibrations, find_by_index, find_by_name
from elmetron.protocols.registry import CommandDefinition, ProtocolProfile


def _build_profile() -> ProtocolProfile:
    commands = {
        "calibrate_ph7": CommandDefinition(
            name="calibrate_ph7",
            description="Buffer 7",
            category="calibration",
            calibration_label="ph7",
            write_hex="02 43 41 4C 37 03",
        ),
        "calibrate_ph4": CommandDefinition(
            name="calibrate_ph4",
            description="Buffer 4",
            calibration_label="ph4",
            write_hex="02 43 41 4C 34 03",
        ),
        "ping": CommandDefinition(name="ping", description="No-op"),
    }
    return ProtocolProfile(name="cx505", commands=commands)


def test_collect_calibrations_filters_and_sorts() -> None:
    profile = _build_profile()
    entries = collect_calibrations(profile)
    assert [entry.name for entry in entries] == ["calibrate_ph4", "calibrate_ph7"]
    assert entries[0].calibration_label == "ph4"
    assert "Buffer" in entries[1].display_label()


def test_find_by_index_validates_bounds() -> None:
    entries = collect_calibrations(_build_profile())
    assert find_by_index(entries, 1).name == "calibrate_ph4"
    with pytest.raises(IndexError):
        find_by_index(entries, 0)
    with pytest.raises(IndexError):
        find_by_index(entries, len(entries) + 1)


def test_find_by_name_case_insensitive_lookup() -> None:
    entries = collect_calibrations(_build_profile())
    assert find_by_name(entries, "CALIBRATE_PH7").name == "calibrate_ph7"
    with pytest.raises(KeyError):
        find_by_name(entries, "unknown")
