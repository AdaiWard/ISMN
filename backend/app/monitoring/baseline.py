from __future__ import annotations

import statistics
from dataclasses import dataclass


@dataclass(slots=True)
class BaselineResult:
    ready: bool
    median: float | None
    deviation_percent: float | None
    anomalous: bool
    explanation: str


def evaluate_moving_baseline(values: list[float], current: float, minimum_samples: int = 10, deviation_ratio: float = 2.0) -> BaselineResult:
    if len(values) < minimum_samples:
        return BaselineResult(False, None, None, False, "Недостаточно данных для базовой линии")
    median = statistics.median(values[-50:])
    if median <= 0:
        return BaselineResult(True, median, None, False, "Нулевая базовая линия; отклонение не вычисляется")
    deviation = (current - median) * 100.0 / median
    anomalous = current > median * deviation_ratio
    explanation = f"Текущее значение {current:.1f}, медиана {median:.1f}, отклонение {deviation:.1f}%"
    return BaselineResult(True, median, deviation, anomalous, explanation)

