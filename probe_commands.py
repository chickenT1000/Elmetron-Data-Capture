import ctypes
import time

import cx505_d2xx as cx

COMMANDS = [
    bytes.fromhex(hex_str)
    for hex_str in (
        '02 03',
        '02 20 03',
        '02 30 03',
        '02 33 03',
        '02 37 03',
        '02 38 03',
        '02 40 03',
        '02 42 03',
        '02 48 03',
        '02 4a 31 34 03',
        '02 4e 31 24 03',
        '02 50 03',
        '02 58 03',
        '02 60 03',
        '02 66 03',
        '02 68 03',
        '02 70 03',
        '02 72 03',
        '02 73 03',
        '02 74 03',
        '02 75 03',
        '02 77 03',
    )
]

BUFFER_SIZE = 1024


def main() -> int:
    devices = cx.enumerate_devices()
    if not devices:
        print('No FTDI devices visible')
        return 1
    handle = None
    try:
        handle = cx.open_device(0)
        cx.configure_device(handle, baud=115200, databits=8, stopbits=1, parity='E', read_timeout=200, write_timeout=200)
        cx.apply_control_lines(handle, 'set', 'set')
        buf = (ctypes.c_ubyte * BUFFER_SIZE)()
        transferred = cx.DWORD()
        for payload in COMMANDS:
            cx._check_status(cx._ft_purge(handle, cx.FT_PURGE_RX), 'FT_Purge_RX')
            print(f'Sending: {payload.hex(" ")}')
            try:
                sent = cx.write_payloads(handle, [payload])
            except Exception as exc:
                print(f'  Write failed: {exc}')
                continue
            print(f'  Sent {sent} byte(s)')
            time.sleep(0.2)
            transferred.value = 0
            status = cx._ft_read(handle, ctypes.byref(buf), cx.DWORD(BUFFER_SIZE), ctypes.byref(transferred))
            if status != 0:
                print(f'  Read failed, status={status}')
                continue
            if transferred.value:
                data = bytes(buf[: transferred.value])
                print(f'  Received {transferred.value} byte(s): {data.hex(" ")}')
                try:
                    text = data.decode("ascii")
                    print(f'    ASCII: {text!r}')
                except UnicodeDecodeError:
                    pass
            else:
                print('  No data')
    finally:
        if handle:
            cx.close_device(handle)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
