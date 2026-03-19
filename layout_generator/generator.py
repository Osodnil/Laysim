from __future__ import annotations

from collections import deque
from typing import List, Optional, Sequence, Tuple

import numpy as np

from .cell_types import CORRIDOR, DOCK, EMPTY, RACK
from .config import GeneratorConfig


def _choose_line_positions(
    length: int,
    step_min: int,
    step_max: int,
    rng: np.random.Generator,
    required_positions: Optional[Sequence[int]] = None,
) -> List[int]:
    """
    Pick discrete "lines" at 1-cell thickness.

    We start from a random offset and step forward with a random stride between
    [step_min, step_max]. Required positions are appended and later deduplicated.
    """
    if length <= 0:
        return []

    required_positions = list(required_positions or [])

    # Choose a random start so layouts diversify.
    start = int(rng.integers(0, max(1, step_max)))
    positions = [start]
    cur = start
    while cur + step_min < length:
        stride = int(rng.integers(step_min, step_max + 1))
        cur = cur + stride
        if cur >= length:
            break
        positions.append(cur)

    positions.extend(required_positions)
    positions = sorted(set(positions))

    # Clamp to valid range
    positions = [p for p in positions if 0 <= p < length]
    return positions


def _choose_dock_positions_from_corridors(
    corridor_columns: Sequence[int],
    n_docks: int,
    n_blocks: int,
    rng: np.random.Generator,
) -> List[int]:
    """
    Dock positions are chosen from corridor columns and grouped into blocks.
    """
    corridor_columns = sorted(corridor_columns)
    if not corridor_columns:
        return []

    n_blocks = int(np.clip(n_blocks, 1, n_docks))

    # Choose block sizes that sum to n_docks.
    # Example for n_blocks=2: [2, 3]
    raw_sizes = rng.multinomial(n_docks, [1 / n_blocks] * n_blocks).tolist()

    # Convert block sizes to dock positions by selecting consecutive items inside corridor_columns.
    # If corridor_columns is too short, we sample with replacement as a fallback.
    if sum(raw_sizes) != n_docks:
        raise RuntimeError("Internal error: dock sizes do not sum to n_docks")

    dock_positions: List[int] = []

    if len(corridor_columns) >= n_docks:
        # Pick a starting index for each block ensuring enough space.
        start_idx_choices = list(range(0, len(corridor_columns) - n_docks + 1))
        # Bias towards random contiguous grouping.
        base_start = int(rng.choice(start_idx_choices)) if start_idx_choices else 0
        idx = base_start
        for size in raw_sizes:
            dock_positions.extend(corridor_columns[idx : idx + size])
            idx += size
    else:
        # Not enough corridor columns to pick unique positions -> sample.
        for _ in range(n_docks):
            dock_positions.append(int(rng.choice(corridor_columns)))

    dock_positions = sorted(set(dock_positions))

    # If duplicates reduced count, fill remaining.
    while len(dock_positions) < n_docks:
        candidate = int(rng.choice(corridor_columns))
        if candidate not in dock_positions:
            dock_positions.append(candidate)

    dock_positions = sorted(dock_positions)[:n_docks]
    return dock_positions


def _rack_access_ratio(grid: np.ndarray) -> float:
    """
    A basic connectivity check:
    - Walkable cells: CORRIDOR and DOCK.
    - A rack is "reachable" if any of its 4-neighbors is reachable walkable space.
    """
    walkable = (grid == CORRIDOR) | (grid == DOCK)
    docks = np.argwhere(grid == DOCK)
    racks = np.argwhere(grid == RACK)
    if len(racks) == 0 or len(docks) == 0:
        return 0.0

    h, w = grid.shape
    dist = np.full((h, w), np.inf, dtype=float)
    q: deque[Tuple[int, int]] = deque()

    for y, x in docks:
        dist[y, x] = 0.0
        q.append((int(y), int(x)))

    # BFS on walkable cells
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

    reachable = 0
    for y, x in racks:
        ok = False
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and walkable[ny, nx] and np.isfinite(dist[ny, nx]):
                ok = True
                break
        if ok:
            reachable += 1

    return reachable / len(racks)


