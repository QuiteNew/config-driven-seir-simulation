from engine.config import SimulationConfig
from engine.runner import run_many, BandSpec

cfg = SimulationConfig(
    population=10000,
    initial_infected=10,
    days=60,
    beta=0.35,
    incubation_days=3,
    infectious_days=7,
    mortality_rate=0.01,
    seed=42,
    interventions=[
        {"type": "lockdown", "start_day": 15, "end_day": 40, "beta_multiplier": 0.4},
        {"type": "vaccination", "start_day": 25, "daily_rate": 0.005},
    ],
)

out = run_many(cfg, runs=30, band=BandSpec(0.1, 0.9))
last = out["aggregate"]["series"][-1]
print("Last day:", last["day"])
print("I mean/low/high:", last["I_mean"], last["I_low"], last["I_high"])
