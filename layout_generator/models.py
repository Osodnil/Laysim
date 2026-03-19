from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class LayoutMetrics:
    score: float
    distance_avg: float
    capacity_racks: int
    connectivity_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

