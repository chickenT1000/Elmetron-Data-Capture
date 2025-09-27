import pytest

import cx505_d2xx


CTRL_ETB = '\x17'
CTRL_STX = '\x02'
CTRL_RS = '\x1e'
CTRL_SOH = '\x01'
CTRL_ETX = '\x03'


def _build_frame(header: str, measurement: str, extra: str = '') -> bytes:
    payload = ''.join([
        CTRL_SOH,
        header,
        CTRL_ETB,
        CTRL_STX,
        measurement,
        CTRL_RS,
        extra,
        CTRL_ETX,
    ])
    return payload.encode('ascii') + b'\r\n'


def test_decode_frame_parses_measurement_sections():
    header = '#CX-505 S/N 12345#READY#RANGE#PH'
    measurement = '#001# 7.123 pH# 24.7 C# 25-09-2025# 12:34:56'
    frame = _build_frame(header, measurement, extra='ignored')

    record = cx505_d2xx._decode_frame(frame)

    header_info = record['header']
    assert header_info['model'] == 'CX-505'
    assert header_info['serial'] == '12345'
    assert header_info['status'] == 'READY'

    measurement_info = record['measurement']
    assert measurement_info['sequence'] == '001'
    assert measurement_info['value'] == pytest.approx(7.123)
    assert measurement_info['value_ph'] == pytest.approx(7.123)
    assert measurement_info['value_unit'] == 'pH'
    assert measurement_info['temperature'] == pytest.approx(24.7)
    assert measurement_info['temperature_celsius'] == pytest.approx(24.7)
    assert measurement_info['temperature_unit'] == 'C'
    assert measurement_info['timestamp'] == '2025-09-25T12:34:56'
    assert measurement_info.get('extra_fields') is None


def test_decode_frame_rejects_frames_without_soh():
    with pytest.raises(ValueError):
        cx505_d2xx._decode_frame(b'#001# 7.123 pH# 24.7 C# 25-09-2025# 12:34:56\x03\r\n')
