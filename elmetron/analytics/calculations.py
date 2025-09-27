"""Analytical helpers for derived metrics."""
from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import Iterable, Optional


def moving_average(values: Iterable[float], window: int) -> Optional[float]:
    """Return the arithmetic mean over the last *window* elements."""

    values = [value for value in values if math.isfinite(value)][-window:]
    if not values:
        return None
    return sum(values) / len(values)


def stability_index(values: Iterable[float]) -> Optional[float]:
    """Return a normalised stability metric (coefficient of variation)."""

    filtered = [value for value in values if math.isfinite(value)]
    if len(filtered) < 2:
        return None
    average = mean(filtered)
    variation = pstdev(filtered)
    if math.isclose(average, 0.0, abs_tol=1e-9):
        return variation
    return variation / abs(average)


def temperature_compensate(value: float, temperature: float, coefficient: float, reference_temperature: float = 25.0) -> float:
    """Apply linear temperature compensation to *value* using *coefficient*."""

    delta = temperature - reference_temperature
    return value + coefficient * delta


def ph_temperature_compensation(ph_value: float, temperature: float, reference_temperature: float = 25.0) -> float:
    """Compensate a pH reading based on temperature relative to reference."""

    # Nernst slope approximation for pH electrodes: -0.03 pH/?C around 25?C
    slope = -0.03
    delta = temperature - reference_temperature
    return ph_value + slope * delta
