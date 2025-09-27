"""Windows service stub for running the acquisition supervisor."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from elmetron import AppConfig, load_config
from elmetron.acquisition import AcquisitionService
from elmetron.protocols import load_registry
from elmetron.service.runner import ServiceRunner
from elmetron.service.supervisor import ServiceSupervisor
from elmetron.storage import Database


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Console runner for the Elmetron acquisition service')
    parser.add_argument('--config', type=Path, help='Configuration file (json/toml/yaml)')
    parser.add_argument('--protocols', type=Path, help='Protocol registry file (toml/json/yaml)')
    parser.add_argument('--watchdog-timeout', type=float, default=0.0, help='Enable watchdog with timeout in seconds (0 disables)')
    parser.add_argument('--watchdog-poll', type=float, default=2.0, help='Watchdog poll interval in seconds (default: 2)')
    parser.add_argument('--health-log', action='store_true', help='Print watchdog health events to stdout')
    parser.add_argument('--health-api-host', type=str, default='127.0.0.1', help='Bind address for the local health API (default: 127.0.0.1)')
    parser.add_argument('--health-api-port', type=int, default=0, help='Port for the local health API (0 disables)')
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    config = load_config(args.config)
    registry = load_registry(args.protocols)
    try:
        _profile = registry.apply_to_device(config.device)
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    database = Database(config.storage)
    service = AcquisitionService(config, database)

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

