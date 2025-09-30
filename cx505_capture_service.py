"""CLI entry point for the Elmetron CX-505 acquisition service."""
from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path

from elmetron import AppConfig, load_config
from elmetron.acquisition import AcquisitionService
from elmetron.hardware import list_devices
from elmetron.protocols import load_registry
from elmetron.service import ServiceSupervisor
from elmetron.service.runner import ServiceRunner
from elmetron.storage import Database


def _apply_overrides(config: AppConfig, args: argparse.Namespace) -> AppConfig:
    device = config.device
    acquisition = config.acquisition
    storage = config.storage

    if args.device_index is not None:
        device = device.with_overrides(index=args.device_index)
    if args.device_serial:
        device = device.with_overrides(serial=args.device_serial)
    if args.baud is not None and args.baud > 0:
        device = device.with_overrides(baud=args.baud)
    if args.window_s is not None and args.window_s > 0:
        acquisition = acquisition.with_overrides(window_s=args.window_s)
    if args.idle_s is not None and args.idle_s >= 0:
        acquisition = acquisition.with_overrides(idle_s=args.idle_s)
    if args.max_runtime_s is not None and args.max_runtime_s >= 0:
        acquisition = acquisition.with_overrides(max_runtime_s=args.max_runtime_s)
    if args.database:
        storage = storage.with_overrides(database_path=args.database)

    if device is not config.device or acquisition is not config.acquisition or storage is not config.storage:
        config = config.with_overrides(device=device, acquisition=acquisition, storage=storage)

    return config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Run the Elmetron CX-505 data acquisition service.',
        epilog='The service continuously captures measurements and stores them in a local SQLite database.',
    )
    parser.add_argument('--config', type=str, required=True, help='Path to the application config TOML file.')
    parser.add_argument(
        '--protocols', type=str, required=True, help='Path to the protocols config TOML file.'
    )
    parser.add_argument('--device-index', type=int, help='Override device index (default: 0).')
    parser.add_argument('--device-serial', type=str, help='Override device by serial number.')
    parser.add_argument('--baud', type=int, help='Override baud rate.')
    parser.add_argument('--window-s', type=float, help='Override capture window duration (seconds).')
    parser.add_argument('--idle-s', type=float, help='Override idle time between windows (seconds).')
    parser.add_argument(
        '--max-runtime-s', type=float, help='Override maximum runtime (seconds, 0 = unlimited).'
    )
    parser.add_argument('--database', type=str, help='Override SQLite database file path.')
    parser.add_argument(
        '--watchdog-timeout',
        type=float,
        default=0,
        help='Enable process watchdog with specified timeout (seconds, 0 to disable).',
    )
    parser.add_argument(
        '--watchdog-poll', type=float, default=2.0, help='Watchdog poll interval (seconds).'
    )
    parser.add_argument(
        '--health-api-port', type=int, default=0, help='Enable HTTP health API on specified port (0 to disable).'
    )
    parser.add_argument(
        '--health-api-host', type=str, default='127.0.0.1', help='Health API host (default: 127.0.0.1).'
    )
    parser.add_argument(
        '--health-log', action='store_true', help='Enable detailed health logging to console.'
    )

    args = parser.parse_args(argv)

    config_path = Path(args.config)
    if not config_path.exists():
        print(f'Config file not found: {config_path}', file=sys.stderr)
        return 1

    protocols_path = Path(args.protocols)
    if not protocols_path.exists():
        print(f'Protocols file not found: {protocols_path}', file=sys.stderr)
        return 1

    config = load_config(config_path)
    config = _apply_overrides(config, args)

    registry = load_registry(protocols_path)

    database = Database(config.storage)
    database.connect()

    print('Connected hardware:')
    devices = list_devices()
    if devices:
        for device in devices:
            print(f'  [{device.index}] {device.description or "(no description)"} (S/N {device.serial or "unknown"})')
    else:
        print('  (none)')
        print('  >> Please connect a compatible Elmetron CX-505 device and retry.')
        database.close()
        return 1

    service = AcquisitionService(
        config,
        database,
        protocol_registry=registry,
    )

    watchdog_timeout = args.watchdog_timeout if args.watchdog_timeout and args.watchdog_timeout > 0 else 0.0
    watchdog_poll = args.watchdog_poll if args.watchdog_poll and args.watchdog_poll > 0 else 2.0
    health_api_port = args.health_api_port if args.health_api_port and args.health_api_port > 0 else 0
    health_api_host = args.health_api_host if health_api_port > 0 else None

    if args.health_log and watchdog_timeout <= 0:
        print('Health logging is enabled but the watchdog timeout is 0; enable --watchdog-timeout to receive alerts.')

    def _watchdog_handler(event) -> None:
        ServiceSupervisor.default_watchdog_handler(event)

    runner = ServiceRunner(
        service,
        watchdog_timeout=watchdog_timeout,
        watchdog_poll=watchdog_poll,
        on_watchdog_event=_watchdog_handler if args.health_log and watchdog_timeout > 0 else None,
        health_api_host=health_api_host,
        health_api_port=health_api_port,
    )

    if runner.health_api_address:
        host, port = runner.health_api_address
        print(f'Health API listening on http://{host}:{port}/health')

    # Setup signal handlers for graceful shutdown
    shutdown_requested = False
    
    def signal_handler(signum, frame):
        nonlocal shutdown_requested
        if not shutdown_requested:
            shutdown_requested = True
            print(f'Received shutdown signal {signum}, stopping capture...')
            runner.service.request_stop()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Windows doesn't have SIGHUP, but register if available
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, signal_handler)

    try:
        runner.run()
    except KeyboardInterrupt:
        print('Interrupted by user, stopping capture...')
        runner.service.request_stop()
    finally:
        database.close()
        if args.health_log:
            snapshot = runner.health.snapshot()
            print(
                f"Health summary: state={snapshot.state} frames={snapshot.frames} "
                f"bytes={snapshot.bytes_read} watchdog={snapshot.watchdog_alert or 'ok'}"
            )
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
