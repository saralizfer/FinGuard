"""Comparable recovery paths using the same profile, shock and budget."""

from finguard.assessment import Profile
from finguard.simulation import Shock, Simulation, simulate

STRATEGIES = ("savings_first", "debt_first", "balanced")


def compare_strategies(profile: Profile, shock: Shock, horizon: int,
                       allocation_budget: float, reserve: float = 0.0) -> dict[str, Simulation]:
    return {strategy: simulate(profile, shock, horizon, strategy, allocation_budget, reserve)
            for strategy in STRATEGIES}
