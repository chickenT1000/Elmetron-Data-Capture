"""Session-scoped analytics engine for derived metrics."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from typing import DefaultDict, Deque, Dict, Optional

from ..config import AnalyticsConfig
from .calculations import (
    moving_average,
    ph_temperature_compensation,
    stability_index,
    temperature_compensate,
)


@dataclass(slots=True)
class AnalyticsProfile:
    """Aggregate profiling metrics for analytics processing."""

    frames_processed: int = 0
    throttled_frames: int = 0
    total_processing_time_s: float = 0.0
    max_processing_time_s: float = 0.0
    last_processing_time_s: float = 0.0
    current_rate_per_minute: float = 0.0
    last_throttled_at: Optional[float] = None

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            'frames_processed': self.frames_processed,
            'throttled_frames': self.throttled_frames,
            'current_rate_per_minute': round(self.current_rate_per_minute, 3),
        }
        if self.frames_processed > 0 and self.total_processing_time_s > 0:
            average = self.total_processing_time_s / self.frames_processed
            payload['average_processing_time_ms'] = round(average * 1000, 3)
        if self.max_processing_time_s > 0:
            payload['max_processing_time_ms'] = round(self.max_processing_time_s * 1000, 3)
        if self.last_processing_time_s > 0:
            payload['last_processing_time_ms'] = round(self.last_processing_time_s * 1000, 3)
        if self.last_throttled_at is not None:
            payload['last_throttled_at'] = datetime.utcfromtimestamp(self.last_throttled_at).isoformat() + 'Z'
        return payload


class AnalyticsEngine:
    """Compute derived metrics for sequential measurement samples."""

    def __init__(self, config: AnalyticsConfig):
        self._config = config
        self._histories: DefaultDict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=config.max_history),
        )
        self._recent_samples: Deque[float] = deque()
        self._rate_window_s = 60.0
        self._profiling_enabled = config.profiling_enabled
        self._profile = AnalyticsProfile()

    def reset(self) -> None:
        """Reset accumulated histories."""

        self._histories.clear()

    def _history(self, unit_key: str) -> Deque[float]:
        return self._histories[unit_key]

    def process(self, decoded_frame: Dict[str, object]) -> Optional[Dict[str, object]]:
        """Process a decoded frame and return derived metrics payload."""

        if not self._config.enabled:
            return None

        measurement = decoded_frame.get("measurement") or {}
        value = measurement.get("value") if isinstance(measurement, dict) else None
        if value is None:
            return None
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return None

        now = time.monotonic()
        recent = self._recent_samples
        while recent and now - recent[0] > self._rate_window_s:
            recent.popleft()
        limit = self._config.max_frames_per_minute
        if limit and len(recent) >= limit:
            self._profile.throttled_frames += 1
            self._profile.last_throttled_at = time.time()
            window = min(now - recent[0], self._rate_window_s) if recent else 1.0
            rate = len(recent) * 60.0 / max(window, 1e-6)
            self._profile.current_rate_per_minute = rate
            return {
                'throttled': True,
                'current_rate_per_minute': round(rate, 3),
            }

        recent.append(now)
        window = min(now - recent[0], self._rate_window_s) if recent else self._rate_window_s
        self._profile.current_rate_per_minute = len(recent) * 60.0 / max(window, 1e-6)

        unit = (
            (measurement.get("value_unit") if isinstance(measurement, dict) else None)
            or (measurement.get("unit") if isinstance(measurement, dict) else None)
            or decoded_frame.get("unit")
            or ""
        )
        unit_key = str(unit).lower() if unit else "default"

        history = self._history(unit_key)
        history.append(numeric_value)

        start = time.perf_counter() if self._profiling_enabled else None

        metrics: Dict[str, object] = {"unit": unit or None, "samples_tracked": len(history)}

        ma_window = self._config.moving_average_window
        if ma_window > 0 and len(history) >= ma_window:
            metrics["moving_average"] = moving_average(history, ma_window)

        stability_window = self._config.stability_window
        if stability_window > 1 and len(history) >= 2:
            recent = list(history)[-stability_window:]
            stability = stability_index(recent)
            if stability is not None:
                metrics["stability_index"] = stability

        temperature = None
        if isinstance(measurement, dict):
            temperature = measurement.get("temperature")
            if temperature is None:
                temperature = measurement.get("temperature_c")
        if temperature is None:
            temperature = decoded_frame.get("temperature")
        try:
            temperature_value = float(temperature) if temperature is not None else None
        except (TypeError, ValueError):
            temperature_value = None

        if temperature_value is not None:
            compensation_payload: Dict[str, object] = {
                "measured_value": numeric_value,
                "measured_temperature": temperature_value,
                "reference_temperature": self._config.reference_temperature,
            }
            if unit_key == "ph":
                compensation_payload["method"] = "ph_slope"
                compensation_payload["compensated_value"] = ph_temperature_compensation(
                    numeric_value,
                    temperature_value,
                    reference_temperature=self._config.reference_temperature,
                )
            elif self._config.temperature_coefficient:
                compensation_payload["method"] = "linear"
                compensation_payload["coefficient"] = self._config.temperature_coefficient
                compensation_payload["compensated_value"] = temperature_compensate(
                    numeric_value,
                    temperature_value,
                    coefficient=self._config.temperature_coefficient,
                    reference_temperature=self._config.reference_temperature,
                )
            if "compensated_value" in compensation_payload:
                metrics["temperature_compensation"] = compensation_payload

        self._profile.frames_processed += 1

        if start is not None:
            duration = time.perf_counter() - start
            self._profile.total_processing_time_s += duration
            self._profile.last_processing_time_s = duration
            if duration > self._profile.max_processing_time_s:
                self._profile.max_processing_time_s = duration
            profiling_payload = {
                'processing_time_ms': round(duration * 1000, 3),
                'rolling_rate_per_minute': round(self._profile.current_rate_per_minute, 3),
            }
            metrics['profiling'] = profiling_payload

        return metrics if len(metrics) > 1 else None

    def profile_summary(self) -> Dict[str, object]:
        """Return a snapshot of accumulated profiling metrics."""

        return self._profile.to_dict()
