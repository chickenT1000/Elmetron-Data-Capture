"""Shared constants used across the Elmetron suite."""
from __future__ import annotations

CTRL_SOH = 0x01
CTRL_STX = 0x02
CTRL_ETX = 0x03
CTRL_ETB = 0x17
CTRL_RS = 0x1E

DEFAULT_POLL_SEQUENCE = bytes.fromhex("01 23 30 23 30 23 30 23 03")
FRAME_TERMINATOR = b"\r\n"

USB_VID = 0x0403  # FTDI default vendor ID
USB_PID = 0x6015  # FT231X USB UART, used by many Elmetron interfaces
