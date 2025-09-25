import argparse
import ctypes
import ctypes.wintypes as wintypes
import os
import re
import json
import sys
import time
from datetime import datetime
from typing import Callable, Iterable, Optional

ftd2xx = ctypes.WinDLL('ftd2xx.dll')

FT_STATUS = ctypes.c_ulong
DWORD = ctypes.c_ulong
ULONG = ctypes.c_ulong
UCHAR = ctypes.c_ubyte
HANDLE = wintypes.HANDLE

FT_PURGE_RX = 0x01
FT_PURGE_TX = 0x02

CTRL_SOH = '\x01'
CTRL_STX = '\x02'
CTRL_ETX = '\x03'
CTRL_ETB = '\x17'
CTRL_RS = '\x1e'
CRLF_BYTES = b'\r\n'

class FT_DEVICE_LIST_INFO_NODE(ctypes.Structure):
    _fields_ = [
        ('Flags', DWORD),
        ('Type', DWORD),
        ('ID', DWORD),
        ('LocId', DWORD),
        ('SerialNumber', ctypes.c_char * 16),
        ('Description', ctypes.c_char * 64),
        ('ftHandle', HANDLE),
    ]

def _check_status(code: int, context: str) -> None:
    if code != 0:
        raise RuntimeError(f"{context} failed with FT_STATUS={code}")

_ft_create_list = ftd2xx.FT_CreateDeviceInfoList
_ft_create_list.argtypes = [ctypes.POINTER(DWORD)]
_ft_create_list.restype = FT_STATUS

_ft_get_list = ftd2xx.FT_GetDeviceInfoList
_ft_get_list.argtypes = [ctypes.POINTER(FT_DEVICE_LIST_INFO_NODE), ctypes.POINTER(DWORD)]
_ft_get_list.restype = FT_STATUS

_ft_open = ftd2xx.FT_Open
_ft_open.argtypes = [ctypes.c_int, ctypes.POINTER(HANDLE)]
_ft_open.restype = FT_STATUS

_ft_open_ex = ftd2xx.FT_OpenEx
_ft_open_ex.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(HANDLE)]
_ft_open_ex.restype = FT_STATUS

_ft_close = ftd2xx.FT_Close
_ft_close.argtypes = [HANDLE]
_ft_close.restype = FT_STATUS

_ft_reset = ftd2xx.FT_ResetDevice
_ft_reset.argtypes = [HANDLE]
_ft_reset.restype = FT_STATUS

_ft_purge = ftd2xx.FT_Purge
_ft_purge.argtypes = [HANDLE, DWORD]
_ft_purge.restype = FT_STATUS

_ft_set_baud = ftd2xx.FT_SetBaudRate
_ft_set_baud.argtypes = [HANDLE, DWORD]
_ft_set_baud.restype = FT_STATUS

_ft_set_data_chars = ftd2xx.FT_SetDataCharacteristics
_ft_set_data_chars.argtypes = [HANDLE, UCHAR, UCHAR, UCHAR]
_ft_set_data_chars.restype = FT_STATUS

_ft_set_flow = ftd2xx.FT_SetFlowControl
_ft_set_flow.argtypes = [HANDLE, ctypes.c_ushort, UCHAR, UCHAR]
_ft_set_flow.restype = FT_STATUS

_ft_set_timeouts = ftd2xx.FT_SetTimeouts
_ft_set_timeouts.argtypes = [HANDLE, DWORD, DWORD]
_ft_set_timeouts.restype = FT_STATUS

_ft_set_chars = ftd2xx.FT_SetChars
_ft_set_chars.argtypes = [HANDLE, UCHAR, UCHAR, UCHAR, UCHAR]
_ft_set_chars.restype = FT_STATUS

_ft_set_latency = ftd2xx.FT_SetLatencyTimer
_ft_set_latency.argtypes = [HANDLE, UCHAR]
_ft_set_latency.restype = FT_STATUS

_ft_set_usb_params = ftd2xx.FT_SetUSBParameters
_ft_set_usb_params.argtypes = [HANDLE, DWORD, DWORD]
_ft_set_usb_params.restype = FT_STATUS

_ft_get_modem_status = ftd2xx.FT_GetModemStatus
_ft_get_modem_status.argtypes = [HANDLE, ctypes.POINTER(DWORD)]
_ft_get_modem_status.restype = FT_STATUS

