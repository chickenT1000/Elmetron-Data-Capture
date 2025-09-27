from __future__ import annotations

import importlib
import sys
import types
from collections import deque
from typing import Deque, List

import pytest

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


