import json
from pathlib import Path

import pytest

from finguard.assessment import Profile, assess


def test_manually_verified_example():
    sample = Path(__file__).resolve().parents[1] / "data" / "sample_profile.json"
    result = assess(Profile(**json.loads(sample.read_text())))
    assert result.cash_flow == 1350
    assert result.unallocated_cash == 950
    assert result.coverage_months == pytest.approx(4500 / 2150)
    assert result.savings_target == 6450
    assert result.savings_shortfall == 1950
    assert result.debt_payment_ratio == pytest.approx(0.0375)


def test_zero_income_and_obligations_have_undefined_ratios():
    result = assess(Profile(0, 0, 0, 0, 0, 0, 0))
    assert result.debt_payment_ratio is None
    assert result.coverage_months is None
    assert result.savings_shortfall == 0


def test_deficit_is_preserved_and_excess_savings_do_not_create_shortfall():
    result = assess(Profile(1000, 1200, 100, 10000, 500, 50, 100))
    assert result.cash_flow == -350
    assert result.unallocated_cash == -450
    assert result.savings_shortfall == 0


@pytest.mark.parametrize("field", list(Profile.__dataclass_fields__))
@pytest.mark.parametrize("invalid", [-1, float("nan"), float("inf")])
def test_reject_invalid_inputs(field, invalid):
    values = dict(income=4000, essential_expenses=2000,
                  discretionary_expenses=500, savings=4500,
                  debt_balance=3000, minimum_debt_payment=150,
                  savings_contribution=400, target_months=3)
    values[field] = invalid
    with pytest.raises(ValueError):
        assess(Profile(**values))


@pytest.mark.parametrize("balance,payment", [(0, 10), (5, 10)])
def test_reject_inconsistent_debt_payment(balance, payment):
    with pytest.raises(ValueError):
        assess(Profile(1000, 500, 100, 0, balance, payment, 0))


def test_derived_numeric_overflow_is_rejected():
    with pytest.raises(ValueError):
        assess(Profile(1000, 1e308, 0, 0, 0, 0, 0, 3))
