from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .config import SimulationConfig
from .state import SEIRState


@dataclass
class DayTransitions:
    """
    What changed during a single day step.
    Keeping this makes analytics + UI easy later (no rewrites).
    """
    new_exposed: int
    new_infected: int
    new_recovered: int
    new_dead: int
    vaccinated: int = 0


def _clamp_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def _binomial(rng: random.Random, n: int, p: float) -> int:
    """
    Pure-python binomial sampler.
    Upgrade path:
      - later swap to numpy for speed (same API)
      - or use approximations for huge n
    """
    if n <= 0:
        return 0
    if p <= 0.0:
        return 0
    if p >= 1.0:
        return n
    c = 0
    for _ in range(n):
        if rng.random() < p:
            c += 1
    return c


def beta_multiplier_for_day(cfg: SimulationConfig, day: int) -> float:
    """
    Interventions hook (lockdowns, etc.).
    For now only supports beta_multiplier. Later we’ll move interventions to their own module.
    """
    mult = 1.0
    for iv in cfg.interventions:
        if iv.get("type") != "lockdown":
            continue
        start = int(iv.get("start_day", 0))
        end = int(iv.get("end_day", cfg.days - 1))
        if start <= day <= end:
            mult *= float(iv.get("beta_multiplier", 1.0))
    return mult


def vaccination_for_day(cfg: SimulationConfig, day: int, susceptible: int) -> int:
    """
    Vaccination hook (moves S -> R).
    For now: deterministic daily fraction. Later: supply limits, priority groups, etc.
    """
    vaccinated = 0
    for iv in cfg.interventions:
        if iv.get("type") != "vaccination":
            continue
        start = int(iv.get("start_day", 0))
        if day < start:
            continue
        rate = float(iv.get("daily_rate", 0.0))
        if rate <= 0:
            continue
        vaccinated += int(rate * susceptible)
    return _clamp_int(vaccinated, 0, susceptible)


def initial_state(cfg: SimulationConfig) -> SEIRState:
    cfg.validate()
    S = cfg.population - (
        cfg.initial_exposed + cfg.initial_infected + cfg.initial_recovered + cfg.initial_dead
    )
    st = SEIRState(
        day=0,
        S=S,
        E=cfg.initial_exposed,
        I=cfg.initial_infected,
        R=cfg.initial_recovered,
        D=cfg.initial_dead,
    )
    st.assert_valid(cfg.population)
    return st


def step_one_day(cfg: SimulationConfig, state: SEIRState, rng: random.Random) -> Tuple[SEIRState, DayTransitions]:
    """
    One-day SEIR(+D) step with infection pressure based on I/N.
    Stochastic transitions using binomial sampling.
    """
    N = cfg.population
    day = state.day

    vaccinated = vaccination_for_day(cfg, day, state.S)
    S_after_vax = state.S - vaccinated
    R_after_vax = state.R + vaccinated

    beta_eff = cfg.beta * beta_multiplier_for_day(cfg, day)

    I_frac = (state.I / N) if N > 0 else 0.0
    lambda_inf = beta_eff * I_frac * cfg.dt_days
    p_SE = 1.0 - math.exp(-lambda_inf)
    p_SE = max(0.0, min(1.0, p_SE))

    new_exposed = _binomial(rng, S_after_vax, p_SE)

    sigma = cfg.dt_days / cfg.incubation_days
    sigma = max(0.0, min(1.0, sigma))
    new_infected = _binomial(rng, state.E, sigma)

    p_death_day = (cfg.mortality_rate / cfg.infectious_days) * cfg.dt_days
    p_death_day = max(0.0, min(1.0, p_death_day))

    gamma = cfg.dt_days / cfg.infectious_days
    gamma = max(0.0, min(1.0, gamma))

    new_dead = _binomial(rng, state.I, p_death_day)
    I_remaining = state.I - new_dead

    new_recovered = _binomial(rng, I_remaining, gamma)

    S2 = S_after_vax - new_exposed
    E2 = state.E + new_exposed - new_infected
    I2 = state.I + new_infected - new_recovered - new_dead
    R2 = R_after_vax + new_recovered
    D2 = state.D + new_dead

    next_state = SEIRState(day=day + 1, S=S2, E=E2, I=I2, R=R2, D=D2)
    next_state.assert_valid(cfg.population)

    transitions = DayTransitions(
        new_exposed=new_exposed,
        new_infected=new_infected,
        new_recovered=new_recovered,
        new_dead=new_dead,
        vaccinated=vaccinated,
    )
    return next_state, transitions


def run(cfg: SimulationConfig) -> Dict[str, List[Dict[str, int]]]:
    """
    Single run. Returns history as list of daily dicts.
    UI/API friendly output (JSON-ready).
    """
    cfg.validate()
    rng = random.Random(cfg.seed)

    st = initial_state(cfg)
    history: List[Dict[str, int]] = [st.as_dict()]
    events: List[Dict[str, int]] = []

    for _ in range(cfg.days):
        st, tr = step_one_day(cfg, st, rng)
        history.append(st.as_dict())
        events.append({
            "day": st.day,
            "new_exposed": tr.new_exposed,
            "new_infected": tr.new_infected,
            "new_recovered": tr.new_recovered,
            "new_dead": tr.new_dead,
            "vaccinated": tr.vaccinated,
        })

    return {
        "history": history,
        "events": events,
        "config": cfg.to_dict(),
    }
