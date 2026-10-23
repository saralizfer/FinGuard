from dataclasses import replace

import pytest

from finguard.assessment import Profile
from finguard.recovery import compare_strategies
from finguard.simulation import Shock, simulate
from finguard.wealth import project


def base(**changes):
    return replace(Profile(1000, 600, 100, 500, 1000, 100, 100, 3, 24, 50), **changes)


def test_manual_month_interest_and_payments_are_counted_once():
    row = simulate(base(), horizon=1).months[1]
    # 1000 * 24% / 12 = 20; debt = 1000 + 20 - 100 - 50 = 870.
    assert row.interest == 20
    assert row.cash_flow == 200
    assert row.savings == 600
    assert row.debt == 870
    assert row.unallocated_cash == 50
    assert row.interest_paid == 20


def test_unpaid_interest_is_not_reported_as_paid():
    result = simulate(base(minimum_debt_payment=1, savings_contribution=0, additional_debt_payment=0), horizon=2)
    assert result.months[1].interest == 20
    assert result.months[1].interest_paid == 1
    assert result.total_interest_paid == 2
    assert result.total_interest > 40


def test_manual_shock_spends_savings_then_borrows_without_negative_savings():
    result = simulate(base(), Shock(expense=1000), horizon=2)
    first, second = result.months[1:]
    # 1000 income - 600 essentials - 100 discretionary - 100 payment - 1000 shock = -800.
    assert first.cash_flow == -800
    assert first.savings_draw == 500
    assert first.new_borrowing == 300
    assert first.savings == 0
    assert first.debt == 1220  # 1000 + 20 interest - 100 payment + 300 borrowing
    assert second.interest == pytest.approx(24.4)  # new borrowing first accrues next month
    assert result.depletion_month == 1


@pytest.mark.parametrize("strategy", ["baseline", "savings_first", "debt_first", "balanced"])
def test_every_month_balances_sources_uses_and_stocks(strategy):
    result = simulate(base(), Shock(1700, 0.5, 200, 3), 24, strategy, 350, 100)
    for row in result.months[1:]:
        assert row.savings >= 0
        assert row.debt >= 0
        assert row.income + row.savings_draw + row.new_borrowing == pytest.approx(
            row.essential_expenses + row.discretionary_expenses + row.unexpected_cost
            + row.required_payment + row.additional_payment + row.savings_contribution + row.unallocated_cash)
        assert row.debt == pytest.approx(row.opening_debt + row.interest
                                         - row.required_payment - row.additional_payment + row.new_borrowing)
        assert row.savings == pytest.approx(row.opening_savings - row.savings_draw + row.savings_contribution)


def test_debt_payoff_is_capped_and_releases_required_payment():
    result = simulate(base(debt_balance=50, minimum_debt_payment=50, apr=0), horizon=2)
    assert result.months[1].debt == 0
    assert result.months[1].additional_payment == 0
    assert result.months[2].required_payment == 0
    assert result.months[2].cash_flow == 300


def test_recovery_strategies_share_budget_with_reserve_and_redirect_unused_funds():
    paths = compare_strategies(base(), Shock(), 24, 200, 600)
    assert paths["savings_first"].months[1].savings_contribution == 200
    assert paths["debt_first"].months[1].savings_contribution == 100  # reserve gap
    assert paths["debt_first"].months[1].additional_payment == 100
    assert paths["balanced"].months[1].savings_contribution == 100
    for result in paths.values():
        for row in result.months[1:]:
            assert row.additional_payment + row.savings_contribution <= 200 + 1e-8
    debt_free = simulate(base(debt_balance=0, minimum_debt_payment=0), horizon=1,
                         strategy="balanced", allocation_budget=200)
    assert debt_free.months[1].savings_contribution == 200


def test_income_shock_duration_and_no_fabricated_recovery():
    result = simulate(base(savings=0), Shock(income_reduction=1, duration=2), 2)
    assert [row.income for row in result.months[1:]] == [0, 0]
    assert result.recovery_month is None
    assert result.target_month is None
    assert result.depletion_month == 0
    resumed = simulate(base(), Shock(income_reduction=1, duration=2), 3)
    assert resumed.months[3].income == 1000


def test_zero_profile_and_zero_budget():
    result = simulate(Profile(0, 0, 0, 0, 0, 0, 0), horizon=2, allocation_budget=0)
    assert result.total_interest == result.total_borrowing == 0
    assert result.recovery_month == 0
    assert result.depletion_month == 0


@pytest.mark.parametrize("kwargs", [
    {"horizon": 0}, {"horizon": 121}, {"reserve": -1}, {"reserve": 10000},
    {"allocation_budget": float("nan")}, {"strategy": "unknown"},
    {"shock": Shock(income_reduction=1.1)}, {"shock": Shock(expense=-1)},
    {"shock": Shock(duration=0)},
])
def test_simulation_rejects_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        simulate(base(), **kwargs)


def test_projection_manual_examples_and_timing():
    zero = project(1000, 100, 1, 0)
    assert zero[-1].value == pytest.approx(2200)
    assert zero[-1].contributed == 2200
    assert project(1000, 0, 1, 12)[-1].value == pytest.approx(1120)
    # 100 at each month end, no growth before the contribution is deposited.
    row = project(0, 100, 1, 12)[1]
    assert row.value == 100
    paused = project(1000, 100, 1, 0, 3)
    assert paused[-1].value == pytest.approx(1900)
    assert project(1000, 0, 1, -10)[-1].value == pytest.approx(900)
    rate = 1.12 ** (1 / 12) - 1
    assert project(1000, 100, 1, 12)[-1].value == pytest.approx(
        1000 * 1.12 + 100 * ((1 + rate) ** 12 - 1) / rate)


def test_initial_target_attainment_is_not_claimed_before_the_shock():
    result = simulate(base(savings=2100), Shock(expense=5000), horizon=1)
    assert result.months[0].savings == result.savings_target
    assert result.target_month is None
    assert result.recovery_month is None


def test_reaching_savings_target_is_distinct_from_recovering_initial_debt():
    # With zero target, the target is satisfied after the shock, but new debt remains.
    result = simulate(base(savings=0, target_months=0), Shock(expense=5000), horizon=1)
    assert result.target_month == 1
    assert result.recovery_month is None


@pytest.mark.parametrize("args", [(-1, 0, 1, 0), (0, -1, 1, 0), (0, 0, 0, 0),
                                   (0, 0, 1, -100), (0, 0, 1, float("nan")), (0, 0, 1, 5, 13)])
def test_projection_validation(args):
    with pytest.raises(ValueError):
        project(*args)


def test_numeric_overflow_is_rejected_instead_of_displaying_infinity():
    with pytest.raises(ValueError):
        project(1e308, 1e308, 1, 100)
    with pytest.raises(ValueError):
        simulate(base(apr=1e308), horizon=120)
