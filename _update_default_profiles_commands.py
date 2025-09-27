from pathlib import Path

path = Path("elmetron/protocols/registry.py")
text = path.read_text(encoding="ascii")
old_cx505 = "        \"chunk_size\": 256,\r\n    },\r\n"
new_cx505 = "        \"chunk_size\": 256,\r\n        \"commands\": {\r\n            \"calibrate_ph7\": {\r\n                \"description\": \"Request pH 7 calibration (CX-505).\",\r\n                \"write_hex\": \"02 43 41 4C 37 03\",\r\n                \"post_delay_s\": 0.5,\r\n                \"read_duration_s\": 2.0,\r\n                \"expect_hex\": \"01\"\r\n            }\r\n        },\r\n    },\r\n"
if old_cx505 not in text:
    raise SystemExit('cx505 block not found')
text = text.replace(old_cx505, new_cx505, 1)
old_cx705 = "        \"chunk_size\": 128,\r\n    },\r\n"
new_cx705 = "        \"chunk_size\": 128,\r\n        \"commands\": {\r\n            \"start_logging\": {\r\n                \"description\": \"Begin streaming dissolved oxygen measurements.\",\r\n                \"write_ascii\": \"START\\r\\n\",\r\n                \"post_delay_s\": 0.2,\r\n                \"read_duration_s\": 3.0\r\n            }\r\n        },\r\n    },\r\n"
if old_cx705 not in text:
    raise SystemExit('cx705 block not found')
text = text.replace(old_cx705, new_cx705, 1)
old_ble = "        \"handshake\": \"connect\",\r\n        \"poll_interval_s\": 5.0,\r\n    },\r\n"
new_ble = "        \"handshake\": \"connect\",\r\n        \"poll_interval_s\": 5.0,\r\n        \"commands\": {\r\n            \"sync_time\": {\r\n                \"description\": \"Request BLE bridge to synchronise its clock.\",\r\n                \"write_ascii\": \"SYNC\\n\",\r\n                \"read_duration_s\": 1.0\r\n            }\r\n        },\r\n    },\r\n"
if old_ble not in text:
    raise SystemExit('ph_ble block not found')
text = text.replace(old_ble, new_ble, 1)
path.write_text(text, encoding='ascii')
