"""Illustrative monthly compounding with end-of-month contributions."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ProjectionMonth:
    month: int
    contributed: float
    value: float


def project(initial: float, monthly: float, years: int, annual_return: float,
            pause_months: int = 0) -> tuple[ProjectionMonth, ...]:
    """annual_return is an effective annual percentage; negative returns allowed.

    A contribution pause skips (rather than defers) early contributions. Initial
    principal remains invested. Neither contributions nor returns are guaranteed.
    """
    if any(not isfinite(value) or value < 0 for value in (initial, monthly)):
        raise ValueError("Amounts must be finite and nonnegative")
    if not isfinite(annual_return) or not -100 < annual_return <= 100:
        raise ValueError("Annual return must be greater than -100% and at most 100%")
    if not isinstance(years, int) or not 1 <= years <= 50:
        raise ValueError("Years must be 1 to 50")
    if not isinstance(pause_months, int) or not 0 <= pause_months <= years * 12:
        raise ValueError("Pause must fit within the projection horizon")
    rate = (1 + annual_return / 100) ** (1 / 12) - 1
    balance = contributed = initial
    rows = [ProjectionMonth(0, contributed, balance)]
    for month in range(1, years * 12 + 1):
        contribution = monthly if month > pause_months else 0.0
        balance = balance * (1 + rate) + contribution
        contributed += contribution
        if not isfinite(balance) or not isfinite(contributed):
            raise ValueError("Projection exceeds the supported numeric range")
        rows.append(ProjectionMonth(month, contributed, balance))
    return tuple(rows)
