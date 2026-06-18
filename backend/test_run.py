from engine.config import SimulationConfig
from engine.model import run

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

out = run(cfg)
print(out["history"][-1])
print("First day event:", out["events"][0])
