from __future__ import annotations

from typing import Dict

import ezdxf
import numpy as np

from .cell_types import CORRIDOR, DOCK, EMPTY, RACK
from .config import GeneratorConfig


_COLOR_BY_TYPE: Dict[int, int] = {
    RACK: 3,  # green-ish
    CORRIDOR: 2,  # yellow-ish
    DOCK: 1,  # red-ish
    EMPTY: 7,  # (unused)
}


def _cell_rect_points(x: int, y: int, width: float, height: float) -> list[tuple[float, float]]:
    return [
        (x, y),
        (x + width, y),
        (x + width, y + height),
        (x, y + height),
        (x, y),
    ]


def export_to_dxf(grid: np.ndarray, filename: str, config: GeneratorConfig) -> None:
    """
    Export a cell grid to DXF as unit rectangles.

    Note: grid y grows downward; we flip y so that "dock row" appears at the bottom
    in CAD coordinates.
    """
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    h, w = grid.shape
    cs = float(config.cell_size)

    for y in range(h):
        for x in range(w):
            v = int(grid[y, x])
            if v == EMPTY:
                continue

            color = _COLOR_BY_TYPE.get(v, 7)
            layer = {RACK: "RACK", CORRIDOR: "CORRIDOR", DOCK: "DOCK"}.get(v, "CELLS")

            # Flip y so y=0 is "top" in array becomes "top" in CAD?
            # Here we flip so bottom row in array becomes bottom in CAD.
            cad_y = (h - 1 - y) * cs
            cad_x = x * cs

            pts = _cell_rect_points(cad_x, cad_y, cs, cs)
            msp.add_lwpolyline(pts, dxfattribs={"color": color, "layer": layer})

    doc.saveas(filename)

