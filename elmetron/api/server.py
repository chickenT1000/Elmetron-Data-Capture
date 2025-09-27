"""Health/status API server for the acquisition service."""
from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from typing import Optional, Tuple

from .diagnostics import build_diagnostic_bundle
from .health import HealthMonitor, health_status_to_dict


def _serialize_datetime(value):
    if value is None:
        return None
    return value.isoformat()


def _snapshot_dict(status):
    payload = asdict(status)
    payload['last_frame_at'] = _serialize_datetime(status.last_frame_at)
    payload['last_window_started'] = _serialize_datetime(status.last_window_started)
    return payload

def _clamp_int(value, default, minimum=None, maximum=None):
    try:
        result = int(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None:
        result = max(result, minimum)
    if maximum is not None:
        result = min(result, maximum)
    return result


def _parse_float(value, default, minimum=None):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None and result < minimum:
        return minimum
    return result


def _stream_log_events(
    monitor,
    writer,
    *,
    since_id=None,
    limit=50,
    interval_s=1.0,
    heartbeat_interval_s=15.0,
    max_loops=None,
):
    """Stream audit events via Server-Sent Events."""

    last_id = since_id
    loops = 0
    heartbeat_due = time.monotonic() + max(heartbeat_interval_s, interval_s)
    while True:
        try:
            events = monitor.recent_events(limit=limit, since_id=last_id)
        except Exception:  # pragma: no cover - defensive guard
            events = []
        events_sorted = sorted(
            events,
            key=lambda item: item.get('id', 0) if isinstance(item, dict) else 0,
        )
        if events_sorted:
            for event in events_sorted:
                if not isinstance(event, dict):
                    continue
                event_id = event.get('id')
                if event_id is None:
                    continue
                try:
                    last_id = int(event_id)
                except (TypeError, ValueError):
                    continue
                payload = json.dumps(event, ensure_ascii=False)
                message = (
                    f"id: {last_id}\n"
                    "event: log\n"
                    f"data: {payload}\n\n"
                )
                writer.write(message.encode('utf-8'))
            writer.flush()
            heartbeat_due = time.monotonic() + max(heartbeat_interval_s, interval_s)
        else:
            now = time.monotonic()
            if now >= heartbeat_due:
                writer.write(b': heartbeat\n\n')
                writer.flush()
                heartbeat_due = now + max(heartbeat_interval_s, interval_s)
        loops += 1
        if max_loops is not None and loops >= max_loops:
            break
        sleep_interval = max(interval_s, 0.0)
        if sleep_interval:
            time.sleep(sleep_interval)




def _handler_factory(monitor: HealthMonitor):
    class HealthHandler(BaseHTTPRequestHandler):  # type: ignore[misc]
        """Minimal handler that exposes /health JSON endpoint."""

        protocol_version = "HTTP/1.1"

        def do_GET(self):  # pylint: disable=invalid-name
            parsed = urlparse(self.path)
            path = parsed.path.rstrip('/')
            if path == '/health':
                status = monitor.snapshot()
                body = json.dumps(health_status_to_dict(status), ensure_ascii=False).encode('utf-8')
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif path == '/health/logs/stream':
                self._handle_log_stream(parsed)
            elif path == '/health/bundle':
                self._handle_bundle(parsed)
            elif path == '/health/logs':
                params = parse_qs(parsed.query)
                limit_param = params.get('limit', ['20'])[-1]
                since_param = params.get('since_id', [None])[-1]
                try:
                    limit = int(limit_param)
                except (TypeError, ValueError):
                    limit = 20
                try:
                    since_id = int(since_param) if since_param is not None else None
                except (TypeError, ValueError):
                    since_id = None
                try:
                    events = monitor.recent_events(limit=limit, since_id=since_id)
                except Exception as exc:  # pragma: no cover - defensive
                    self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f'Failed to fetch events: {exc}')
                    return
                body = json.dumps({'events': events}, ensure_ascii=False).encode('utf-8')
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_error(HTTPStatus.NOT_FOUND, 'Endpoint not found')



        def _handle_bundle(self, parsed):
            params = parse_qs(parsed.query)
            event_limit = _clamp_int(params.get('events', ['200'])[-1], default=200, minimum=1, maximum=1000)
            session_limit = _clamp_int(params.get('sessions', ['5'])[-1], default=5, minimum=0, maximum=100)
            filename = params.get('filename', [None])[-1]
            if not filename:
                filename = f"elmetron_diagnostic_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.zip"
            try:
                bundle_bytes = build_diagnostic_bundle(
                    monitor.service,
                    monitor,
                    event_limit=event_limit,
                    session_limit=session_limit,
                )
            except Exception as exc:  # pragma: no cover - defensive
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f'Failed to build diagnostic bundle: {exc}')
                return

            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Content-Length', str(len(bundle_bytes)))
            self.end_headers()
            self.wfile.write(bundle_bytes)


        def _handle_log_stream(self, parsed):
            params = parse_qs(parsed.query)
            limit = _clamp_int(params.get('limit', ['50'])[-1], default=50, minimum=1, maximum=500)
            interval_s = _parse_float(params.get('interval_s', ['1'])[-1], default=1.0, minimum=0.0)
            heartbeat_s = _parse_float(
                params.get('heartbeat_s', ['15'])[-1],
                default=15.0,
                minimum=max(interval_s, 0.1) if interval_s else 0.1,
            )
            since_param = params.get('since_id', [None])[-1]
            last_event_header = self.headers.get('Last-Event-ID') if hasattr(self, 'headers') else None
            since_id = None
            for candidate in (last_event_header, since_param):
                if candidate is None:
                    continue
                try:
                    since_id = int(candidate)
                except (TypeError, ValueError):
                    continue
                else:
                    break

            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()
            retry_ms = max(int(max(interval_s, 0.5) * 1000), 1000)
            try:
                self.wfile.write(f'retry: {retry_ms}\n\n'.encode('utf-8'))
                self.wfile.flush()
                _stream_log_events(
                    monitor,
                    self.wfile,
                    since_id=since_id,
                    limit=limit,
                    interval_s=max(interval_s, 0.0),
                    heartbeat_interval_s=max(heartbeat_s, 0.1),
                )
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):  # pragma: no cover - client disconnect
                return
            except Exception:  # pragma: no cover - defensive
                return

        def log_message(self, format, *args):  # noqa: A003 - silence default logging
            return

    return HealthHandler


class HealthApiServer:
    """Threaded HTTP server that publishes the acquisition health snapshot."""

    def __init__(
        self,
        monitor: HealthMonitor,
        host: str = '127.0.0.1',
        port: int = 0,
    ) -> None:
        handler = _handler_factory(monitor)
        self._server = ThreadingHTTPServer((host, port), handler)
        self._thread: Optional[threading.Thread] = None

    @property
    def address(self) -> Tuple[str, int]:
        return self._server.server_address  # type: ignore[return-value]

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._server.serve_forever, name='health-api', daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._server.server_close()



