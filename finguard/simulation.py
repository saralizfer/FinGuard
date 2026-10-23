"""Deterministic monthly cash-flow ledger. All amounts are nominal USD.

No bank-specific minimum-payment formula, fees, daily accrual, or credit limits.
See docs/model.md for the transaction order and interpretation of recovery.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from finguard.assessment import Profile, assess

Strategy = Literal["baseline", "savings_first", "debt_first", "balanced"]


@dataclass(frozen=True)
class Shock:
    expense: float = 0.0
    income_reduction: float = 0.0  # fraction, not percentage
    essential_increase: float = 0.0  # monthly USD
    duration: int = 1

    def validate(self) -> None:
        for value in (self.expense, self.income_reduction, self.essential_increase):
            if not isfinite(value) or value < 0:
                raise ValueError("Shock inputs must be finite and nonnegative")
        if self.income_reduction > 1:
            raise ValueError("Income reduction must be between zero and one")
        if not isinstance(self.duration, int) or not 1 <= self.duration <= 120:
            raise ValueError("Shock duration must be 1 to 120 months")


@dataclass(frozen=True)
class Month:
    month: int
    income: float
    essential_expenses: float
    discretionary_expenses: float
    unexpected_cost: float
    opening_savings: float
    opening_debt: float
    interest: float
    required_payment: float
    additional_payment: float
    cash_flow: float  # income less spending and required payment, before allocations
    savings_draw: float
    new_borrowing: float
    savings_contribution: float
    unallocated_cash: float
    savings: float
    debt: float
    interest_paid: float = 0.0


@dataclass(frozen=True)
class Simulation:
    months: tuple[Month, ...]
    savings_target: float
    target_month: int | None
    recovery_month: int | None
    depletion_month: int | None

    @property
    def total_interest(self) -> float:
        return sum(row.interest for row in self.months)

    @property
    def total_borrowing(self) -> float:
        return sum(row.new_borrowing for row in self.months)

    @property
    def total_interest_paid(self) -> float:
        return sum(row.interest_paid for row in self.months)


def simulate(
    profile: Profile,
    shock: Shock = Shock(),
    horizon: int = 24,
    strategy: Strategy = "baseline",
    allocation_budget: float | None = None,
    reserve: float = 0.0,
) -> Simulation:
    """Simulate month 1 onward, including an opening month-0 snapshot.

    Baseline funds planned savings then planned extra payments from surplus.
    Recovery strategies use the same capped allocation budget, defaulting to
    all monthly surplus, and redirect allocations when either goal is met.
    All policies stop new savings contributions at the fixed baseline target.
    A reserve is prioritized under debt-first; it can still be spent in a deficit.
    """
    assessment = assess(profile)
    shock.validate()
    if not isinstance(horizon, int) or not 1 <= horizon <= 120:
        raise ValueError("Horizon must be 1 to 120 months")
    if strategy not in ("baseline", "savings_first", "debt_first", "balanced"):
        raise ValueError("Unknown allocation strategy")
    if allocation_budget is not None and (not isfinite(allocation_budget) or allocation_budget < 0):
        raise ValueError("Allocation budget must be finite and nonnegative")
    if not isfinite(reserve) or not 0 <= reserve <= assessment.savings_target:
        raise ValueError("Reserve must be between zero and the savings target")

    savings, debt = profile.savings, profile.debt_balance
    target = assessment.savings_target
    unpaid_interest = 0.0  # opening debt is treated as principal for attribution
    # Month 0 records stocks only; all transaction fields are zero.
    rows = [Month(0, 0, 0, 0, 0, savings, debt, 0, 0, 0, 0, 0, 0, 0, 0, savings, debt)]
    target_month = None
    recovery_month = None
    depletion = 0 if savings == 0 else None
    no_shock = shock.expense == shock.income_reduction == shock.essential_increase == 0
    end_shock = 0 if no_shock else shock.duration
    if end_shock == 0 and savings >= target:
        target_month = recovery_month = 0

    for month in range(1, horizon + 1):
        opening_savings, opening_debt = savings, debt
        affected = month <= shock.duration
        income = profile.income * (1 - shock.income_reduction if affected else 1)
        essential = profile.essential_expenses + (shock.essential_increase if affected else 0)
        expense = shock.expense if month == 1 else 0.0
        interest = debt * profile.apr / 100 / 12
        debt += interest
        payment = min(profile.minimum_debt_payment, debt)
        debt -= payment
        cash = income - essential - profile.discretionary_expenses - expense - payment
        draw = borrowing = contribution = extra = 0.0
        if cash < 0:
            draw = min(savings, -cash)
            savings -= draw
            borrowing = max(0.0, -cash - draw)
            debt += borrowing
            unallocated = 0.0
        else:
            room = max(0.0, target - savings)
            if strategy == "baseline":
                contribution = min(cash, profile.savings_contribution, room)
                extra = min(cash - contribution, profile.additional_debt_payment, debt)
            else:
                budget = min(cash, allocation_budget if allocation_budget is not None else cash)
                if strategy == "savings_first":
                    contribution = min(budget, room)
                    extra = min(budget - contribution, debt)
                elif strategy == "debt_first":
                    contribution = min(budget, max(0.0, reserve - savings))
                    extra = min(budget - contribution, debt)
                    contribution += min(budget - contribution - extra, max(0.0, room - contribution))
                else:
                    contribution = min(budget / 2, room)
                    extra = min(budget - contribution, debt)
                    contribution += min(budget - contribution - extra, max(0.0, room - contribution))
            savings += contribution
            debt = max(0.0, debt - extra)
            unallocated = max(0.0, cash - contribution - extra)
        # Attribute actual required + extra payments to accrued interest first.
        # This is reporting only; the same payments have already reduced total debt.
        unpaid_interest += interest
        paid_interest = min(unpaid_interest, payment + extra)
        unpaid_interest -= paid_interest
        if any(not isfinite(value) for value in (income, essential, interest, payment, cash,
                                                 savings, debt, unallocated, borrowing)):
            raise ValueError("Simulation exceeds the supported numeric range")
        rows.append(Month(month, income, essential, profile.discretionary_expenses,
                          expense, opening_savings, opening_debt, interest, payment,
                          extra, cash, draw, borrowing, contribution, unallocated, savings, debt, paid_interest))
        if depletion is None and savings <= 1e-8:
            depletion = month
        # Attainment is assessed after all shock transactions, never before a future shock.
        if month >= end_shock and savings >= target - 1e-8:
            if target_month is None:
                target_month = month
            if recovery_month is None and debt <= profile.debt_balance + 1e-8:
                recovery_month = month

    return Simulation(tuple(rows), target, target_month, recovery_month, depletion)
