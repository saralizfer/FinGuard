"""Deterministic explanations of existing model results; no new forecasts.

Messages describe the selected profile/scenario and offer controls to explore.
They do not rank a person's health or recommend investments.
"""

from dataclasses import dataclass
from math import isfinite

from finguard.assessment import Assessment, Profile
from finguard.simulation import Simulation


@dataclass(frozen=True)
class Insight:
    explanation: str
    next_step: str
    values: dict[str, float | int]


def assessment_feedback(profile: Profile, result: Assessment) -> tuple[Insight, ...]:
    items = []
    if result.cash_flow < 0:
        items.append(Insight("fb_cash_deficit", "fb_explore_budget", {"amount": -result.cash_flow}))
    elif result.unallocated_cash < 0:
        items.append(Insight("fb_saving_unfunded", "fb_explore_saving", {"amount": -result.unallocated_cash}))
    elif result.unallocated_cash == 0:
        items.append(Insight("fb_cash_zero", "fb_explore_no_room", {}))
    else:
        items.append(Insight("fb_cash_available", "fb_explore_surplus", {"amount": result.unallocated_cash}))
    if result.coverage_months is None or result.savings_target == 0:
        items.append(Insight("fb_target_undefined", "fb_check_target", {}))
    elif result.savings_shortfall > 0:
        items.append(Insight("fb_fund_gap", "fb_explore_fund", {
            "months": result.coverage_months, "gap": result.savings_shortfall,
            "percent": min(100.0, profile.savings / result.savings_target * 100),
        }))
    else:
        items.append(Insight("fb_fund_met", "fb_explore_shock", {"target_months": profile.target_months}))
    if profile.debt_balance > 0:
        # Reuse the same opening-month interest approximation as the simulator.
        interest = profile.debt_balance * profile.apr / 100 / 12
        key = "fb_debt_growing" if profile.minimum_debt_payment < interest else "fb_debt_cost"
        if isfinite(interest):
            items.append(Insight(key, "fb_explore_debt", {"interest": interest, "payment": profile.minimum_debt_payment}))
    return tuple(items)


def emergency_feedback(result: Simulation) -> tuple[Insight, ...]:
    first = result.months[1]
    items = [Insight("fb_shock_month", "fb_explore_shock_budget", {
        "remaining": first.savings, "draw": first.savings_draw, "borrowed": first.new_borrowing,
    })]
    if result.recovery_month is None:
        items.append(Insight("fb_recovery_unreached", "fb_explore_recovery", {"horizon": len(result.months) - 1}))
    else:
        items.append(Insight("fb_recovery_reached", "fb_compare_recovery", {"month": result.recovery_month}))
    return tuple(items)


def recovery_feedback(results: dict[str, Simulation]) -> tuple[Insight, ...]:
    interest = [result.total_interest for result in results.values()]
    spread = max(interest) - min(interest)
    key = "fb_interest_tradeoff" if spread >= 0.005 else "fb_interest_equal"
    items = [Insight(key, "fb_compare_liquidity", {"spread": spread, "horizon": len(next(iter(results.values())).months) - 1})]
    if all(result.target_month is None for result in results.values()):
        items.append(Insight("fb_all_targets_unreached", "fb_explore_allocation", {}))
    return tuple(items)


def wealth_feedback(final_value: float, goal: float, monthly: float, capacity: float) -> tuple[Insight, ...]:
    if monthly > capacity:
        return (Insight("fb_projection_unfunded", "fb_explore_projection_budget", {
            "monthly": monthly, "capacity": capacity, "gap": monthly - capacity,
        }),)
    if final_value < goal:
        return (Insight("fb_projection_gap", "fb_explore_goal", {"gap": goal - final_value}),)
    return (Insight("fb_projection_met", "fb_test_assumptions", {}),)
