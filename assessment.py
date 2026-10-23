"""Baseline monthly assessment. See docs/model.md for units and assumptions."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class Profile:
    income: float
    essential_expenses: float
    discretionary_expenses: float
    savings: float
    debt_balance: float
    minimum_debt_payment: float
    savings_contribution: float
    target_months: float = 3.0
    apr: float = 24.0
    additional_debt_payment: float = 0.0


@dataclass(frozen=True)
class Assessment:
    cash_flow: float
    unallocated_cash: float
    coverage_months: float | None
    savings_target: float
    savings_shortfall: float
    debt_payment_ratio: float | None


def assess(profile: Profile) -> Assessment:
    """Return descriptive indicators, without an invented health score.

    Income is take-home income. None denotes an undefined ratio.
    Contributions are planned transfers, not additional living expenses.
    """
    for name, value in vars(profile).items():
        if not isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and nonnegative")
    if profile.debt_balance == 0 and profile.minimum_debt_payment > 0:
        raise ValueError("A debt payment requires an outstanding debt balance")
    if profile.minimum_debt_payment > profile.debt_balance:
        raise ValueError("Baseline debt payment cannot exceed debt balance")

    obligations = profile.essential_expenses + profile.minimum_debt_payment
    cash_flow = profile.income - obligations - profile.discretionary_expenses
    target = obligations * profile.target_months
    result = Assessment(
        cash_flow=cash_flow,
        unallocated_cash=cash_flow - profile.savings_contribution,
        coverage_months=profile.savings / obligations if obligations else None,
        savings_target=target,
        savings_shortfall=max(0.0, target - profile.savings),
        debt_payment_ratio=(profile.minimum_debt_payment / profile.income
                            if profile.income else None),
    )
    if any(value is not None and not isfinite(value) for value in vars(result).values()):
        raise ValueError("Amounts exceed the supported numeric range")
    return result
