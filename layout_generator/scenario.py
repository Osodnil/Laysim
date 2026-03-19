from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict

import numpy as np

from .config import GeneratorConfig
from .models import LayoutMetrics


@dataclass
class Scenario:
    """
    Stable container for future integration with simulation/optimization.

    - `grid` is kept as numpy array so a future simulator can read it directly.
    - `metrics` and `config` are kept as plain dataclass objects for easy serialization.
    """

    id: int
    config: GeneratorConfig
    grid: np.ndarray
    metrics: LayoutMetrics

    def to_report_row(self) -> Dict[str, Any]:
        row = {
            "id": int(self.id),
            "score": float(self.metrics.score),
            "distance_avg": float(self.metrics.distance_avg),
            "capacity_racks": int(self.metrics.capacity_racks),
            "connectivity_ratio": float(self.metrics.connectivity_ratio),
        }
        # Flatten config into the same CSV row (useful for later analysis).
        row.update(asdict(self.config))
        return row

    def save_grid_npy(self, filename: str) -> None:
        np.save(filename, self.grid)