_ft_set_dtr = ftd2xx.FT_SetDtr
_ft_set_dtr.argtypes = [HANDLE]
_ft_set_dtr.restype = FT_STATUS

_ft_clr_dtr = ftd2xx.FT_ClrDtr
_ft_clr_dtr.argtypes = [HANDLE]
_ft_clr_dtr.restype = FT_STATUS

_ft_set_rts = ftd2xx.FT_SetRts
_ft_set_rts.argtypes = [HANDLE]
_ft_set_rts.restype = FT_STATUS

_ft_clr_rts = ftd2xx.FT_ClrRts
_ft_clr_rts.argtypes = [HANDLE]
_ft_clr_rts.restype = FT_STATUS

_ft_read = ftd2xx.FT_Read
_ft_read.argtypes = [HANDLE, ctypes.c_void_p, DWORD, ctypes.POINTER(DWORD)]
_ft_read.restype = FT_STATUS

_ft_write = ftd2xx.FT_Write
_ft_write.argtypes = [HANDLE, ctypes.c_void_p, DWORD, ctypes.POINTER(DWORD)]
_ft_write.restype = FT_STATUS

_ft_queue_status = ftd2xx.FT_GetQueueStatus
_ft_queue_status.argtypes = [HANDLE, ctypes.POINTER(DWORD)]
_ft_queue_status.restype = FT_STATUS

def enumerate_devices():
    count = DWORD()
    _check_status(_ft_create_list(ctypes.byref(count)), 'FT_CreateDeviceInfoList')
    if count.value == 0:
        return []
    buffer_type = FT_DEVICE_LIST_INFO_NODE * count.value
    buffer = buffer_type()
    _check_status(_ft_get_list(buffer, ctypes.byref(count)), 'FT_GetDeviceInfoList')
    results = []
    for node in buffer[: count.value]:
        results.append({
            'flags': node.Flags,
            'type': node.Type,
            'id': node.ID,
            'loc_id': node.LocId,
            'serial': node.SerialNumber.decode(errors='ignore').strip('\x00'),
            'description': node.Description.decode(errors='ignore').strip('\x00'),
        })
    return results

def open_device(index: int, serial: Optional[str] = None) -> HANDLE:
    handle = HANDLE()
    if serial:
        serial_bytes = serial.encode('ascii')
        _check_status(
            _ft_open_ex(ctypes.c_char_p(serial_bytes), 0x00000001, ctypes.byref(handle)),
            'FT_OpenEx(serial)'
        )
    else:
        _check_status(_ft_open(index, ctypes.byref(handle)), 'FT_Open')
    return handle

def close_device(handle: HANDLE) -> None:
    if handle:
        _check_status(_ft_close(handle), 'FT_Close')

def configure_device(handle: HANDLE, baud: int, databits: int, stopbits: float, parity: str, read_timeout: int, write_timeout: int) -> None:
    stopbit_map = {1: 0x00, 1.5: 0x01, 2: 0x02}
    parity_map = {'N': 0x00, 'O': 0x01, 'E': 0x02, 'M': 0x03, 'S': 0x04}
    if databits not in (7, 8):
        raise ValueError('Only 7 or 8 data bits supported')
    if stopbits not in stopbit_map:
        raise ValueError('Stop bits must be 1, 1.5, or 2')
    parity = parity.upper()
    if parity not in parity_map:
        raise ValueError('Parity must be one of N, O, E, M, S')

    _check_status(_ft_reset(handle), 'FT_ResetDevice')
    _check_status(_ft_purge(handle, FT_PURGE_RX | FT_PURGE_TX), 'FT_Purge')
    _check_status(_ft_set_baud(handle, DWORD(baud)), 'FT_SetBaudRate')
    _check_status(_ft_set_data_chars(handle, UCHAR(databits), UCHAR(stopbit_map[stopbits]), UCHAR(parity_map[parity])), 'FT_SetDataCharacteristics')
    _check_status(_ft_set_flow(handle, ctypes.c_ushort(0), UCHAR(0), UCHAR(0)), 'FT_SetFlowControl')
    _check_status(_ft_set_usb_params(handle, DWORD(65536), DWORD(65536)), 'FT_SetUSBParameters')
    _check_status(_ft_set_chars(handle, UCHAR(0), UCHAR(0), UCHAR(0), UCHAR(0)), 'FT_SetChars')
    _check_status(_ft_set_latency(handle, UCHAR(2)), 'FT_SetLatencyTimer')
    modem_status = DWORD()
    _check_status(_ft_get_modem_status(handle, ctypes.byref(modem_status)), 'FT_GetModemStatus')
    _check_status(_ft_purge(handle, FT_PURGE_RX | FT_PURGE_TX), 'FT_Purge')
    _check_status(_ft_set_timeouts(handle, DWORD(read_timeout), DWORD(write_timeout)), 'FT_SetTimeouts')