def generate_layout(config: GeneratorConfig, rng: np.random.Generator) -> np.ndarray:
    """
    Generate a single layout grid.

    Corridors are created as 1-cell thick orthogonal lines.
    Dock cells are placed on corridor columns and grouped into blocks.
    Remaining cells are filled with racks using simple zone-dependent probabilities.
    """
    h, w = config.height, config.width
    picking_start_y = h - int(round(h * config.picking_ratio))
    picking_start_y = int(np.clip(picking_start_y, 0, h - 1))

    max_attempts = 50
    connectivity_target = 0.80  # basic guardrail for the next scoring step

    for _attempt in range(max_attempts):
        grid = np.zeros((h, w), dtype=int)

        # Build corridor network (vertical lines full-height)
        corridor_columns = _choose_line_positions(
            length=w,
            step_min=config.vertical_corridor_step_min,
            step_max=config.vertical_corridor_step_max,
            rng=rng,
        )
        if len(corridor_columns) < 2:
            continue
        for x in corridor_columns:
            grid[:, x] = CORRIDOR

        # Build horizontal corridor lines.
        # Always include one row right above docks to guarantee entry depth.
        required_horizontal = [h - 2]
        # Also add a row near the picking/storage boundary (if possible).
        if 0 <= picking_start_y - 1 < h - 1:
            required_horizontal.append(picking_start_y - 1)

        corridor_rows = _choose_line_positions(
            length=h,
            step_min=config.horizontal_corridor_step_min,
            step_max=config.horizontal_corridor_step_max,
            rng=rng,
            required_positions=required_horizontal,
        )
        for y in corridor_rows:
            grid[y, :] = CORRIDOR

        # Place dock cells (on corridor columns; grouped)
        dock_positions = _choose_dock_positions_from_corridors(
            corridor_columns=corridor_columns,
            n_docks=config.n_docks,
            n_blocks=config.dock_blocks,
            rng=rng,
        )
        for x in dock_positions:
            grid[h - 1, x] = DOCK

        # Fill racks in EMPTY cells
        for y in range(h):
            for x in range(w):
                if grid[y, x] != EMPTY:
                    continue
                if y == h - 1:
                    # bottom row without docks stays empty
                    continue
                in_picking = y >= picking_start_y
                p = config.rack_prob_picking if in_picking else config.rack_prob_storage
                if rng.random() < p:
                    grid[y, x] = RACK

        # Basic connectivity guard
        if _rack_access_ratio(grid) >= connectivity_target and np.any(grid == RACK):
            return grid

    # Fallback: return last attempt-like layout (even if connectivity is weaker)
    # (We do another attempt once to ensure DOCK exists if possible.)
    grid = np.zeros((h, w), dtype=int)
    corridor_columns = _choose_line_positions(
        length=w,
        step_min=config.vertical_corridor_step_min,
        step_max=config.vertical_corridor_step_max,
        rng=rng,
    )
    if not corridor_columns:
        corridor_columns = [w // 2]
    for x in corridor_columns:
        grid[:, x] = CORRIDOR
    dock_positions = _choose_dock_positions_from_corridors(
        corridor_columns=corridor_columns,
        n_docks=config.n_docks,
        n_blocks=config.dock_blocks,
        rng=rng,
    )
    for x in dock_positions:
        grid[h - 1, x] = DOCK

    picking_start_y = h - int(round(h * config.picking_ratio))
    picking_start_y = int(np.clip(picking_start_y, 0, h - 1))
    for y in range(h):
        for x in range(w):
            if grid[y, x] != EMPTY:
                continue
            if y == h - 1:
                continue
            in_picking = y >= picking_start_y
            p = config.rack_prob_picking if in_picking else config.rack_prob_storage
            if rng.random() < p:
                grid[y, x] = RACK

    return grid

