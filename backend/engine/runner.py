from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import math

from .config import SimulationConfig
from .model import run


@dataclass(frozen=True)
class BandSpec:
    low_q: float = 0.10
    high_q: float = 0.90

    def validate(self) -> None:
        if not (0.0 <= self.low_q < self.high_q <= 1.0):
            raise ValueError("Invalid quantiles")


def _quantile_sorted(values_sorted: List[float], q: float) -> float:
    if not values_sorted:
        raise ValueError("Empty values")
    n = len(values_sorted)
    if n == 1:
        return float(values_sorted[0])
    x = (n - 1) * q
    lo = int(math.floor(x))
    hi = int(math.ceil(x))
    if lo == hi:
        return float(values_sorted[lo])
    frac = x - lo
    return float(values_sorted[lo] * (1.0 - frac) + values_sorted[hi] * frac)


def _aggregate_history(histories: List[List[Dict[str, int]]], band: BandSpec) -> Dict[str, Any]:
    band.validate()
    n_runs = len(histories)
    if n_runs == 0:
        raise ValueError("No histories to aggregate")

    n_days = len(histories[0])
    for h in histories:
        if len(h) != n_days:
            raise ValueError("All runs must have same number of days")

    keys = ["S", "E", "I", "R", "D"]
    agg: List[Dict[str, Any]] = []

    for t in range(n_days):
        day = int(histories[0][t]["day"])
        row: Dict[str, Any] = {"day": day}

        for k in keys:
            vals = [float(h[t][k]) for h in histories]
            vals_sorted = sorted(vals)
            mean = sum(vals) / n_runs
            low = _quantile_sorted(vals_sorted, band.low_q)
            high = _quantile_sorted(vals_sorted, band.high_q)
            vmin = float(vals_sorted[0])
            vmax = float(vals_sorted[-1])

            row[f"{k}_mean"] = mean
            row[f"{k}_low"] = low
            row[f"{k}_high"] = high
            row[f"{k}_min"] = vmin
            row[f"{k}_max"] = vmax

        agg.append(row)

    return {"days": n_days, "runs": n_runs, "series": agg}


def run_many(
    cfg: SimulationConfig,
    runs: int = 50,
    seed_start: Optional[int] = None,
    band: Optional[BandSpec] = None,
) -> Dict[str, Any]:
    cfg.validate()
    if runs <= 0:
        raise ValueError("runs must be > 0")

    base_seed = cfg.seed if cfg.seed is not None else 0
    if seed_start is None:
        seed_start = base_seed

    band = band or BandSpec(0.10, 0.90)

    histories: List[List[Dict[str, int]]] = []
    run_seeds: List[int] = []

    for i in range(runs):
        s = int(seed_start + i)
        run_cfg = SimulationConfig.from_dict({**cfg.to_dict(), "seed": s})
        out = run(run_cfg)
        histories.append(out["history"])
        run_seeds.append(s)

    aggregated = _aggregate_history(histories, band)

    return {
        "config": cfg.to_dict(),
        "runs": runs,
        "seed_start": seed_start,
        "seeds": run_seeds,
        "band": {"low_q": band.low_q, "high_q": band.high_q},
        "aggregate": aggregated,
    }
