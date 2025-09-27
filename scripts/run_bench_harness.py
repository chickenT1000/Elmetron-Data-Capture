"""Bench harness for CX-505 simulated runs.

This script launches the acquisition service with configuration overrides that
replace the live CX-505 device with the simulated transport used in tests.
It enables watchdog monitoring, health API streaming, and structured logging.

When a real CX-505 is available, remove the simulation flag and rerun with the
actual device config path.
"""

from __future__ import annotations

import argparse
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
    if args.simulation:
        cmd.extend(["--profile", "cx505_sim"])
    if args.extra_args:
        cmd.extend(args.extra_args)
    return cmd


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    command = build_command(args)
    print("Launching bench harness with command:")
    print(" ".join(command))
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
