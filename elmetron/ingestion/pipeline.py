"""Ingestion pipeline that decodes frames and persists them."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Optional

from ..analytics.engine import AnalyticsEngine
from ..config import IngestionConfig
from ..storage.database import DeviceMetadata, SessionHandle

import cx505_d2xx


class FrameIngestor:
    """Decode CX-505 frames and push them into the storage layer."""

    def __init__(
        self,
        config: IngestionConfig,
        session: SessionHandle,
        analytics: Optional[AnalyticsEngine] = None,
        *,
        decode_error_callback: Optional[Callable[[bytes, Exception], None]] = None,
        session_buffer: Optional[object] = None,
    ) -> None:
        self._config = config
        self._session = session
        self._analytics = analytics
        self._decode_error_callback = decode_error_callback
        self._session_buffer = session_buffer
        self._frames = 0
        self._analytics_profile: Optional[Dict[str, object]] = None

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
            if self._decode_error_callback:
                try:
                    self._decode_error_callback(frame, exc)
                except Exception:  # pragma: no cover - defensive
                    pass
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
            self._analytics_profile = self._analytics.profile_summary()
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

        # Write to crash-resistant buffer
        if self._session_buffer is not None:
            try:
                self._session_buffer.append_measurement(
                    captured_at=captured_at,
                    raw_frame=frame.hex(),
                    decoded=decoded,
                    derived_metrics=analytics_payload,
                )
            except Exception:  # pragma: no cover - defensive
                pass  # Don't fail capture if buffer write fails
        decoded['storage']['measurement_id'] = storage_result.measurement_id
        decoded['storage']['session_id'] = self._session.id
        decoded['storage']['captured_at'] = captured_at.isoformat(timespec='milliseconds') + 'Z'

        self._frames += 1
        return decoded

    @property
    def analytics_profile(self) -> Optional[Dict[str, object]]:
        if self._analytics is None:
            return None
        if self._analytics_profile is None:
            self._analytics_profile = self._analytics.profile_summary()
        return self._analytics_profile
