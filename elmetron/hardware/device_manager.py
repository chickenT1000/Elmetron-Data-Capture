"""Hardware interface layer for Elmetron meters across multiple transports."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Protocol

from ..config import DeviceConfig

import cx505_d2xx


class DeviceInterface(Protocol):
    """Common interface for transport adapters."""

    def open(self) -> "ListedDevice":  # pragma: no cover - protocol signature
        ...

    def close(self) -> None:  # pragma: no cover - protocol signature
        ...

    def run_window(
        self,
        duration_s: float,
        frame_handler: Optional["FrameHandler"],
        log_path: Optional[str] = None,
        print_raw: bool = False,
    ) -> int:  # pragma: no cover - protocol signature
        ...

    def write(self, payloads: Iterable[bytes]) -> int:  # pragma: no cover - protocol signature
        ...

    def __enter__(self) -> "DeviceInterface":  # pragma: no cover - protocol signature
        ...

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - protocol signature
        ...


@dataclass(slots=True)
class ListedDevice:
    """Metadata describing a connected instrument."""

    index: int
    serial: Optional[str]
    description: Optional[str]
    flags: int = 0
    type: int = 0
    loc_id: int = 0
    id: int = 0
    transport: str = "ftdi"


FrameHandler = Callable[[bytes], None]


SUPPORTED_TRANSPORTS = {"ftdi", "ble", "sim"}


def list_devices(transport: str = "ftdi") -> list[ListedDevice]:
    """Enumerate visible devices for *transport*."""

    transport = transport.lower()
    if transport == "sim":
        return [
            ListedDevice(
                index=0,
                serial="SIM-DEVICE",
                description="Simulated CX-505",
                transport="sim",
            )
        ]
    if transport != "ftdi":
        raise ValueError(f"Device enumeration is not implemented for transport '{transport}'")
    devices: list[ListedDevice] = []
    for index, info in enumerate(cx505_d2xx.enumerate_devices()):
        devices.append(
            ListedDevice(
                index=index,
                serial=info.get("serial"),
                description=info.get("description"),
                flags=info.get("flags", 0),
                type=info.get("type", 0),
                loc_id=info.get("loc_id", 0),
                id=info.get("id", 0),
                transport="ftdi",
            )
        )
    return devices


class CX505Interface(DeviceInterface):
    """Manage a CX-505 connection using the FTDI D2XX bridge."""

    def __init__(self, config: DeviceConfig):
        self._config = config
        self._handle: Optional[cx505_d2xx.HANDLE] = None
        self._device: Optional[ListedDevice] = None
        self._poll_payload: Optional[bytes] = _parse_hex_bytes(config.poll_hex) if config.poll_hex else None

    @property
    def device(self) -> Optional[ListedDevice]:
        return self._device

    def open(self) -> ListedDevice:
        if self._handle is not None:
            assert self._device is not None
            return self._device
        devices = list_devices()
        if not devices:
            raise RuntimeError("No FTDI D2XX devices detected")
        target: Optional[ListedDevice] = None
        if self._config.serial:
            for entry in devices:
                if entry.serial and entry.serial.strip() == self._config.serial:
                    target = entry
                    break
            if target is None:
                raise RuntimeError(f"Serial '{self._config.serial}' not found among connected devices")
            handle = cx505_d2xx.open_device(0, self._config.serial)
        else:
            if self._config.index >= len(devices):
                raise RuntimeError(f"Device index {self._config.index} out of range (found {len(devices)})")
            target = devices[self._config.index]
            handle = cx505_d2xx.open_device(self._config.index)
        cx505_d2xx.configure_device(
            handle,
            self._config.baud,
            self._config.data_bits,
            self._config.stop_bits,
            self._config.parity,
            self._config.read_timeout_ms,
            self._config.write_timeout_ms,
        )
        cx505_d2xx.apply_control_lines(handle, self._config.dtr, self._config.rts)
        self._handle = handle
        assert target is not None
        target.transport = "ftdi"
        self._device = target
        if self._poll_payload:
            cx505_d2xx.write_payloads(handle, [self._poll_payload])
        return target

    def close(self) -> None:
        if self._handle is not None:
            try:
                cx505_d2xx.close_device(self._handle)
            finally:
                self._handle = None
                self._device = None

    def run_window(
        self,
        duration_s: float,
        frame_handler: Optional[FrameHandler],
        log_path: Optional[str] = None,
        print_raw: bool = False,
    ) -> int:
        if self._handle is None:
            self.open()
        assert self._handle is not None
        poll_interval = self._config.poll_interval_s if self._config.poll_interval_s is not None else 1.0
        total = cx505_d2xx.read_stream(
            self._handle,
            duration_s,
            self._config.chunk_size,
            hex_dump=False,
            log_path=log_path,
            poll_payload=self._poll_payload,
            poll_interval=poll_interval,
            frame_handler=frame_handler,
            print_raw=print_raw,
        )
        return total

    def write(self, payloads: Iterable[bytes]) -> int:
        if self._handle is None:
            self.open()
        assert self._handle is not None
        return cx505_d2xx.write_payloads(self._handle, payloads)

    def __enter__(self) -> "CX505Interface":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        self.close()


class BleAdapter(Protocol):
    """Minimal protocol for BLE client adapters."""

    def connect(self) -> None:  # pragma: no cover - protocol signature
        ...

    def disconnect(self) -> None:  # pragma: no cover - protocol signature
        ...

    def read(self, timeout: float) -> Optional[bytes]:  # pragma: no cover - protocol signature
        ...

    def write(self, payload: bytes) -> None:  # pragma: no cover - protocol signature
        ...

    def info(self) -> dict[str, Optional[str]]:  # pragma: no cover - optional hook
        ...


class BleBridgeInterface(DeviceInterface):
    """Bridge interface for BLE-connected instruments.

    The implementation relies on a user-supplied *adapter_factory* that produces a
    ``BleAdapter``. A default factory can be provided in deployments that install
    BLE dependencies (e.g. bleak); tests may inject lightweight fakes.
    """

    def __init__(
        self,
        config: DeviceConfig,
        adapter_factory: Optional[Callable[[DeviceConfig], BleAdapter]] = None,
        read_interval_s: float = 0.1,
    ) -> None:
        self._config = config
        self._adapter_factory = adapter_factory or _default_ble_adapter_factory
        self._adapter: Optional[BleAdapter] = None
        self._device: Optional[ListedDevice] = None
        self._connected = False
        self._read_interval_s = max(read_interval_s, 0.01)

    def open(self) -> ListedDevice:
        adapter = self._ensure_adapter()
        if not self._connected:
            adapter.connect()
            self._connected = True
            info = _adapter_info(adapter)
            description = info.get("description") or self._config.handshake or "BLE bridge"
            serial = info.get("serial") or self._config.serial
            self._device = ListedDevice(
                index=self._config.index,
                serial=serial,
                description=description,
                transport="ble",
            )
            self._maybe_send_handshake(adapter)
        assert self._device is not None
        return self._device

    def close(self) -> None:
        if self._adapter and self._connected:
            try:
                self._adapter.disconnect()
            finally:
                self._connected = False
                self._device = None

    def run_window(
        self,
        duration_s: float,
        frame_handler: Optional[FrameHandler],
        log_path: Optional[str] = None,
        print_raw: bool = False,
    ) -> int:
        _ = log_path, print_raw  # BLE transport does not currently support raw logging.
        if duration_s <= 0:
            return 0
        self.open()
        assert self._adapter is not None
        total = 0
        deadline = time.monotonic() + duration_s
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            timeout = min(self._read_interval_s, remaining)
            chunk = self._adapter.read(timeout)
            if not chunk:
                continue
            total += len(chunk)
            if frame_handler:
                frame_handler(chunk)
        return total

    def write(self, payloads: Iterable[bytes]) -> int:
        self.open()
        assert self._adapter is not None
        bytes_written = 0
        for payload in payloads:
            if not isinstance(payload, (bytes, bytearray)):
                raise TypeError("BLE payloads must be bytes-like")
            self._adapter.write(bytes(payload))
            bytes_written += len(payload)
        return bytes_written

    def __enter__(self) -> "BleBridgeInterface":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        self.close()

    def _ensure_adapter(self) -> BleAdapter:
        if self._adapter is None:
            self._adapter = self._adapter_factory(self._config)
        return self._adapter

    def _maybe_send_handshake(self, adapter: BleAdapter) -> None:
        handshake = (self._config.handshake or "").strip()
        if not handshake:
            return
        try:
            handshake_method = getattr(adapter, "handshake", None)
            if callable(handshake_method):
                handshake_method(handshake)
                return
            adapter.write(handshake.encode("utf-8"))
        except Exception:  # pragma: no cover - best effort handshake
            pass


def create_interface(
    config: DeviceConfig,
    *,
    adapter_factory: Optional[Callable[[DeviceConfig], BleAdapter]] = None,
) -> DeviceInterface:
    """Create an interface instance based on *config.transport*."""

    transport = (config.transport or "ftdi").lower()
    if transport == "ftdi":
        return CX505Interface(config)
    if transport == "ble":
        return BleBridgeInterface(config, adapter_factory=adapter_factory)
    if transport == "sim":
        return SimulatedInterface(config)
    raise ValueError(f"Unsupported transport '{config.transport}'")


def _adapter_info(adapter: BleAdapter) -> dict[str, Optional[str]]:
    try:
        info = adapter.info()
    except AttributeError:
        return {}
    except Exception:  # pragma: no cover - defensive
        return {}
    if not isinstance(info, dict):
        return {}
    return {key: info.get(key) for key in ("serial", "description")}


def _default_ble_adapter_factory(config: DeviceConfig) -> BleAdapter:
    from .ble import create_ble_adapter

    return create_ble_adapter(config)


def _parse_hex_bytes(payload: str) -> Optional[bytes]:
    payload = payload.strip()
    if not payload:
        return None
    parts = payload.replace(",", " ").split()
    return bytes(int(part, 16) for part in parts)


class SimulatedInterface(DeviceInterface):
    """In-memory simulation of a CX-505 interface for bench harness runs."""

    def __init__(self, config: DeviceConfig) -> None:
        self._config = config
        self._device = ListedDevice(
            index=config.index,
            serial=config.serial or "SIM-DEVICE",
            description="Simulated CX-505",
            transport="sim",
        )
        self._opened = False
        self._frame_counter = 0

    def open(self) -> ListedDevice:
        self._opened = True
        return self._device

    def close(self) -> None:
        self._opened = False

    def run_window(
        self,
        duration_s: float,
        frame_handler: Optional[FrameHandler],
        log_path: Optional[str] = None,
        print_raw: bool = False,
    ) -> int:
        _ = print_raw
        self.open()
        samples = max(int(duration_s * 5), 1)
        frames: list[bytes] = []
        total = 0
        for _ in range(samples):
            frame = self._generate_frame()
            frames.append(frame)
            total += len(frame)
            if frame_handler:
                frame_handler(frame)
        if log_path:
            with open(log_path, "ab") as handle:
                for frame in frames:
                    handle.write(frame + b"\n")
        return total

    def write(self, payloads: Iterable[bytes]) -> int:
        return sum(len(payload) for payload in payloads)

    def __enter__(self) -> "SimulatedInterface":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        self.close()

    def _generate_frame(self) -> bytes:
        self._frame_counter += 1
        value = 700 + (self._frame_counter % 50)
        timestamp = int(time.time())
        payload = f"SIM:{self._frame_counter:04d}:{value:03d}:{timestamp}".encode("ascii")
        return payload[:64]