def apply_control_lines(handle: HANDLE, dtr: str, rts: str) -> None:
    toggled = False
    if dtr == 'set':
        _check_status(_ft_set_dtr(handle), 'FT_SetDtr')
        toggled = True
    elif dtr == 'clear':
        _check_status(_ft_clr_dtr(handle), 'FT_ClrDtr')
        toggled = True
    if rts == 'set':
        _check_status(_ft_set_rts(handle), 'FT_SetRts')
        toggled = True
    elif rts == 'clear':
        _check_status(_ft_clr_rts(handle), 'FT_ClrRts')
        toggled = True
    if toggled:
        _check_status(_ft_purge(handle, FT_PURGE_RX), 'FT_Purge_RX')
        _check_status(_ft_purge(handle, FT_PURGE_TX), 'FT_Purge_TX')

def _prepare_payloads(write_ascii: Optional[str], write_hex: Optional[str]) -> Iterable[bytes]:
    if write_ascii:
        yield write_ascii.encode('ascii')
    if write_hex:
        parts = re.split(r'[\s,]+', write_hex.strip())
        data = bytearray()
        for part in parts:
            if not part:
                continue
            data.append(int(part, 16))
        yield bytes(data)

def write_payloads(handle: HANDLE, payloads: Iterable[bytes]) -> int:
    total = 0
    for payload in payloads:
        if not payload:
            continue
        buffer = (ctypes.c_ubyte * len(payload))(*payload)
        written = DWORD()
        _check_status(_ft_write(handle, ctypes.byref(buffer), DWORD(len(payload)), ctypes.byref(written)), 'FT_Write')
        total += written.value
    return total



def _normalize_whitespace(text: str) -> str:
    if not text:
        return ''
    text = text.replace('\u00a0', ' ').replace('\u00b0', ' deg ')
    text = text.strip()
    return re.sub(r'\s+', ' ', text)


