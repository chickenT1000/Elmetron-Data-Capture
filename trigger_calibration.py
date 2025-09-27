"""Interactive helper for triggering calibration commands."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from elmetron import load_config
from elmetron.cli.calibration import (
    CalibrationEntry,
    collect_calibrations,
    find_by_index,
    find_by_name,
    format_calibration_list,
)
from elmetron.cli.common import apply_device_overrides, resolve_profile
from elmetron.commands import run_command
from elmetron.protocols import load_registry

DEFAULT_PROFILE = "cx505"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Trigger calibration commands interactively or on-demand')
    parser.add_argument('--config', type=Path, help='Configuration file (json/toml/yaml) to load')
    parser.add_argument('--protocols', type=Path, help='Protocol registry file defining commands')
    parser.add_argument('--device-index', type=int, help='Override device index from config')
    parser.add_argument('--device-serial', type=str, help='Override target device serial number')
    parser.add_argument('--profile', type=str, help='Select protocol profile (default: cx505)')
    parser.add_argument('--no-profile-defaults', action='store_true', help='Do not let profiles override serial parameters')
    parser.add_argument('--baud', type=int, help='Override baud rate')
    parser.add_argument('--data-bits', dest='data_bits', type=int, choices=[7, 8], help='Override data bits')
    parser.add_argument('--stop-bits', dest='stop_bits', type=float, choices=[1.0, 1.5, 2.0], help='Override stop bits')
    parser.add_argument('--parity', type=str, choices=list('NOEMS'), help='Override parity setting')
    parser.add_argument('--poll-hex', type=str, help='Hex payload to use for poll frames')
    parser.add_argument('--poll-interval', type=float, help='Seconds between poll transmissions')
    parser.add_argument('--latency', type=int, help='FTDI latency timer in milliseconds (1-255)')
    parser.add_argument('--timeouts', type=int, nargs=2, metavar=('READ_MS', 'WRITE_MS'), help='Read/write timeouts in milliseconds')
    parser.add_argument('--read-duration', type=float, help='Override command read duration in seconds')
    parser.add_argument('--list', action='store_true', help='List available calibration commands and exit')
    parser.add_argument('--command', help='Calibration name or 1-based index to execute')
    parser.add_argument('--json', action='store_true', help='Emit command result as JSON for automation use')
    parser.add_argument('--dry-run', action='store_true', help='Print the selected command without executing it')
    parser.add_argument('-y', '--yes', action='store_true', help='Run without interactive confirmation')
    return parser.parse_args(argv)


def _select_from_arg(entries: list[CalibrationEntry], raw: str) -> CalibrationEntry:
    token = raw.strip()
    if not token:
        raise ValueError('Calibration identifier cannot be empty')
    if token.isdigit():
        index = int(token)
        try:
            return find_by_index(entries, index)
        except IndexError as exc:
            raise ValueError(str(exc)) from exc
    try:
        return find_by_name(entries, token)
    except KeyError as exc:
        raise ValueError(str(exc)) from exc


def _prompt_for_selection(entries: list[CalibrationEntry]) -> Optional[CalibrationEntry]:
    print('Available calibrations:')
    print(format_calibration_list(entries))
    while True:
        raw = input('Select calibration [index/command, q to abort]: ').strip()
        if not raw:
            continue
        lowered = raw.lower()
        if lowered in {'q', 'quit', 'exit'}:
            return None
        try:
            return _select_from_arg(entries, raw)
        except ValueError as exc:
            print(f"Invalid selection: {exc}")


def _confirm(entry: CalibrationEntry) -> bool:
    prompt = f"Run calibration '{entry.name}'"
    if entry.calibration_label:
        prompt += f" [{entry.calibration_label}]"
    prompt += '? [y/N]: '
    response = input(prompt).strip().lower()
    return response in {'y', 'yes'}


def _emit_result_json(result) -> None:
    payload = {
        'command': result.name,
        'written_bytes': result.written_bytes,
        'bytes_read': result.bytes_read,
        'duration_s': result.duration_s,
        'frames_hex': result.frames_as_hex,
        'matched_expectation': result.matched_expectation,
        'expected_hex': result.expected_hex,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _emit_result_text(result) -> None:
    print(f"Command: {result.name}")
    print(f"Written bytes: {result.written_bytes}")
    print(f"Bytes read: {result.bytes_read}")
    print(f"Duration: {result.duration_s:.3f}s")
    if result.expected_hex:
        status = 'ok' if result.matched_expectation else 'mismatch'
        print(f"Expectation: {result.expected_hex} -> {status}")
    if result.frames:
        print('Frames:')
        for idx, frame in enumerate(result.frames_as_hex, 1):
            print(f"  [{idx}] {frame}")
    else:
        print('Frames: <none>')


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    config = load_config(args.config)
    apply_device_overrides(config.device, args)

    registry = load_registry(args.protocols)
    try:
        profile = resolve_profile(registry, config.device, default_profile=DEFAULT_PROFILE)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    calibrations = collect_calibrations(profile)
    if not calibrations:
        print(f"No calibration commands defined for profile '{profile.name}'.", file=sys.stderr)
        return 4

    if args.list:
        if args.json:
            payload = [
                {
                    'name': entry.name,
                    'calibration_label': entry.calibration_label,
                    'description': entry.description,
                }
                for entry in calibrations
            ]
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(format_calibration_list(calibrations))
        return 0

    entry: Optional[CalibrationEntry]
    if args.command:
        try:
            entry = _select_from_arg(calibrations, args.command)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 3
    else:
        entry = _prompt_for_selection(calibrations)
        if entry is None:
            print('Cancelled. No calibration executed.')
            return 0

    if args.dry_run:
        print(f"Selected calibration: {entry.display_label()}")
        return 0

    if not args.yes:
        if not _confirm(entry):
            print('Cancelled. No calibration executed.')
            return 0

    try:
        result = run_command(config.device, entry.command, read_duration_override=args.read_duration)
    except Exception as exc:  # pragma: no cover - hardware failure surfaces at runtime
        print(f"Calibration failed: {exc}", file=sys.stderr)
        return 5

    if args.json:
        _emit_result_json(result)
    else:
        _emit_result_text(result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
