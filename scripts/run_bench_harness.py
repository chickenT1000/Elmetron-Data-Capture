"""Bench harness for CX-505 simulated runs.

This script launches the acquisition service with configuration overrides that
replace the live CX-505 device with the simulated transport used in tests.
It enables watchdog monitoring, health API streaming, and structured logging.

When a real CX-505 is available, remove the simulation flag and rerun with the
actual device config path.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CX-505 bench harness (simulated)")
    parser.add_argument("--config", type=Path, default=Path("config/app.toml"), help="Path to acquisition config")
    parser.add_argument(
        "--protocols",
        type=Path,
        default=Path("config/protocols.toml"),
        help="Protocol registry path",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/bench_harness.sqlite"),
        help="SQLite database path for the harness run",
    )
    parser.add_argument(
        "--health-port",
        type=int,
        default=8051,
        help="Health API port to expose during the bench run",
    )
    parser.add_argument(
        "--watchdog-timeout",
        type=float,
        default=10.0,
        help="Watchdog timeout in seconds",
    )
    parser.add_argument(
        "--window",
        type=float,
        default=2.0,
        help="Capture window duration in seconds",
    )
    parser.add_argument(
        "--idle",
        type=float,
        default=1.0,
        help="Idle duration between windows",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console stream from acquisition service",
    )
    parser.add_argument(
        "--open-retry-attempts",
        type=int,
        help="Override FTDI open retry attempts",
    )
    parser.add_argument(
        "--open-retry-backoff",
        type=float,
        help="Override FTDI open retry backoff in seconds",
    )
    parser.add_argument(
        "--restart-backoff-max",
        type=float,
        help="Maximum reconnect delay after repeated device failures",
    )
    parser.add_argument(
        "--simulation",
        action="store_true",
        default=False,
        help="Enable simulation profile overrides",
    )
    parser.add_argument(
        "--extra-args",
        nargs=argparse.REMAINDER,
        help="Additional arguments passed to cx505_capture_service.py",
    )
    return parser.parse_args(argv)


def build_command(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        "cx505_capture_service.py",
        "--config",
        str(args.config),
        "--protocols",
        str(args.protocols),
        "--database",
        str(args.database),
        "--health-api-port",
        str(args.health_port),
        "--watchdog-timeout",
        str(args.watchdog_timeout),
        "--watchdog-poll",
        "2.0",
        "--status-every",
        "5",
        "--window",
        str(args.window),
        "--idle",
        str(args.idle),
    ]
    if args.quiet:
        cmd.append("--quiet")
    if args.open_retry_attempts is not None:
        cmd.extend(["--open-retry-attempts", str(args.open_retry_attempts)])
    if args.open_retry_backoff is not None:
        cmd.extend(["--open-retry-backoff", str(args.open_retry_backoff)])
    if args.restart_backoff_max is not None:
        cmd.extend(["--restart-backoff-max", str(args.restart_backoff_max)])
    if args.simulation:
        cmd.extend(["--profile", "cx505_sim"])
    if args.extra_args:
        cmd.extend(args.extra_args)
    return cmd


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not _check_existing_capture_processes():
        print("Aborting harness launch; please stop the existing cx505_capture_service instance and retry.")
        return 1
    command = build_command(args)
    print("Launching bench harness with command:")
    print(" ".join(command))
    return subprocess.call(command)


def _check_existing_capture_processes() -> bool:
    """Return True when no other capture service instance appears to be running."""

    if os.name != "nt":
        return True
    try:
        output = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/V"],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return True

    lowered = output.lower()
    if "cx505_capture_service.py" not in lowered:
        return True
    print("Detected an existing python.exe running cx505_capture_service.py."
          " Close it before starting the bench harness.")
    return False


if __name__ == "__main__":
    raise SystemExit(main())
