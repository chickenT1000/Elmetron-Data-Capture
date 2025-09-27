from __future__ import annotations

import textwrap

import pytest

from elmetron.protocols.validator import (  # type: ignore
    ValidationResult,
    validate_profiles,
)
from validate_protocols import main as validate_cli


def _valid_profile() -> dict[str, object]:
    return {
        "transport": "ftdi",
        "poll_hex": "01 02",
        "poll_interval_s": 1.0,
        "baud": 9600,
        "data_bits": 8,
        "stop_bits": 2.0,
        "parity": "E",
        "latency_timer_ms": 1,
        "read_timeout_ms": 100,
        "write_timeout_ms": 100,
        "chunk_size": 64,
        "commands": {
            "calibrate": {
                "write_hex": "AA BB",
                "post_delay_s": 0.5,
                "read_duration_s": 1.0,
                "expect_hex": "01",
                "default_max_retries": 0,
            }
        },
    }


def test_validate_profiles_accepts_valid_profile() -> None:
    profiles = {"cx505": _valid_profile()}
    result = validate_profiles(profiles)
    assert isinstance(result, ValidationResult)
    assert not result.errors
    assert not result.warnings


def test_validate_profiles_flags_command_issues() -> None:
    broken = _valid_profile()
    broken["poll_hex"] = "GG"  # invalid hex
    broken["commands"]["calibrate"]["post_delay_s"] = -1  # type: ignore[index]
    broken["commands"]["calibrate"]["write_hex"] = "ZZ"  # type: ignore[index]
    profiles = {"cx505": broken}

    result = validate_profiles(profiles)
    messages = {issue.message for issue in result.errors}
    assert any(issue.location.endswith('poll_hex') for issue in result.errors)
    assert any("post_delay_s" in issue.location for issue in result.errors)
    assert any("write_hex" in issue.location for issue in result.errors)


def test_validate_profiles_reports_missing_command_payload() -> None:
    profile = _valid_profile()
    profile["commands"]["noop"] = {}  # type: ignore[index]
    result = validate_profiles({"cx505": profile})
    assert any("Command must define" in issue.message for issue in result.errors)


def test_cli_reports_errors(tmp_path, capsys) -> None:
    registry = tmp_path / "protocols.toml"
    registry.write_text(
        textwrap.dedent(
            """
            [profiles.cx505]
            transport = "serial"
            poll_interval_s = 0

            [profiles.cx505.commands.bad]
            write_ascii = 123
            """
        ),
        encoding="utf-8",
    )

    exit_code = validate_cli([str(registry)])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Unknown transport" in captured.out
    assert "poll_interval_s" in captured.out
    assert "write_ascii" in captured.out


def test_cli_warnings_toggle(tmp_path, capsys) -> None:
    registry = tmp_path / "protocols.toml"
    registry.write_text(
        textwrap.dedent(
            """
            [profiles.lab_meter]
            poll_hex = "01 02"
            poll_interval_s = 1
            baud = 9600
            data_bits = 8
            stop_bits = 2
            parity = "E"
            latency_timer_ms = 1
            read_timeout_ms = 100
            write_timeout_ms = 100
            chunk_size = 64

            [profiles.lab_meter.commands.ping]
            write_ascii = "PING\\n"
            read_duration_s = 1
            """
        ),
        encoding="utf-8",
    )

    exit_code = validate_cli([str(registry)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Validation OK" in captured.out

    exit_code = validate_cli([str(registry), "--warnings-as-errors"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Warnings treated as errors" in captured.out

