"""Session-scoped analytics engine for derived metrics."""
from __future__ import annotations

from collections import defaultdict, deque
from typing import DefaultDict, Deque, Dict, Optional

from ..config import AnalyticsConfig
from .calculations import (
    moving_average,
    ph_temperature_compensation,
    stability_index,
    temperature_compensate,
)


class AnalyticsEngine:
    """Compute derived metrics for sequential measurement samples."""

    def __init__(self, config: AnalyticsConfig):
        self._config = config
        self._histories: DefaultDict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=config.max_history),
        )

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

        unit = (
            (measurement.get("value_unit") if isinstance(measurement, dict) else None)
            or (measurement.get("unit") if isinstance(measurement, dict) else None)
            or decoded_frame.get("unit")
            or ""
        )
        unit_key = str(unit).lower() if unit else "default"

        history = self._history(unit_key)
        history.append(numeric_value)

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

        return metrics if len(metrics) > 1 else None
