from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .registry import _load_json, _load_toml, _load_yaml

VALID_TRANSPORTS = {"ftdi", "ble", "sim"}
VALID_PARITIES = {"N", "E", "O", "M", "S"}


@dataclass(slots=True)
class ValidationIssue:
    level: str
    location: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - helper for CLI
        return f"[{self.level}] {self.location}: {self.message}"


@dataclass(slots=True)
class ValidationResult:
    issues: List[ValidationIssue]

    @property
    def errors(self) -> List[ValidationIssue]:
        return [issue for issue in self.issues if issue.level == "error"]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [issue for issue in self.issues if issue.level == "warning"]

    def extend(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues.extend(issues)

    def merge(self, other: "ValidationResult") -> None:
        self.issues.extend(other.issues)


def validate_registry_payload(payload: Mapping[str, Any]) -> ValidationResult:
    issues: List[ValidationIssue] = []
    profiles = payload.get("profiles") if isinstance(payload, Mapping) else None
    if not isinstance(profiles, Mapping):
        issues.append(ValidationIssue("error", "profiles", "Expected 'profiles' mapping"))
        return ValidationResult(issues)
    issues.extend(validate_profiles(profiles).issues)
    return ValidationResult(issues)


def validate_registry_file(path: Path) -> ValidationResult:
    if not path.exists():
        return ValidationResult([ValidationIssue("error", str(path), "Registry file not found")])

    suffix = path.suffix.lower()
    try:
        if suffix in {".toml", ".tml"}:
            payload = _load_toml(path)
        elif suffix in {".json", ".jsn"}:
            payload = _load_json(path)
        elif suffix in {".yaml", ".yml"}:
            payload = _load_yaml(path)
        else:
            return ValidationResult([
                ValidationIssue("error", str(path), f"Unsupported registry format '{path.suffix}'"),
            ])
    except Exception as exc:  # pragma: no cover - parsing safety
        return ValidationResult([
            ValidationIssue("error", str(path), f"Failed to parse registry: {exc}"),
        ])
    if not isinstance(payload, Mapping):
        return ValidationResult([
            ValidationIssue("error", str(path), "Registry root must be a mapping"),
        ])
    return validate_registry_payload(payload)


def validate_profiles(profiles: Mapping[str, Any]) -> ValidationResult:
    issues: List[ValidationIssue] = []
    if not profiles:
        issues.append(ValidationIssue("error", "profiles", "No protocol profiles defined"))
        return ValidationResult(issues)
    name_counts: Dict[str, int] = {}
    for name, profile in profiles.items():
        location = f"profiles.{name}"
        if not isinstance(profile, Mapping):
            issues.append(ValidationIssue("error", location, "Profile must be a mapping"))
            continue
        lowered = name.lower()
        name_counts[lowered] = name_counts.get(lowered, 0) + 1
        issues.extend(_validate_profile(name, profile))

    for lowered, count in name_counts.items():
        if count > 1:
            issues.append(
                ValidationIssue(
                    "error",
                    f"profiles.{lowered}",
                    "Duplicate profile name detected (case-insensitive)",
                )
            )

    return ValidationResult(issues)


def _validate_profile(name: str, profile: Mapping[str, Any]) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    location = f"profiles.{name}"

    transport = profile.get("transport")
    if transport is None:
        issues.append(ValidationIssue("warning", f"{location}.transport", "Transport not specified; defaulting to 'ftdi'"))
    elif not isinstance(transport, str) or not transport.strip():
        issues.append(ValidationIssue("error", f"{location}.transport", "Transport must be a non-empty string"))
    elif transport not in VALID_TRANSPORTS:
        issues.append(
            ValidationIssue(
                "error",
                f"{location}.transport",
                f"Unknown transport '{transport}'; expected one of {sorted(VALID_TRANSPORTS)}",
            )
        )

    poll_hex = profile.get("poll_hex")
    if poll_hex is not None and not _is_hex_string(poll_hex):
        issues.append(ValidationIssue("error", f"{location}.poll_hex", "poll_hex must be space-separated hex bytes"))

    poll_interval = profile.get("poll_interval_s")
    if poll_interval is not None and not _is_positive_number(poll_interval, allow_zero=False):
        issues.append(ValidationIssue("error", f"{location}.poll_interval_s", "poll_interval_s must be > 0"))

    baud = profile.get("baud")
    if baud is not None and not _is_positive_int(baud):
        issues.append(ValidationIssue("error", f"{location}.baud", "baud must be a positive integer"))

    data_bits = profile.get("data_bits")
    if data_bits is not None and not _is_positive_int(data_bits):
        issues.append(ValidationIssue("error", f"{location}.data_bits", "data_bits must be a positive integer"))

    stop_bits = profile.get("stop_bits")
    if stop_bits is not None and not _is_positive_number(stop_bits, allow_zero=False):
        issues.append(ValidationIssue("error", f"{location}.stop_bits", "stop_bits must be > 0"))

    parity = profile.get("parity")
    if parity is not None and (not isinstance(parity, str) or parity.upper() not in VALID_PARITIES):
        issues.append(
            ValidationIssue(
                "error",
                f"{location}.parity",
                f"parity must be one of {sorted(VALID_PARITIES)}",
            )
        )

    latency = profile.get("latency_timer_ms")
    if latency is not None and not _is_non_negative_int(latency):
        issues.append(ValidationIssue("error", f"{location}.latency_timer_ms", "latency_timer_ms must be >= 0"))

    read_timeout = profile.get("read_timeout_ms")
    if read_timeout is not None and not _is_non_negative_int(read_timeout):
        issues.append(ValidationIssue("error", f"{location}.read_timeout_ms", "read_timeout_ms must be >= 0"))

    write_timeout = profile.get("write_timeout_ms")
    if write_timeout is not None and not _is_non_negative_int(write_timeout):
        issues.append(ValidationIssue("error", f"{location}.write_timeout_ms", "write_timeout_ms must be >= 0"))

    chunk_size = profile.get("chunk_size")
    if chunk_size is not None and not _is_positive_int(chunk_size):
        issues.append(ValidationIssue("error", f"{location}.chunk_size", "chunk_size must be a positive integer"))

    commands = profile.get("commands")
    if commands is not None:
        if not isinstance(commands, Mapping):
            issues.append(ValidationIssue("error", f"{location}.commands", "commands must be a mapping"))
        else:
            command_names: Dict[str, int] = {}
            for command_name, command_data in commands.items():
                lowered = command_name.lower()
                command_names[lowered] = command_names.get(lowered, 0) + 1
                issues.extend(_validate_command(name, command_name, command_data))
            for lowered, count in command_names.items():
                if count > 1:
                    issues.append(
                        ValidationIssue(
                            "error",
                            f"{location}.commands.{lowered}",
                            "Duplicate command name detected (case-insensitive)",
                        )
                    )
    else:
        issues.append(
            ValidationIssue("warning", f"{location}.commands", "Profile defines no commands")
        )

    return issues


def _validate_command(profile_name: str, command_name: str, command_data: Any) -> List[ValidationIssue]:
    location = f"profiles.{profile_name}.commands.{command_name}"
    issues: List[ValidationIssue] = []

    if not isinstance(command_data, Mapping):
        issues.append(ValidationIssue("error", location, "Command definition must be a mapping"))
        return issues

    write_hex = command_data.get("write_hex")
    write_ascii = command_data.get("write_ascii")

    if not write_hex and not write_ascii:
        issues.append(ValidationIssue("error", f"{location}.write_hex", "Command must define write_hex or write_ascii"))
    if write_hex and not _is_hex_string(write_hex):
        issues.append(ValidationIssue("error", f"{location}.write_hex", "write_hex must be space-separated hex bytes"))
    if write_ascii is not None and not isinstance(write_ascii, str):
        issues.append(ValidationIssue("error", f"{location}.write_ascii", "write_ascii must be a string"))

    expect_hex = command_data.get("expect_hex")
    if expect_hex is not None and not _is_hex_string(expect_hex):
        issues.append(ValidationIssue("error", f"{location}.expect_hex", "expect_hex must be space-separated hex bytes"))

    post_delay = command_data.get("post_delay_s")
    if post_delay is not None and not _is_non_negative_number(post_delay):
        issues.append(ValidationIssue("error", f"{location}.post_delay_s", "post_delay_s must be >= 0"))

    read_duration = command_data.get("read_duration_s")
    if read_duration is not None and not _is_positive_number(read_duration, allow_zero=False):
        issues.append(ValidationIssue("error", f"{location}.read_duration_s", "read_duration_s must be > 0 when provided"))

    max_retries = command_data.get("default_max_retries")
    if max_retries is not None and not _is_non_negative_int(max_retries):
        issues.append(ValidationIssue("error", f"{location}.default_max_retries", "default_max_retries must be >= 0"))

    retry_backoff = command_data.get("default_retry_backoff_s")
    if retry_backoff is not None and not _is_positive_number(retry_backoff, allow_zero=False):
        issues.append(
            ValidationIssue(
                "error",
                f"{location}.default_retry_backoff_s",
                "default_retry_backoff_s must be > 0 when provided",
            )
        )

    category = command_data.get("category")
    if category is not None and not isinstance(category, str):
        issues.append(ValidationIssue("error", f"{location}.category", "category must be a string"))
    calibration_label = command_data.get("calibration_label")
    if calibration_label is not None and not isinstance(calibration_label, str):
        issues.append(
            ValidationIssue("error", f"{location}.calibration_label", "calibration_label must be a string"),
        )

    return issues


def _is_hex_string(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    tokens = [token for token in value.replace("-", " ").split() if token]
    if not tokens:
        return False
    for token in tokens:
        if len(token) != 2:
            return False
        try:
            int(token, 16)
        except ValueError:
            return False
    return True


def _is_positive_number(value: Any, *, allow_zero: bool) -> bool:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return numeric >= 0 if allow_zero else numeric > 0


def _is_non_negative_number(value: Any) -> bool:
    return _is_positive_number(value, allow_zero=True)


def _is_positive_int(value: Any) -> bool:
    try:
        integer = int(value)
    except (TypeError, ValueError):
        return False
    return integer > 0


def _is_non_negative_int(value: Any) -> bool:
    try:
        integer = int(value)
    except (TypeError, ValueError):
        return False
    return integer >= 0
