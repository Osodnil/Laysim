from __future__ import annotations

from typing import Any, Dict, Iterable, List

import pandas as pd


def write_results_csv(rows: Iterable[Dict[str, Any]], filename: str) -> None:
    df = pd.DataFrame(list(rows))
    # Keep a stable column order if possible.
    preferred = ["id", "score", "distance_avg", "capacity_racks", "connectivity_ratio"]
    cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
    df = df[cols]
    df.to_csv(filename, index=False, encoding="utf-8")


def summarize_top_k(rows: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    rows_sorted = sorted(rows, key=lambda r: float(r["score"]))
    return rows_sorted[:top_k]

