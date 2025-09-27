"""BLE adapter implementations backed by optional bleak support."""
from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any, Callable, Deque, Optional

from ..config import DeviceConfig

try:
    from bleak import BleakClient  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    BleakClient = None


class BleakBridgeAdapter:
    """Thin synchronous wrapper around a `bleak` client."""

    def __init__(
        self,
        config: DeviceConfig,
        client_factory: Optional[Callable[[str], Any]] = None,
    ) -> None:
        factory = client_factory or BleakClient
        if factory is None:
            raise RuntimeError(
                "BLE support requires the 'bleak' package. Install it or supply a custom adapter factory."
            )
        self._client_factory = factory
        self._address = config.ble_address or config.serial
        if not self._address:
            raise RuntimeError(
                "BLE transport requires `device.ble_address` or `device.serial` to identify the instrument"
            )
        self._read_char = config.ble_read_characteristic
        self._write_char = config.ble_write_characteristic or self._read_char
        self._notify_char = config.ble_notify_characteristic
        self._connect_timeout = max(
            (config.read_timeout_ms or 10000) / 1000.0,
            1.0,
        )
        self._client: Any = None
        self._notifications: Deque[bytes] = deque()
        self._notify_active = False

    def connect(self) -> None:
        if self._client is not None:
            return
        client = self._client_factory(self._address)
        _run_async(lambda: client.connect(timeout=self._connect_timeout))
        self._client = client
        if self._notify_char:
            _run_async(lambda: client.start_notify(self._notify_char, self._handle_notification))
            self._notify_active = True

    def disconnect(self) -> None:
        if self._client is None:
            return
        if self._notify_active and self._notify_char:
            try:
                _run_async(lambda: self._client.stop_notify(self._notify_char))
            except Exception:  # pragma: no cover - best-effort cleanup
                pass
        _run_async(lambda: self._client.disconnect())
        self._client = None
        self._notify_active = False
        self._notifications.clear()

    def read(self, timeout: float) -> Optional[bytes]:
        if self._client is None:
            return None
        if self._notify_char:
            deadline = time.monotonic() + timeout if timeout else None
            while True:
                if self._notifications:
                    return self._notifications.popleft()
                if deadline is not None and time.monotonic() >= deadline:
                    return None
                time.sleep(0.05)
        if self._read_char is None:
            return None
        data = _run_async(lambda: self._client.read_gatt_char(self._read_char))
        if data is None:
            return None
        return bytes(data)

    def write(self, payload: bytes) -> None:
        if self._client is None:
            self.connect()
        if self._write_char is None:
            raise RuntimeError(
                "BLE write attempted but no `device.ble_write_characteristic` (or read characteristic) is configured"
            )
        _run_async(lambda: self._client.write_gatt_char(self._write_char, payload, response=True))

    def info(self) -> dict[str, Optional[str]]:
        return {
            "serial": self._address,
            "description": "BLE bridge",
        }

    def _handle_notification(self, _handle: int, data: bytes) -> None:
        self._notifications.append(bytes(data))


def create_ble_adapter(config: DeviceConfig) -> BleakBridgeAdapter:
    """Create a bleak-backed adapter for *config*."""

    return BleakBridgeAdapter(config)


def _run_async(factory: Callable[[], Any]) -> Any:
    """Execute an awaitable returned by *factory* on a private event loop."""

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(factory())
    finally:
        asyncio.set_event_loop(None)
        loop.close()


__all__ = ["BleakBridgeAdapter", "create_ble_adapter"]
