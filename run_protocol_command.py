"""Execute a named protocol command against an Elmetron meter."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from elmetron import load_config
from elmetron.cli.common import apply_device_overrides, find_command, resolve_profile
from elmetron.commands import run_command
from elmetron.protocols import load_registry

DEFAULT_PROFILE = "cx505"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Execute a named protocol command')
    parser.add_argument('command', help='Command identifier defined in the protocol profile')
    parser.add_argument('--config', type=Path, help='Configuration file (json/toml/yaml)')
    parser.add_argument('--protocols', type=Path, help='Protocol registry file (toml/json/yaml)')
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
    parser.add_argument('--json', action='store_true', help='Emit result as JSON for automation use')
    return parser.parse_args(argv)


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

    try:
        definition = find_command(profile, args.command)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 3

    result = run_command(config.device, definition, read_duration_override=args.read_duration)

    if args.json:
        payload = {
            "command": result.name,
            "written_bytes": result.written_bytes,
            "bytes_read": result.bytes_read,
            "duration_s": result.duration_s,
            "frames_hex": result.frames_as_hex,
            "matched_expectation": result.matched_expectation,
            "expected_hex": result.expected_hex,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Command: {result.name}")
        print(f"Written bytes: {result.written_bytes}")
        print(f"Bytes read: {result.bytes_read}")
        print(f"Duration: {result.duration_s:.3f}s")
        if result.expected_hex:
            status = "ok" if result.matched_expectation else "mismatch"
            print(f"Expectation: {result.expected_hex} -> {status}")
        if result.frames:
            print("Frames:")
            for idx, frame in enumerate(result.frames_as_hex, 1):
                print(f"  [{idx}] {frame}")
        else:
            print("Frames: <none>")
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
