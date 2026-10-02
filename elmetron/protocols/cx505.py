"""Pure CX-505 frame decoding; no driver or hardware access."""

from __future__ import annotations

import re

from datetime import datetime

from typing import Optional

CTRL_SOH = '\x01'
CTRL_STX = '\x02'
CTRL_ETX = '\x03'
CTRL_ETB = '\x17'
CTRL_RS = '\x1e'
CRLF_BYTES = b'\r\n'

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

decode_frame = _decode_frame
extract_frames = _extract_frames