def _safe_float(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    try:
        candidate = text.replace(',', '.')
        return float(candidate)
    except (ValueError, AttributeError):
        return None


def _split_sections(segment: str) -> list[str]:
    if not segment:
        return []
    return [_normalize_whitespace(part) for part in segment.split('#') if part.strip()]


VALUE_UNIT_FIELDS = {
    'mv_rel': 'value_millivolts_relative',
    'mv': 'value_millivolts',
    'ma_rel': 'value_milliamps_relative',
    'ma': 'value_milliamps',
    'a': 'value_amperes',
    'v': 'value_volts',
    'ohm': 'value_ohms',
    'kohm': 'value_kilohms',
    'percent': 'value_percent',
    'ph': 'value_ph',
}

TEMP_UNIT_FIELDS = {
    'degc': 'temperature_celsius',
    'deg_c': 'temperature_celsius',
    'c': 'temperature_celsius',
    'degf': 'temperature_fahrenheit',
    'deg_f': 'temperature_fahrenheit',
    'f': 'temperature_fahrenheit',
    'k': 'temperature_kelvin',
}


def _unit_slug(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    normalized = _normalize_whitespace(text).lower()
    normalized = normalized.replace('\u00b0', 'deg').replace('%', 'percent')
    slug = re.sub(r'[^a-z0-9]+', '_', normalized).strip('_')
    return slug or None




def _extract_frames(buffer: bytearray) -> list[bytes]:
    frames: list[bytes] = []
    while True:
        if not buffer:
            break
        try:
            start = buffer.index(0x01)
        except ValueError:
            buffer.clear()
            break
        if start:
            del buffer[:start]
        try:
            end = buffer.index(0x03, 1)
        except ValueError:
            break
        finish = end + 1
        while finish < len(buffer) and buffer[finish] in (0x0d, 0x0a):
            finish += 1
        frame = bytes(buffer[:finish])
        del buffer[:finish]
        frames.append(frame)
    return frames


def _decode_frame(frame: bytes) -> dict:
    if not frame:
        raise ValueError('empty frame')
    core = frame.rstrip(CRLF_BYTES)
    if not core:
        raise ValueError('frame contained only whitespace')
    if core[0] != 0x01:
        raise ValueError('frame missing SOH')
    etx_index = core.rfind(0x03)
    if etx_index == -1:
        raise ValueError('frame missing ETX')
    payload = core[1:etx_index]
    text_content = payload.decode('latin-1', errors='replace')
    text_content = text_content.replace('\u00a0', ' ').replace('\r', '').replace('\n', '')
    header_text = text_content
    measurement_text = ''
    if CTRL_ETB in text_content:
        header_text, remainder = text_content.split(CTRL_ETB, 1)
        if CTRL_STX in remainder:
            _, remainder = remainder.split(CTRL_STX, 1)
        measurement_text = remainder
    if CTRL_RS in measurement_text:
        measurement_text = measurement_text.split(CTRL_RS, 1)[0]
    header_text = _normalize_whitespace(header_text)
    measurement_text = _normalize_whitespace(measurement_text)
    header_fields = _split_sections(header_text)
    measurement_fields = _split_sections(measurement_text)
    record = {
        'raw_hex': core.hex(),
        'header': {
            'raw': header_text,
            'fields': header_fields,
        },
        'measurement': {
            'raw': measurement_text,
            'fields': measurement_fields,
        },
    }
    header_info = record['header']
    if header_fields:
        first = header_fields[0]
        if 'S/N' in first:
            model, serial = first.split('S/N', 1)
            header_info['model'] = _normalize_whitespace(model)
            header_info['serial'] = serial.strip()
        else:
            header_info['model'] = first
    if len(header_fields) > 1:
        header_info['status'] = header_fields[1]
    if len(header_fields) > 2:
        header_info['range'] = header_fields[2]
    if len(header_fields) > 3:
        header_info['mode'] = header_fields[3]
    measurement_info = record['measurement']
    measurement_info['sequence'] = None
    measurement_info['value'] = None
    measurement_info['value_text'] = None
    measurement_info['value_unit'] = None
    measurement_info['value_unit_slug'] = None
    measurement_info['temperature'] = None
    measurement_info['temperature_text'] = None
    measurement_info['temperature_unit'] = None
    measurement_info['temperature_unit_slug'] = None
    if measurement_fields:
        first_field = measurement_fields[0]
        if ':' in first_field:
            measurement_info['sequence'] = first_field.split(':', 1)[1].strip()
        else:
            measurement_info['sequence'] = first_field
    if len(measurement_fields) > 1:
        value_text = _normalize_whitespace(measurement_fields[1])
        measurement_info['value_text'] = value_text
        value_parts = value_text.split(' ', 1)
        measurement_info['value'] = _safe_float(value_parts[0])
        unit_label = value_parts[1] if len(value_parts) > 1 else ''
        unit_label = _normalize_whitespace(unit_label)
        if unit_label:
            measurement_info['value_unit'] = unit_label
            measurement_info['unit'] = unit_label
            slug = _unit_slug(unit_label)
            if slug:
                measurement_info['value_unit_slug'] = slug
                alias = VALUE_UNIT_FIELDS.get(slug)
                if alias and measurement_info['value'] is not None:
                    measurement_info[alias] = measurement_info['value']
    if len(measurement_fields) > 2:
        temp_text = _normalize_whitespace(measurement_fields[2])
        measurement_info['temperature_text'] = temp_text
        temp_parts = temp_text.split(' ', 1)
        measurement_info['temperature'] = _safe_float(temp_parts[0])
        temp_unit = temp_parts[1] if len(temp_parts) > 1 else ''
        temp_unit = _normalize_whitespace(temp_unit)
        if temp_unit:
            measurement_info['temperature_unit'] = temp_unit
            slug = _unit_slug(temp_unit)
            if slug:
                measurement_info['temperature_unit_slug'] = slug
                alias = TEMP_UNIT_FIELDS.get(slug)
                if alias and measurement_info['temperature'] is not None:
                    measurement_info[alias] = measurement_info['temperature']
    if len(measurement_fields) > 3:
        measurement_info['date'] = measurement_fields[3]
    if len(measurement_fields) > 4:
        measurement_info['time'] = measurement_fields[4]
        date_value = measurement_info.get('date')
        if date_value:
            try:
                dt = datetime.strptime(f"{date_value} {measurement_info['time']}", '%d-%m-%Y %H:%M:%S')
                measurement_info['timestamp'] = dt.isoformat()
            except ValueError:
                pass
    if len(measurement_fields) > 5:
        measurement_info['extra_fields'] = measurement_fields[5:]
    return record


def read_stream(
    handle: HANDLE,
    duration: float,
    chunk: int,
    hex_dump: bool,
    log_path: Optional[str],
    poll_payload: Optional[bytes],
    poll_interval: float,
    frame_handler: Optional[Callable[[bytes], None]] = None,
    print_raw: bool = True,
) -> int:
    deadline = time.time() + duration
    buffer = (ctypes.c_ubyte * chunk)()
    transferred = DWORD()
    first = True
    total_bytes = 0
    log_file = None
    frame_buffer = bytearray()
    next_poll = time.time() if poll_payload else None
    effective_interval = poll_interval if poll_interval and poll_interval > 0 else 1.0
    try:
        if log_path:
            log_file = open(log_path, 'ab', buffering=0)
        while time.time() < deadline:
            now = time.time()
            if poll_payload and next_poll is not None and now >= next_poll:
                try:
                    write_payloads(handle, [poll_payload])
                except Exception as exc:
                    print(f'Warning: poll write failed: {exc}', file=sys.stderr)
                next_poll = now + effective_interval
                time.sleep(min(0.05, effective_interval / 4))
            transferred.value = 0
            status = _ft_read(handle, ctypes.byref(buffer), DWORD(chunk), ctypes.byref(transferred))
            if status != 0:
                raise RuntimeError(f'FT_Read failed with FT_STATUS={status}')
            if transferred.value:
                data = bytes(buffer[: transferred.value])
                total_bytes += len(data)
                if frame_handler:
                    frame_buffer.extend(data)
                    for frame in _extract_frames(frame_buffer):
                        frame_handler(frame)
                if hex_dump:
                    print(data.hex(' '))
                elif print_raw:
                    text = data.decode('latin-1')
                    end = '' if text.endswith('\n') else '\n'
                    try:
                        print(text, end=end)
                    except UnicodeEncodeError:
                        fallback = text.encode('ascii', 'replace').decode('ascii')
                        print(fallback, end=end)
                if log_file:
                    log_file.write(data)
                first = False
            else:
                if first:
                    queue = DWORD()
                    _check_status(_ft_queue_status(handle, ctypes.byref(queue)), 'FT_GetQueueStatus')
                    print(f'Waiting for data... (RX queue: {queue.value} bytes)')
                    first = False
                time.sleep(0.1)
    finally:
        if log_file:
            log_file.close()
    return total_bytes

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description='Interact with Elmetron CX-505 via FTDI D2XX driver')
    parser.add_argument('--list', action='store_true', help='List D2XX devices and exit')
    parser.add_argument('--index', type=int, default=0, help='Index of the FTDI device to use')
    parser.add_argument('--serial', type=str, help='Open device by serial number instead of index')
    parser.add_argument('--baud', type=int, default=9600, help='Baud rate to set (default: 9600)')
    parser.add_argument('--databits', type=int, default=8, choices=[7, 8], help='Number of data bits (default: 8)')
    parser.add_argument('--stopbits', type=float, default=1, choices=[1, 1.5, 2], help='Number of stop bits (default: 1)')
    parser.add_argument('--parity', type=str, default='N', help='Parity (N, O, E, M, S). Default: N')
    parser.add_argument('--duration', type=float, default=5.0, help='Seconds to read from the device (default: 5)')
    parser.add_argument('--chunk', type=int, default=256, help='Read chunk size in bytes (default: 256)')
    parser.add_argument('--hex', action='store_true', help='Print received bytes as hex strings')
    parser.add_argument('--timeouts', type=int, nargs=2, metavar=('READ_MS', 'WRITE_MS'), default=[500, 500], help='Read/write timeouts in ms (default: 500 500)')
    parser.add_argument('--dtr', choices=['set', 'clear', 'ignore'], default='set', help='Control DTR line (default: set)')
    parser.add_argument('--rts', choices=['set', 'clear', 'ignore'], default='set', help='Control RTS line (default: set)')
    parser.add_argument('--write', type=str, help='ASCII string to write before reading (e.g. "START\r\n")')
    parser.add_argument('--write-hex', type=str, help='Space or comma separated hex byte values to write before reading')
    parser.add_argument('--write-delay', type=float, default=0.2, help='Delay in seconds after sending data before reading')
    parser.add_argument('--poll-hex', type=str, help='Space or comma separated hex byte values to send periodically while reading')
    parser.add_argument('--poll-interval', type=float, default=1.0, help='Seconds between poll transmissions when --poll-hex is set (default: 1.0)')
    parser.add_argument('--no-read', action='store_true', help='Do not read; just perform the write and exit')
    parser.add_argument('--log', type=str, help='Append raw bytes to this file')
    parser.add_argument('--json', action='store_true', help='Decode CX-505 frames and print newline-delimited JSON to stdout')
    parser.add_argument('--json-out', type=str, help='Append decoded frames as JSON Lines to this file')
    args = parser.parse_args(argv)
    json_enabled = bool(args.json or args.json_out)

    if args.list:
        devices = enumerate_devices()
        if not devices:
            print('No FTDI D2XX devices found')
        else:
            print(f'Found {len(devices)} device(s):')
            for idx, info in enumerate(devices):
                print(f"[{idx}] {info['description'] or '<no description>'} (S/N {info['serial'] or '<unknown>'}) Flags=0x{info['flags']:08X} Type={info['type']} LocId=0x{info['loc_id']:08X} ID=0x{info['id']:08X}")
        return 0

    handle = None
    json_file = None
    frame_handler = None
    try:
        devices = enumerate_devices()
        if args.serial:
            target_serial = args.serial
        else:
            if args.index >= len(devices):
                raise IndexError(f'Device index {args.index} is out of range (found {len(devices)} device(s))')
            target_serial = devices[args.index]['serial']
        description = None
        if args.serial:
            description = next((d['description'] for d in devices if d['serial'] == args.serial), None)
        else:
            description = devices[args.index]['description']
        label = args.serial if args.serial else str(args.index)
        print(f"Opening device {label}: {description or '<no description>'} (S/N {target_serial or '<unknown>'})")
        handle = open_device(args.index if not args.serial else 0, args.serial)
        configure_device(handle, args.baud, args.databits, args.stopbits, args.parity, args.timeouts[0], args.timeouts[1])
        apply_control_lines(handle, args.dtr, args.rts)

        poll_payload = None

        if args.poll_hex:
            poll_candidates = list(_prepare_payloads(None, args.poll_hex))
            if len(poll_candidates) != 1:
                raise ValueError('--poll-hex expects exactly one payload')
            poll_payload = poll_candidates[0]
            if not poll_payload:
                raise ValueError('--poll-hex payload must include at least one byte')

        if args.json_out and json_file is None:
            json_file = open(args.json_out, 'a', encoding='utf-8')

        if json_enabled:
            def _emit_json(record: dict) -> None:
                line = json.dumps(record, ensure_ascii=False)
                if args.json:
                    print(line)
                if json_file:
                    json_file.write(line + '\n')
                    json_file.flush()

            def frame_handler_inner(frame_bytes: bytes) -> None:
                try:
                    record = _decode_frame(frame_bytes)
                except Exception as exc:
                    print(f'Warning: failed to decode frame: {exc}', file=sys.stderr)
                    return
                _emit_json(record)

            frame_handler = frame_handler_inner

        payloads = list(_prepare_payloads(args.write, args.write_hex))
        if payloads:
            written = write_payloads(handle, payloads)
            print(f'Sent {written} byte(s) to device')
            if args.write_delay > 0:
                time.sleep(args.write_delay)
        if args.no_read:
            return 0
        print(f'Reading for {args.duration} second(s)...')
        print_raw = not (json_enabled and not args.hex)
        total = read_stream(handle, args.duration, args.chunk, args.hex, args.log, poll_payload, args.poll_interval, frame_handler, print_raw)
        print(f'Finished: received {total} byte(s)')
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    finally:
        if handle:
            try:
                close_device(handle)
            except Exception as exc:
                print(f'Warning: failed to close device cleanly: {exc}', file=sys.stderr)
        if json_file:
            try:
                json_file.close()
            except Exception as exc:
                print(f'Warning: failed to close JSON log: {exc}', file=sys.stderr)
    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))

