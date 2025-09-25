import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import cx505_d2xx

DEFAULT_POLL_HEX = "01 23 30 23 30 23 30 23 03"


def _ensure_poll_payload(hex_string: str) -> bytes:
    payloads = list(cx505_d2xx._prepare_payloads(None, hex_string))
    if len(payloads) != 1 or not payloads[0]:
        raise ValueError('Poll payload must contain exactly one non-empty frame')
    return payloads[0]


def _open_device(index: int, baud: int, databits: int, stopbits: float, parity: str, timeouts: tuple[int, int]) -> cx505_d2xx.HANDLE:
    handle = cx505_d2xx.open_device(index)
    cx505_d2xx.configure_device(handle, baud, databits, stopbits, parity, timeouts[0], timeouts[1])
    cx505_d2xx.apply_control_lines(handle, 'set', 'set')
    return handle


def main() -> int:
    parser = argparse.ArgumentParser(description='Continuous capture service for the Elmetron CX-505 meter')
    parser.add_argument('--output', type=Path, default=Path('captures/cx505_capture.jsonl'), help='JSON Lines file to append decoded frames to (default: captures/cx505_capture.jsonl)')
    parser.add_argument('--device-index', type=int, default=0, help='Index of the FTDI device to use (default: 0)')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate (default: 115200)')
    parser.add_argument('--databits', type=int, choices=[7, 8], default=8, help='Data bits (default: 8)')
    parser.add_argument('--stopbits', type=float, choices=[1.0, 1.5, 2.0], default=2.0, help='Stop bits (default: 2.0)')
    parser.add_argument('--parity', type=str, choices=list('NOEMS'), default='E', help='Parity (default: E)')
    parser.add_argument('--timeouts', type=int, nargs=2, metavar=('READ_MS', 'WRITE_MS'), default=[500, 500], help='Read/write timeouts in ms (default: 500 500)')
    parser.add_argument('--chunk', type=int, default=256, help='Read chunk size in bytes (default: 256)')
    parser.add_argument('--window', type=float, default=10.0, help='Seconds per capture window (default: 10)')
    parser.add_argument('--poll-hex', type=str, default=DEFAULT_POLL_HEX, help='Hex encoded poll frame (default: CX-505 handshake request)')
    parser.add_argument('--poll-interval', type=float, default=1.0, help='Seconds between poll transmissions (default: 1.0)')
    parser.add_argument('--idle', type=float, default=0.0, help='Seconds to sleep between windows (default: 0)')
    parser.add_argument('--status-every', type=float, default=30.0, help='Print progress every N seconds (0 disables)')
    parser.add_argument('--restart-delay', type=float, default=2.0, help='Seconds to wait before reconnecting after failure (default: 2)')
    parser.add_argument('--max-runtime', type=float, default=0.0, help='Stop after N seconds (0 keeps running)')
    parser.add_argument('--quiet', action='store_true', help='Suppress status messages')
    args = parser.parse_args()

    if args.window <= 0:
        raise SystemExit('Capture window must be positive')
    if args.poll_interval <= 0:
        raise SystemExit('Poll interval must be positive')
    if args.restart_delay < 0:
        raise SystemExit('Restart delay cannot be negative')

    output_path = args.output.expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    poll_payload = _ensure_poll_payload(args.poll_hex)

    devices = cx505_d2xx.enumerate_devices()
    if not devices:
        raise SystemExit('No FTDI D2XX devices detected')
    if args.device_index >= len(devices):
        raise SystemExit(f'Device index {args.device_index} out of range (found {len(devices)} device(s))')
    device_info = devices[args.device_index]

    if not args.quiet:
        description = device_info['description'] or '<no description>'
        serial = device_info['serial'] or '<unknown>'
        print(f'Starting capture on index {args.device_index}: {description} (S/N {serial})')

    stats = {'frames': 0}
    start_time = time.time()
    next_status = start_time + args.status_every if args.status_every > 0 else None
    handle = None
    json_file = output_path.open('a', encoding='utf-8')

    def handle_frame(frame_bytes: bytes) -> None:
        try:
            record = cx505_d2xx._decode_frame(frame_bytes)
        except Exception as exc:  # pylint: disable=broad-except
            if not args.quiet:
                print(f'Warning: failed to decode frame: {exc}')
            return
        record['captured_at'] = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
        record['device'] = {
            'serial': device_info['serial'],
            'description': device_info['description'],
        }
        record['frame_index'] = stats['frames'] + 1
        json_file.write(json.dumps(record, ensure_ascii=False))
        json_file.write(chr(10))
        json_file.flush()
        stats['frames'] += 1
        json_file.flush()
        stats['frames'] += 1

    def close_handle() -> None:
        nonlocal handle
        if handle:
            try:
                cx505_d2xx.close_device(handle)
            except Exception:  # pylint: disable=broad-except
                pass
            handle = None

    try:
        while True:
            if args.max_runtime > 0 and time.time() - start_time >= args.max_runtime:
                if not args.quiet:
                    print('Max runtime reached, stopping capture.')
                break
            if handle is None:
                try:
                    handle = _open_device(args.device_index, args.baud, args.databits, args.stopbits, args.parity, tuple(args.timeouts))
                    cx505_d2xx.write_payloads(handle, [poll_payload])
                    if not args.quiet:
                        print('Link opened.')
                except Exception as exc:  # pylint: disable=broad-except
                    close_handle()
                    if not args.quiet:
                        print(f'Warning: failed to open device: {exc}. Retrying in {args.restart_delay}s')
                    time.sleep(max(args.restart_delay, 0.5))
                    continue
            try:
                cx505_d2xx.read_stream(handle, args.window, args.chunk, False, None, poll_payload, args.poll_interval, handle_frame, False)
            except KeyboardInterrupt:
                if not args.quiet:
                    print('Interrupted by user. Stopping capture.')
                break
            except Exception as exc:  # pylint: disable=broad-except
                if not args.quiet:
                    print(f'Warning: capture window failed: {exc}. Restarting link.')
                close_handle()
                time.sleep(max(args.restart_delay, 0.5))
                continue
            if args.status_every > 0 and not args.quiet and time.time() >= next_status:
                print(f'Stored {stats["frames"]} frame(s) to {output_path}')
                next_status = time.time() + args.status_every
            if args.idle > 0:
                time.sleep(args.idle)
    finally:
        close_handle()
        json_file.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

