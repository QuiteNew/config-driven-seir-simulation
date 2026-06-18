from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class SEIRState:
    """
    Compartment counts. Integers for stochastic runs.
    """
    day: int
    S: int
    E: int
    I: int
    R: int
    D: int = 0

    def total_alive(self) -> int:
        return self.S + self.E + self.I + self.R

    def total(self) -> int:
        return self.S + self.E + self.I + self.R + self.D

    def as_dict(self) -> Dict[str, int]:
        return {
            "day": self.day,
            "S": self.S,
            "E": self.E,
            "I": self.I,
            "R": self.R,
            "D": self.D,
        }

    def assert_valid(self, population: int) -> None:
        for k, v in self.as_dict().items():
            if k != "day" and v < 0:
                raise ValueError(f"Invalid negative compartment {k}={v}")
        if self.total() != population:
            raise ValueError(f"Population not conserved: {self.total()} != {population}")
