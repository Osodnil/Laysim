from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GeneratorConfig:
    # Grid size (in cells)
    width: int = 50
    height: int = 30

    # Scenario generation
    n_layouts: int = 30
    top_k: int = 5
    seed: Optional[int] = None

    # Dock placement
    n_docks: int = 5
    dock_blocks: int = 2  # how many groups of dock positions

    # Corridor generation (aim: dense enough to have meaningful rack access)
    # Corridor lines are 1-cell thick in this discrete model.
    vertical_corridor_step_min: int = 2
    vertical_corridor_step_max: int = 3
    horizontal_corridor_step_min: int = 2
    horizontal_corridor_step_max: int = 3

    # Zones (simple heuristic)
    picking_ratio: float = 0.25  # bottom portion considered "picking"
    rack_prob_picking: float = 0.70
    rack_prob_storage: float = 0.95

    # Scoring weights (lower score is better)
    w_distance: float = 1.0
    w_capacity: float = 1.0
    w_connectivity: float = 2.0

    # DXF cell size scaling
    cell_size: float = 1.0

