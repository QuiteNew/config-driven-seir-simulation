from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import json


@dataclass(frozen=True)
class SimulationConfig:
    """
    Single source of truth for the whole simulation.
    Everything is config-driven so the engine stays upgrade-friendly.
    """
    population: int = 1000
    initial_exposed: int = 0
    initial_infected: int = 10
    initial_recovered: int = 0
    initial_dead: int = 0

    days: int = 120
    dt_days: float = 1.0

    beta: float = 0.35
    incubation_days: float = 3.0
    infectious_days: float = 7.0

    mortality_rate: float = 0.01

    seed: Optional[int] = 42

    interventions: List[Dict[str, Any]] = field(default_factory=list)

    def validate(self) -> None:
        if self.population <= 0:
            raise ValueError("population must be > 0")
        if self.days <= 0:
            raise ValueError("days must be > 0")
        if self.beta < 0:
            raise ValueError("beta must be >= 0")
        if self.incubation_days <= 0:
            raise ValueError("incubation_days must be > 0")
        if self.infectious_days <= 0:
            raise ValueError("infectious_days must be > 0")
        if not (0.0 <= self.mortality_rate <= 1.0):
            raise ValueError("mortality_rate must be between 0 and 1")

        total_init = (
            self.initial_exposed
            + self.initial_infected
            + self.initial_recovered
            + self.initial_dead
        )
        if total_init > self.population:
            raise ValueError("initial states exceed population")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SimulationConfig":
        if d is None:
            d = {}
        if not isinstance(d, dict):
            raise TypeError("config must be an object/dict")

        allowed = set(SimulationConfig.__dataclass_fields__.keys())
        clean: Dict[str, Any] = {k: v for k, v in d.items() if k in allowed}

        cfg = SimulationConfig(**clean)
        cfg.validate()
        return cfg

    @staticmethod
    def from_json(text: str) -> "SimulationConfig":
        return SimulationConfig.from_dict(json.loads(text))
