from __future__ import annotations

from collections import deque
from typing import Tuple

import numpy as np

from .cell_types import CORRIDOR, DOCK, RACK
from .config import GeneratorConfig
from .models import LayoutMetrics


def _bfs_dist_from_docks(grid: np.ndarray) -> np.ndarray:
    """
    Multi-source BFS on walkable cells (CORRIDOR + DOCK).
    Returns distance array with np.inf for unreachable cells.
    """
    walkable = (grid == CORRIDOR) | (grid == DOCK)
    docks = np.argwhere(grid == DOCK)

    h, w = grid.shape
    dist = np.full((h, w), np.inf, dtype=float)
    q: deque[Tuple[int, int]] = deque()

    for y, x in docks:
        dist[int(y), int(x)] = 0.0
        q.append((int(y), int(x)))

    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if not (0 <= ny < h and 0 <= nx < w):
                continue
            if not walkable[ny, nx]:
                continue
            nd = dist[y, x] + 1.0
            if nd < dist[ny, nx]:
                dist[ny, nx] = nd
                q.append((ny, nx))

    return dist


def calculate_distance_score(grid: np.ndarray) -> float:
    """
    Distance score = average shortest corridor-distance to access racks.

    For each rack, we look at its 4-neighborhood:
    - if any neighbor walkable cell (corridor/dock) is reachable from docks,
      use the minimum BFS distance to that neighbor + 1 (step into rack access).
    - unreachable racks are ignored; if none are reachable, distance is +inf.
    """
    dist = _bfs_dist_from_docks(grid)
    walkable = np.isfinite(dist)
    docks_exist = np.any(grid == DOCK)
    racks = np.argwhere(grid == RACK)
    if not docks_exist or len(racks) == 0:
        return float("inf")

    h, w = grid.shape
    total = 0.0
    reachable = 0

    for y, x in racks:
        best = np.inf
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = int(y) + dy, int(x) + dx
            if 0 <= ny < h and 0 <= nx < w and walkable[ny, nx]:
                best = min(best, dist[ny, nx] + 1.0)
        if np.isfinite(best):
            total += float(best)
            reachable += 1

    if reachable == 0:
        return float("inf")
    return total / reachable


def calculate_capacity_score(grid: np.ndarray) -> int:
    return int(np.sum(grid == RACK))


def calculate_connectivity_ratio(grid: np.ndarray) -> float:
    """
    Ratio of racks that have at least one reachable walkable 4-neighbor.
    """
    dist = _bfs_dist_from_docks(grid)
    walkable = np.isfinite(dist)
    racks = np.argwhere(grid == RACK)
    if len(racks) == 0:
        return 0.0

    h, w = grid.shape
    reachable = 0
    for y, x in racks:
        ok = False
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = int(y) + dy, int(x) + dx
            if 0 <= ny < h and 0 <= nx < w and walkable[ny, nx]:
                ok = True
                break
        if ok:
            reachable += 1

    return reachable / len(racks)


def score_layout(grid: np.ndarray, config: GeneratorConfig) -> LayoutMetrics:
    """
    Lower is better.

    score =
      w_distance * distance_norm
      - w_capacity * capacity_norm
      - w_connectivity * connectivity_norm
    """
    distance_avg = calculate_distance_score(grid)
    capacity_racks = calculate_capacity_score(grid)
    connectivity_ratio = calculate_connectivity_ratio(grid)

    # Distance dominates less if no racks are reachable.
    if not np.isfinite(distance_avg):
        return LayoutMetrics(
            score=float("inf"),
            distance_avg=float("inf"),
            capacity_racks=capacity_racks,
            connectivity_ratio=connectivity_ratio,
        )

    # Normalizations to make weights more stable across grid sizes.
    denom_dist = float(config.width + config.height)
    distance_norm = distance_avg / max(1.0, denom_dist)

    denom_cap = float(config.width * config.height)
    capacity_norm = float(capacity_racks) / max(1.0, denom_cap)

    connectivity_norm = float(connectivity_ratio)

    score = (
        config.w_distance * distance_norm
        - config.w_capacity * capacity_norm
        - config.w_connectivity * connectivity_norm
    )

    return LayoutMetrics(
        score=float(score),
        distance_avg=float(distance_avg),
        capacity_racks=int(capacity_racks),
        connectivity_ratio=float(connectivity_ratio),
    )

