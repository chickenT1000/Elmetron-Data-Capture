"""CLI entry point for the Elmetron CX-505 acquisition service."""
from __future__ import annotations

import argparse
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
        device.index = args.device_index
    if args.device_serial:
        device.serial = args.device_serial
    if args.profile:
        device.profile = args.profile
    if args.no_profile_defaults:
        device.use_profile_defaults = False
    if args.baud is not None:
        device.baud = args.baud
    if args.data_bits is not None:
        device.data_bits = args.data_bits
    if args.stop_bits is not None:
        device.stop_bits = args.stop_bits
    if args.parity:
        device.parity = args.parity
    if args.poll_hex:
        device.poll_hex = args.poll_hex
    if args.poll_interval is not None:
        device.poll_interval_s = args.poll_interval
    if args.latency is not None:
        device.latency_timer_ms = args.latency
    if args.timeouts:
        device.read_timeout_ms, device.write_timeout_ms = args.timeouts
    if args.chunk_size is not None:
        device.chunk_size = args.chunk_size

    if args.window is not None:
        acquisition.window_s = args.window
    if args.idle is not None:
        acquisition.idle_s = args.idle
    if args.restart_delay is not None:
        acquisition.restart_delay_s = args.restart_delay
    if args.status_every is not None:
        acquisition.status_interval_s = args.status_every
    if args.max_runtime is not None:
        acquisition.max_runtime_s = args.max_runtime
    if args.quiet:
        acquisition.quiet = True

    if args.database:
        storage.database_path = args.database

    return config


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Elmetron CX-505 acquisition service")
    parser.add_argument('--config', type=Path, help='Configuration file (json/toml/yaml)')
    parser.add_argument('--protocols', type=Path, help='Protocol registry file (toml/json/yaml)')
    parser.add_argument('--list-devices', action='store_true', help='List available FTDI devices and exit')
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
    parser.add_argument('--chunk-size', dest='chunk_size', type=int, help='Read chunk size in bytes')
    parser.add_argument('--window', type=float, help='Seconds per capture window')
    parser.add_argument('--idle', type=float, help='Seconds to sleep between windows')
    parser.add_argument('--restart-delay', type=float, help='Seconds to wait before reconnecting after failure')
    parser.add_argument('--status-every', type=float, help='Status print interval in seconds (0 disables)')
    parser.add_argument('--max-runtime', type=float, help='Stop after N seconds (0 keeps running)')
    parser.add_argument('--database', type=Path, help='SQLite database path override')
    parser.add_argument('--quiet', action='store_true', help='Suppress console status output')
    parser.add_argument('--watchdog-timeout', type=float, default=0.0, help='Enable watchdog with timeout in seconds (0 disables)')
    parser.add_argument('--watchdog-poll', type=float, default=2.0, help='Watchdog poll interval in seconds (default: 2.0)')
    parser.add_argument('--health-log', action='store_true', help='Print watchdog health events to stdout')
    parser.add_argument('--health-api-host', type=str, default='127.0.0.1', help='Bind address for the local health API (default: 127.0.0.1)')
    parser.add_argument('--health-api-port', type=int, default=0, help='Port for the local health API (0 disables)')
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if args.list_devices:
        devices = list_devices()
        if not devices:
            print('No FTDI devices visible')
        else:
            for device in devices:
                label = device.description or '<no description>'
                serial = device.serial or '<no serial>'
                print(f"[{device.index}] {label} (S/N {serial}) Type={device.type} LocId=0x{device.loc_id:08X} ID=0x{device.id:08X}")
        return 0

    config = load_config(args.config)
    config = _apply_overrides(config, args)

    registry = load_registry(args.protocols)
    try:
        profile = registry.apply_to_device(config.device)
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    command_definitions = profile.commands if profile else {}

    database = Database(config.storage)
    service = AcquisitionService(
        config,
        database,
        command_definitions=command_definitions,
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













