from __future__ import annotations

import importlib
import sys
import types
from collections import deque
from typing import Deque, List, Optional

import pytest

import elmetron.hardware.device_manager as device_manager
from elmetron.config import DeviceConfig
from elmetron.hardware import BleBridgeInterface, CX505Interface, SimulatedInterface, create_interface


class FakeBleAdapter:
    """In-memory BLE adapter used for unit tests."""

    def __init__(self, frames: List[bytes] | None = None) -> None:
        self.connected = False
        self.frames: Deque[bytes] = deque(frames or [])
        self.written: List[bytes] = []

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def read(self, timeout: float) -> bytes | None:  # pragma: no cover - invoked indirectly
        if self.frames:
            return self.frames.popleft()
        return None

    def write(self, payload: bytes) -> None:
        self.written.append(bytes(payload))

    def info(self) -> dict[str, str]:
        return {"serial": "BLE123", "description": "Test BLE adapter"}


def test_create_interface_ftdi_returns_cx505() -> None:
    config = DeviceConfig()
    interface = create_interface(config)
    assert isinstance(interface, CX505Interface)


def test_create_interface_simulated_generates_frames(tmp_path) -> None:
    config = DeviceConfig(transport="sim", profile="cx505_sim")
    interface = create_interface(config)
    assert isinstance(interface, SimulatedInterface)

    frames: list[bytes] = []
    total = interface.run_window(1.0, frame_handler=frames.append, log_path=str(tmp_path / "sim.log"))
    assert total > 0
    assert frames
    assert frames[0].startswith(b"SIM:")
    interface.close()


def test_create_interface_ble_uses_supplied_adapter_factory() -> None:
    frames = [b"abc", b"defg"]
    adapter = FakeBleAdapter(frames)
    config = DeviceConfig(transport="ble", handshake="HELLO")
    collected: List[bytes] = []

    interface = create_interface(config, adapter_factory=lambda cfg: adapter)
    assert isinstance(interface, BleBridgeInterface)

    total = interface.run_window(0.05, frame_handler=collected.append)
    assert total == sum(len(frame) for frame in frames)
    assert collected == frames
    assert adapter.connected
    assert adapter.written[0] == b"HELLO"

    interface.close()
    assert not adapter.connected


def test_ble_write_sends_payloads_via_adapter() -> None:
    adapter = FakeBleAdapter()
    config = DeviceConfig(transport="ble")
    interface = BleBridgeInterface(config, adapter_factory=lambda _: adapter)

    written = interface.write([b"12", b"345"])
    assert written == 5
    assert adapter.written == [b"12", b"345"]

    interface.close()


def test_default_ble_adapter_factory_raises_without_dependency() -> None:
    config = DeviceConfig(
        transport="ble",
        ble_address="AA:BB",
        ble_read_characteristic="0000ffe1-0000-1000-8000-00805f9b34fb",
    )
    interface = create_interface(config)
    with pytest.raises(RuntimeError):
        interface.open()


def test_default_ble_adapter_factory_uses_bleak_when_available(monkeypatch) -> None:
    class DummyClient:
        def __init__(self, address: str) -> None:
            self.address = address
            self.connected = False
            self.writes: list[tuple[str, bytes]] = []

        async def connect(self, timeout: float | None = None) -> None:  # pragma: no cover - exercised indirectly
            self.connected = True

        async def disconnect(self) -> None:
            self.connected = False

        async def read_gatt_char(self, characteristic: str) -> bytes:
            self.last_read_char = characteristic
            return b"\x01\x02"

        async def write_gatt_char(self, characteristic: str, data: bytes, response: bool = False) -> None:
            self.writes.append((characteristic, bytes(data)))

    fake_bleak = types.SimpleNamespace(BleakClient=DummyClient)
    monkeypatch.setitem(sys.modules, "bleak", fake_bleak)

    import elmetron.hardware.ble as ble_module
    import elmetron.hardware.device_manager as device_manager

    importlib.reload(ble_module)
    importlib.reload(device_manager)

    config = DeviceConfig(
        transport="ble",
        handshake="HELLO",
        ble_address="AA:BB",
        ble_read_characteristic="read-char",
        ble_write_characteristic="write-char",
    )

    interface = device_manager.create_interface(config)
    assert isinstance(interface, device_manager.BleBridgeInterface)

    collected: List[bytes] = []
    total = interface.run_window(0.05, frame_handler=collected.append)
    assert total > 0
    assert collected and collected[0] == b"\x01\x02"

    adapter = interface._adapter  # type: ignore[attr-defined]  # pylint: disable=protected-access
    assert adapter is not None
    client = adapter._client  # type: ignore[attr-defined]  # pylint: disable=protected-access
    assert client is not None
    assert client.writes[0] == ("write-char", b"HELLO")

    interface.close()

    del sys.modules["bleak"]
    importlib.reload(ble_module)
    importlib.reload(device_manager)


