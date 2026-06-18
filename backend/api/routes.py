from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

from engine.config import SimulationConfig
from engine.model import run
from engine.runner import run_many, BandSpec

router = APIRouter()


class SimRequest(BaseModel):
    config: Dict[str, Any] = Field(default_factory=dict)


class MultiSimRequest(BaseModel):
    config: Dict[str, Any] = Field(default_factory=dict)
    runs: int = 30
    seed_start: Optional[int] = None
    band_low: float = 0.10
    band_high: float = 0.90


class CompareRequest(BaseModel):
    config_a: Dict[str, Any] = Field(default_factory=dict)
    config_b: Dict[str, Any] = Field(default_factory=dict)
    runs: int = 30
    seed_start: Optional[int] = None
    band_low: float = 0.10
    band_high: float = 0.90


@router.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@router.post("/simulate/run")
def simulate_run(req: SimRequest) -> Dict[str, Any]:
    try:
        cfg = SimulationConfig.from_dict(req.config)
        return run(cfg)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _as_list(x: Any) -> Optional[list]:
    if x is None:
        return None
    if isinstance(x, list):
        return x
    if isinstance(x, tuple):
        return list(x)
    if isinstance(x, (str, bytes, dict)):
        return None
    tolist = getattr(x, "tolist", None)
    if callable(tolist):
        try:
            v = tolist()
            if isinstance(v, list):
                return v
            if isinstance(v, (tuple,)):
                return list(v)
        except Exception:
            pass
    try:
        return list(x)
    except Exception:
        return None


def _pick_series_key(mean: Dict[str, Any]) -> Optional[str]:
    candidates = ["I", "infected", "Infected", "INFECTED", "i", "I_count", "infected_count"]
    for k in candidates:
        if k in mean and _as_list(mean.get(k)) is not None:
            return k

    for k, v in mean.items():
        if _as_list(v) is not None and "infect" in str(k).lower():
            return k

    for k, v in mean.items():
        if _as_list(v) is not None and str(k).strip().lower() == "i":
            return k

    return None


def _normalize_multi_output(raw: Dict[str, Any]) -> Dict[str, Any]:
    agg = raw.get("aggregate")
    if not isinstance(agg, dict):
        raise ValueError("aggregate missing in run_many output")

    series = agg.get("series")
    if not isinstance(series, list) or len(series) == 0:
        raise ValueError(f"aggregate.series missing/invalid. type={type(series).__name__}")

    first = series[0]
    if not isinstance(first, dict):
        raise ValueError(f"aggregate.series items must be dict rows. first_type={type(first).__name__}")

    if "I_mean" in first:
        days = []
        I_mean = []
        I_low = []
        I_high = []

        for row in series:
            if not isinstance(row, dict):
                continue

            d = row.get("day")
            if d is None:
                d = row.get("days")

            days.append(d)

            I_mean.append(row.get("I_mean"))
            I_low.append(row.get("I_low"))
            I_high.append(row.get("I_high"))

        if len(days) == 0 or len(I_mean) == 0:
            raise ValueError("aggregate.series rows did not produce any infected series values")

        if any(v is None for v in days):
            days = list(range(len(I_mean)))

        return {
            "days": days,
            "I_mean": I_mean,
            "I_low": I_low,
            "I_high": I_high,
            "format": "rows",
        }

    raise ValueError(f"aggregate.series row format not recognized. first_row_keys={list(first.keys())}")


@router.post("/simulate/multi")
def simulate_multi(req: MultiSimRequest) -> Dict[str, Any]:
    try:
        if not isinstance(req.config, dict):
            raise ValueError("config must be an object/dict (not a string)")

        cfg = SimulationConfig.from_dict(req.config)
        band = BandSpec(low_q=req.band_low, high_q=req.band_high)

        raw = run_many(cfg, runs=req.runs, seed_start=req.seed_start, band=band)
        if not isinstance(raw, dict):
            raise ValueError("run_many did not return a dict")

        return _normalize_multi_output(raw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/simulate/compare")
def simulate_compare(req: CompareRequest) -> Dict[str, Any]:
    try:
        if not isinstance(req.config_a, dict) or not isinstance(req.config_b, dict):
            raise ValueError("config_a and config_b must be objects/dicts")

        band = BandSpec(low_q=req.band_low, high_q=req.band_high)

        cfg_a = SimulationConfig.from_dict(req.config_a)
        raw_a = run_many(cfg_a, runs=req.runs, seed_start=req.seed_start, band=band)
        out_a = _normalize_multi_output(raw_a)

        cfg_b = SimulationConfig.from_dict(req.config_b)
        raw_b = run_many(cfg_b, runs=req.runs, seed_start=req.seed_start, band=band)
        out_b = _normalize_multi_output(raw_b)

        return {"a": out_a, "b": out_b}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
