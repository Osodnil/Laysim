from __future__ import annotations

import argparse
import os
from typing import Any, Dict, List

import numpy as np

from layout_generator.config import GeneratorConfig
from layout_generator.dxf_export import export_to_dxf
from layout_generator.generator import generate_layout
from layout_generator.report import summarize_top_k, write_results_csv
from layout_generator.scoring import score_layout
from layout_generator.scenario import Scenario


def _build_config(args: argparse.Namespace) -> GeneratorConfig:
    return GeneratorConfig(
        width=args.width,
        height=args.height,
        n_layouts=args.n_layouts,
        top_k=args.top_k,
        seed=args.seed,
        n_docks=args.n_docks,
        dock_blocks=args.dock_blocks,
        vertical_corridor_step_min=args.vertical_corridor_step_min,
        vertical_corridor_step_max=args.vertical_corridor_step_max,
        horizontal_corridor_step_min=args.horizontal_corridor_step_min,
        horizontal_corridor_step_max=args.horizontal_corridor_step_max,
        picking_ratio=args.picking_ratio,
        rack_prob_picking=args.rack_prob_picking,
        rack_prob_storage=args.rack_prob_storage,
        w_distance=args.w_distance,
        w_capacity=args.w_capacity,
        w_connectivity=args.w_connectivity,
        cell_size=args.cell_size,
    )


def _config_to_row_fields(config: GeneratorConfig) -> Dict[str, Any]:
    # Data needed in the report; keep the config readable.
    return {
        "width": config.width,
        "height": config.height,
        "n_docks": config.n_docks,
        "dock_blocks": config.dock_blocks,
        "v_step_min": config.vertical_corridor_step_min,
        "v_step_max": config.vertical_corridor_step_max,
        "h_step_min": config.horizontal_corridor_step_min,
        "h_step_max": config.horizontal_corridor_step_max,
        "picking_ratio": config.picking_ratio,
        "rack_prob_picking": config.rack_prob_picking,
        "rack_prob_storage": config.rack_prob_storage,
        "w_distance": config.w_distance,
        "w_capacity": config.w_capacity,
        "w_connectivity": config.w_connectivity,
        "cell_size": config.cell_size,
        "seed": config.seed,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate multiple CD layout candidates and export top-K to DXF.")
    p.add_argument("--width", type=int, default=50)
    p.add_argument("--height", type=int, default=30)
    p.add_argument("--n-layouts", type=int, default=30)
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--seed", type=int, default=None)

    p.add_argument("--n-docks", type=int, default=5)
    p.add_argument("--dock-blocks", type=int, default=2)

    p.add_argument("--vertical-corridor-step-min", type=int, default=2)
    p.add_argument("--vertical-corridor-step-max", type=int, default=3)
    p.add_argument("--horizontal-corridor-step-min", type=int, default=2)
    p.add_argument("--horizontal-corridor-step-max", type=int, default=3)

    p.add_argument("--picking-ratio", type=float, default=0.25)
    p.add_argument("--rack-prob-picking", type=float, default=0.70)
    p.add_argument("--rack-prob-storage", type=float, default=0.95)

    p.add_argument("--w-distance", type=float, default=1.0)
    p.add_argument("--w-capacity", type=float, default=1.0)
    p.add_argument("--w-connectivity", type=float, default=2.0)

    p.add_argument("--cell-size", type=float, default=1.0)

    p.add_argument("--output-dir", type=str, default=".out")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    config = _build_config(args)
    rng = np.random.default_rng(config.seed)

    rows: List[Dict[str, Any]] = []
    scenarios_by_id: Dict[int, Scenario] = {}

    for i in range(config.n_layouts):
        grid = generate_layout(config, rng=rng)
        metrics = score_layout(grid, config)

        scenario = Scenario(id=i, config=config, grid=grid, metrics=metrics)
        scenarios_by_id[i] = scenario
        row_fields = _config_to_row_fields(config)
        row_fields.update(
            {
                "id": i,
                "score": metrics.score,
                "distance_avg": metrics.distance_avg,
                "capacity_racks": metrics.capacity_racks,
                "connectivity_ratio": metrics.connectivity_ratio,
            }
        )
        rows.append(row_fields)

        print(f"[{i+1}/{config.n_layouts}] score={metrics.score:.6f} racks={metrics.capacity_racks} conn={metrics.connectivity_ratio:.3f}")

    # Save report for all layouts
    report_path = os.path.join(args.output_dir, "layouts_report.csv")
    write_results_csv(rows, report_path)
    print(f"CSV gerado: {report_path}")

    # Export top-K
    top_rows = summarize_top_k(rows, config.top_k)
    for rank, r in enumerate(top_rows, start=1):
        layout_id = int(r["id"])
        scenario = scenarios_by_id[layout_id]
        grid = scenario.grid
        filename = os.path.join(
            args.output_dir,
            f"layout_{rank}_id_{layout_id}_score_{float(r['score']):.4f}.dxf",
        )
        export_to_dxf(grid, filename, config)
        print(f"Exportado: {filename}")

        npy_filename = os.path.join(args.output_dir, f"grid_topk_{rank}_id_{layout_id}.npy")
        scenario.save_grid_npy(npy_filename)
        print(f"Grid salvo: {npy_filename}")


if __name__ == "__main__":
    main()