def test_cx505_interface_retries_until_success(monkeypatch) -> None:
    attempts: list[tuple[int, Optional[str]]] = []

    mock_device = device_manager.ListedDevice(index=0, serial="SER123", description="CX505")

    monkeypatch.setattr(device_manager, "list_devices", lambda: [mock_device])

    def fake_open(index: int, serial: Optional[str] = None):
        attempts.append((index, serial))
        if len(attempts) < 3:
            raise RuntimeError("FT_Open busy")
        return object()

    monkeypatch.setattr(device_manager.cx505_d2xx, "open_device", fake_open)
    monkeypatch.setattr(device_manager.cx505_d2xx, "configure_device", lambda *_, **__: None)
    monkeypatch.setattr(device_manager.cx505_d2xx, "apply_control_lines", lambda *_, **__: None)
    monkeypatch.setattr(device_manager.cx505_d2xx, "write_payloads", lambda *_, **__: None)
    monkeypatch.setattr(device_manager.cx505_d2xx, "close_device", lambda *_: None)
    monkeypatch.setattr(device_manager.time, "sleep", lambda *_: None)

    config = DeviceConfig(serial="SER123", poll_hex=None, open_retry_attempts=3, open_retry_backoff_s=0.0)
    interface = device_manager.CX505Interface(config)

    device = interface.open()
    assert device.serial == "SER123"
    assert len(attempts) == 3
    interface.close()


def test_cx505_interface_waits_for_device(monkeypatch) -> None:
    responses = [
        [],
        [device_manager.ListedDevice(index=0, serial="SER123", description="CX505")],
    ]

    def fake_list() -> list[device_manager.ListedDevice]:
        if responses:
            return responses.pop(0)
        return [device_manager.ListedDevice(index=0, serial="SER123", description="CX505")]

    monkeypatch.setattr(device_manager, "list_devices", fake_list)
    monkeypatch.setattr(device_manager.cx505_d2xx, "open_device", lambda *args, **kwargs: object())
    monkeypatch.setattr(device_manager.cx505_d2xx, "configure_device", lambda *_, **__: None)
    monkeypatch.setattr(device_manager.cx505_d2xx, "apply_control_lines", lambda *_, **__: None)
    monkeypatch.setattr(device_manager.cx505_d2xx, "write_payloads", lambda *_, **__: None)
    monkeypatch.setattr(device_manager.cx505_d2xx, "close_device", lambda *_: None)

    sleeps: list[float] = []
    monkeypatch.setattr(device_manager.time, "sleep", lambda value: sleeps.append(value))

    config = DeviceConfig(serial="SER123", poll_hex=None, open_retry_attempts=2, open_retry_backoff_s=0.1)
    interface = device_manager.CX505Interface(config)
    interface.open()
    interface.close()

    assert sleeps, "expected retry backoff to be applied"


def test_cx505_interface_raises_after_exhausted_retries(monkeypatch) -> None:
    monkeypatch.setattr(device_manager, "list_devices", lambda: [device_manager.ListedDevice(index=0, serial="SER123", description="CX505")])

    def always_fail(*_args, **_kwargs) -> object:
        raise RuntimeError("FT_Open busy")

    monkeypatch.setattr(device_manager.cx505_d2xx, "open_device", always_fail)
    monkeypatch.setattr(device_manager.cx505_d2xx, "configure_device", lambda *_, **__: None)
    monkeypatch.setattr(device_manager.cx505_d2xx, "apply_control_lines", lambda *_, **__: None)
    monkeypatch.setattr(device_manager.cx505_d2xx, "write_payloads", lambda *_, **__: None)
    monkeypatch.setattr(device_manager.cx505_d2xx, "close_device", lambda *_: None)
    monkeypatch.setattr(device_manager.time, "sleep", lambda *_: None)

    config = DeviceConfig(serial="SER123", poll_hex=None, open_retry_attempts=2, open_retry_backoff_s=0.0)
    interface = device_manager.CX505Interface(config)

    with pytest.raises(RuntimeError) as exc_info:
        interface.open()
    assert "Failed to open FTDI device" in str(exc_info.value)


def test_cx505_interface_closes_handle_on_configuration_failure(monkeypatch) -> None:
    listed = device_manager.ListedDevice(index=0, serial="SER123", description="CX505")
    monkeypatch.setattr(device_manager, "list_devices", lambda: [listed])

    handles = []

    def fake_open(*_args, **_kwargs):
        handle = object()
        handles.append(handle)
        return handle

    monkeypatch.setattr(device_manager.cx505_d2xx, "open_device", fake_open)

    configure_calls = []

    def fake_configure(handle, *args, **kwargs):
        configure_calls.append(handle)
        if len(configure_calls) == 1:
            raise RuntimeError("configure failed")

    monkeypatch.setattr(device_manager.cx505_d2xx, "configure_device", fake_configure)

    monkeypatch.setattr(device_manager.cx505_d2xx, "apply_control_lines", lambda *_, **__: None)
    monkeypatch.setattr(device_manager.cx505_d2xx, "write_payloads", lambda *_, **__: None)

    closed_handles = []
    monkeypatch.setattr(device_manager.cx505_d2xx, "close_device", lambda handle: closed_handles.append(handle))
    monkeypatch.setattr(device_manager.time, "sleep", lambda *_: None)

    config = DeviceConfig(serial="SER123", poll_hex=None, open_retry_attempts=2, open_retry_backoff_s=0.0)
    interface = device_manager.CX505Interface(config)

    device = interface.open()
    assert device.serial == "SER123"
    assert len(configure_calls) == 2
    assert closed_handles == [handles[0]]


