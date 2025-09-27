"""Ingestion pipeline that decodes frames and persists them."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from ..analytics.engine import AnalyticsEngine
from ..config import IngestionConfig
from ..storage.database import DeviceMetadata, SessionHandle

import cx505_d2xx


class FrameIngestor:
    """Decode CX-505 frames and push them into the storage layer."""

    def __init__(self, config: IngestionConfig, session: SessionHandle, analytics: Optional[AnalyticsEngine] = None):
        self._config = config
        self._session = session
        self._analytics = analytics
        self._frames = 0

    @property
    def frames(self) -> int:
        return self._frames

    def handle_frame(self, frame: bytes) -> Optional[Dict[str, Any]]:
        captured_at = datetime.utcnow()
        try:
            decoded = cx505_d2xx._decode_frame(frame)  # pylint: disable=protected-access
        except Exception as exc:  # pylint: disable=broad-except
            self._session.log_event(
                'warning',
                'decode',
                'Failed to decode frame',
                {
                    'error': str(exc),
                    'frame_hex': frame.hex(),
                },
            )
            return None

        header = decoded.get('header', {})
        candidate_serial = header.get('serial') or self._session.metadata.serial
        candidate_model = header.get('model') or self._session.metadata.model
        candidate_description = (
            self._session.metadata.description
            or candidate_model
            or header.get('raw')
        )
        device_meta = DeviceMetadata(
            serial=candidate_serial,
            description=candidate_description,
            model=candidate_model,
        )
        if device_meta != self._session.metadata:
            self._session.update_instrument(device_meta)
            self._session.set_metadata(
                {
                    'device.serial': device_meta.serial,
                    'device.model': device_meta.model,
                    'device.description': device_meta.description,
                }
            )

        if self._config.enrich_with_timestamp:
            decoded['captured_at'] = captured_at.isoformat(timespec='milliseconds') + 'Z'
        if self._config.annotate_device:
            decoded.setdefault('device', {})
            decoded['device'].update(
                {
                    'serial': device_meta.serial,
                    'description': device_meta.description,
                    'model': device_meta.model,
                }
            )
        if self._config.emit_raw_frame:
            decoded['raw_frame_hex'] = frame.hex()

        if self._analytics:
            analytics_payload = self._analytics.process(decoded)
            if analytics_payload:
                decoded['analytics'] = analytics_payload
        else:
            analytics_payload = None

        storage_result = self._session.store_capture(
            captured_at,
            frame,
            decoded,
            derived_metrics=analytics_payload,
        )
        decoded.setdefault('storage', {})
        decoded['storage']['frame_id'] = storage_result.frame_id
        decoded['storage']['measurement_id'] = storage_result.measurement_id
        decoded['storage']['session_id'] = self._session.id
        decoded['storage']['captured_at'] = captured_at.isoformat(timespec='milliseconds') + 'Z'

        self._frames += 1
        return decoded
