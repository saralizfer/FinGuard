"""Audit-only independent arithmetic; does not change application behavior.

Closed forms, Decimal arithmetic, explicit manual cases, and independent
conservation identities complement the pre-existing implementation tests.
"""

import json
import random
from dataclasses import replace
from decimal import Decimal, localcontext
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from finguard.assessment import Profile, assess
from finguard.recovery import compare_strategies
from finguard.simulation import Shock, simulate
from finguard.translations import TEXT
from finguard.wealth import project

APP = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")
D = lambda value: Decimal(str(value))
DEFAULT = Profile(4000, 2000, 500, 4500, 3000, 150, 400)


def test_requested_baseline_against_decimal_arithmetic():
    actual = assess(DEFAULT)
    obligations = D(2000) + D(150)
    expected = [D(4000) - obligations - D(500), D(4000) - obligations - D(500) - D(400),
                D(4500) / obligations, D(3) * obligations,
                D(3) * obligations - D(4500), D(150) / D(4000)]
    for field, value in zip(actual.__dataclass_fields__, expected):
        assert getattr(actual, field) == pytest.approx(float(value), rel=1e-12)
    assert D(4500) / (D(3) * obligations) * 100 == pytest.approx(D("69.76744186046511627906976744"))


@pytest.mark.parametrize("balance,apr,payment,months", [
    (3000, 24, 150, 12), (3000, 24, 150, 24), (3000, 24, 150, 36),
    (1000, 0, 100, 24), (1000, 36, 5, 24), (1000, 24, 0, 24),
    (100, 12, 100, 2), (0, 24, 0, 24),
])
def test_amortization_against_closed_form_and_terminal_payment(balance, apr, payment, months):
    p = Profile(10000, 0, 0, 0, balance, payment, 0, 0, apr)
    result = simulate(p, horizon=months)
    rate, principal, total_paid = D(apr) / 1200, D(balance), D(0)
    # Fixed-payment annuity closed form, until the payoff month. The final
    # payment is independently capped at the previous closed-form debt + interest.
    def raw_debt(n):
        if rate == 0:
            return principal - D(payment) * n
        return principal * (1 + rate) ** n - D(payment) * (((1 + rate) ** n - 1) / rate)
    for month, row in enumerate(result.months[1:], 1):
        previous = max(D(0), raw_debt(month - 1))
        actual_payment = min(D(payment), previous * (1 + rate))
        total_paid += actual_payment
        expected = max(D(0), raw_debt(month))
        assert row.debt == pytest.approx(float(expected), abs=1e-8)
        assert row.interest == pytest.approx(float(previous * rate), abs=1e-8)
        assert row.required_payment == pytest.approx(float(actual_payment), abs=1e-8)
    expected_interest = max(D(0), raw_debt(months)) - principal + total_paid
    assert result.total_interest == pytest.approx(float(expected_interest), abs=1e-8)


@pytest.mark.parametrize("shock,cash,saved,debt,borrowed,contributed", [
    (Shock(expense=2500), -1150, 3350, 2910, 0, 0),
    (Shock(expense=10000), -8650, 0, 7060, 4150, 0),
    (Shock(income_reduction=1, duration=3), -2650, 1850, 2910, 0, 0),
    (Shock(income_reduction=0.30, duration=3), 150, 4650, 2910, 0, 150),
    (Shock(essential_increase=300, duration=3), 1050, 4900, 2910, 0, 400),
])
def test_manual_first_month_shocks(shock, cash, saved, debt, borrowed, contributed):
    row = simulate(DEFAULT, shock).months[1]
    assert row.cash_flow == pytest.approx(cash)
    assert row.savings == pytest.approx(saved)
    assert row.debt == pytest.approx(debt)
    assert row.new_borrowing == pytest.approx(borrowed)
    assert row.savings_contribution == pytest.approx(contributed)
    assert row.interest == 60


def test_unemployment_three_months_decimal_reconciliation():
    result = simulate(DEFAULT, Shock(income_reduction=1, duration=3), horizon=4)
    # Independent explicit worksheet: three zero-income months at 2,650 costs.
    debt1 = D(3000) * D("1.02") - 150
    debt2 = debt1 * D("1.02") - 150 + 800
    debt3 = debt2 * D("1.02") - 150 + 2650
    for month, expected in enumerate([debt1, debt2, debt3], 1):
        assert result.months[month].debt == pytest.approx(float(expected))
    assert result.total_borrowing == 3450
    assert result.depletion_month == 2
    assert result.months[4].income == 4000
    assert result.months[4].savings == 400


def test_zero_initial_debt_new_borrowing_keeps_configured_zero_minimum():
    # Validates the current documented fixed-payment assumption, not real card
    # issuer behavior: borrowing does not dynamically create a minimum payment.
    p = replace(DEFAULT, debt_balance=0, minimum_debt_payment=0)
    result = simulate(p, Shock(expense=10000), horizon=2)
    assert result.months[1].new_borrowing == 4000
    assert result.months[1].debt == 4000
    assert result.months[2].interest == 80
    assert result.months[2].required_payment == 0
    assert result.months[2].debt == 4080


@pytest.mark.parametrize("strategy,contribution,extra,savings,debt", [
    ("savings_first", 400, 0, 4900, 2910),
    ("debt_first", 0, 400, 4500, 2510),
    ("balanced", 200, 200, 4700, 2710),
])
def test_recovery_manual_allocation(strategy, contribution, extra, savings, debt):
    row = compare_strategies(DEFAULT, Shock(), 24, 400)[strategy].months[1]
    assert (row.savings_contribution, row.additional_payment, row.savings, row.debt) == (
        contribution, extra, savings, debt)
    assert row.unallocated_cash == 950


def decimal_reference_path(profile, shock, strategy, cap, reserve, horizon):
    """Standalone double-entry worksheet with priority allocation buckets.

    Decimal stocks and generic ordered buckets are independent of production
    simulation code. Closed forms and manual cases above are additional oracles.
    """
    savings, debt = D(profile.savings), D(profile.debt_balance)
    target = D(profile.target_months) * (D(profile.essential_expenses) + D(profile.minimum_debt_payment))
    unpaid = D(0)
    for month in range(1, horizon + 1):
        income = D(profile.income) * (1 - D(shock.income_reduction) if month <= shock.duration else 1)
        costs = D(profile.essential_expenses) + D(profile.discretionary_expenses)
        costs += D(shock.essential_increase) if month <= shock.duration else 0
        costs += D(shock.expense) if month == 1 else 0
        interest = debt * D(profile.apr) / 1200
        debt += interest
        unpaid += interest
        required = min(D(profile.minimum_debt_payment), debt)
        debt -= required
        cash = income - costs - required
        extra = contribution = borrowing = D(0)
        if cash < 0:
            withdrawal = min(savings, -cash)
            savings -= withdrawal
            borrowing = -cash - withdrawal
            debt += borrowing
        else:
            pool = cash if strategy == "baseline" else min(cash, D(cap))
            # Each bucket requests a maximum amount; remaining budget flows to
            # later buckets. Repeated savings buckets implement redistribution.
            if strategy == "baseline":
                buckets = [("savings", D(profile.savings_contribution), target),
                           ("debt", D(profile.additional_debt_payment), D(0))]
            elif strategy == "savings_first":
                buckets = [("savings", pool, target), ("debt", pool, D(0))]
            elif strategy == "debt_first":
                buckets = [("savings", pool, D(reserve)), ("debt", pool, D(0)), ("savings", pool, target)]
            else:
                buckets = [("savings", pool / 2, target), ("debt", pool, D(0)), ("savings", pool, target)]
            for account, request, ceiling in buckets:
                capacity = max(D(0), ceiling - savings) if account == "savings" else debt
                amount = min(pool, request, capacity)
                pool -= amount
                if account == "savings":
                    savings += amount
                    contribution += amount
                else:
                    debt -= amount
                    extra += amount
        interest_paid = min(unpaid, required + extra)
        unpaid -= interest_paid
        yield {"savings": savings, "debt": debt, "interest": interest,
               "required_payment": required, "additional_payment": extra,
               "savings_contribution": contribution, "new_borrowing": borrowing,
               "interest_paid": interest_paid}


@pytest.mark.parametrize("strategy", ["baseline", "savings_first", "debt_first", "balanced"])
@pytest.mark.parametrize("shock", [Shock(), Shock(expense=2500), Shock(expense=10000),
                                   Shock(income_reduction=1, duration=3),
                                   Shock(income_reduction=.3, duration=3),
                                   Shock(essential_increase=300, duration=3)])
def test_full_paths_against_separate_decimal_priority_worksheet(strategy, shock):
    result = simulate(DEFAULT, shock, 120, strategy, 400, 500)
    expected = decimal_reference_path(DEFAULT, shock, strategy, 400, 500, 120)
    for row, reference in zip(result.months[1:], expected):
        for field, value in reference.items():
            assert getattr(row, field) == pytest.approx(float(value), abs=1e-7)


@pytest.mark.parametrize("seed", range(12))
def test_seeded_conservation_under_all_policies(seed):
    rng = random.Random(seed)
    debt = rng.randint(0, 20000)
    p = Profile(rng.randint(0, 8000), rng.randint(0, 5000), rng.randint(0, 2000),
                rng.randint(0, 15000), debt, min(debt, rng.randint(0, 600)),
                rng.randint(0, 1000), rng.randint(0, 8), rng.choice([0, 12, 24, 60]), rng.randint(0, 500))
    shock = Shock(rng.randint(0, 10000), rng.choice([0, 0.25, 0.5, 1]), rng.randint(0, 600), 3)
    for strategy in ("baseline", "savings_first", "debt_first", "balanced"):
        result = simulate(p, shock, 24, strategy, 500, 0)
        total_principal = D(p.debt_balance)
        for row in result.months[1:]:
            sources = sum(map(D, [row.income, row.savings_draw, row.new_borrowing]))
            uses = sum(map(D, [row.essential_expenses, row.discretionary_expenses, row.unexpected_cost,
                               row.required_payment, row.additional_payment, row.savings_contribution, row.unallocated_cash]))
            assert float(sources - uses) == pytest.approx(0, abs=1e-8)
            assert row.savings >= 0 and row.debt >= 0
            assert row.savings == pytest.approx(row.opening_savings - row.savings_draw + row.savings_contribution)
            total_principal += D(row.new_borrowing)
        assert result.months[-1].debt == pytest.approx(float(
            total_principal + sum(D(row.interest) - D(row.required_payment) - D(row.additional_payment)
                                  for row in result.months[1:])), abs=1e-7)
        assert result.total_interest_paid <= result.total_interest + 1e-8


@pytest.mark.parametrize("annual", [-90, -10, 0, 5, 12, 50])
@pytest.mark.parametrize("pause", [0, 3, 12])
def test_projection_against_independent_discounted_cash_flow_sum(annual, pause):
    with localcontext() as context:
        context.prec = 50
        rate = (1 + D(annual) / 100) ** (D(1) / 12)
        for years in (1, 10):
            for monthly in (100, 200):
                count = years * 12
                expected = D(1000) * rate ** count + sum(
                    D(monthly) * rate ** (count - month) for month in range(pause + 1, count + 1))
                actual = project(1000, monthly, years, annual, pause)[-1]
                assert actual.value == pytest.approx(float(expected), rel=1e-11, abs=1e-8)
                assert actual.contributed == 1000 + monthly * (count - pause)


@pytest.mark.parametrize("changes", [
    dict(income=0), dict(savings=0), dict(debt_balance=0, minimum_debt_payment=0),
    dict(income=100, savings=0), dict(essential_expenses=0, minimum_debt_payment=0),
])
def test_extreme_profile_cases_run_both_languages(changes):
    app = AppTest.from_file(APP, default_timeout=30).run()
    for key, value in changes.items():
        app.number_input(key=key).set_value(value)
    app.run()
    assert not app.exception
    snapshot = app.dataframe[0].value.iloc[:, 1:].to_numpy().tolist()
    app.selectbox(key="language").select("es").run()
    assert not app.exception
    assert app.dataframe[0].value.iloc[:, 1:].to_numpy().tolist() == snapshot
    assert len(app.tabs) == 5


@pytest.mark.parametrize("scenario", ["medical", "vehicle", "income_loss", "reduced_income", "living_cost"])
def test_all_scenario_labels_translate_without_changing_numbers(scenario):
    app = AppTest.from_file(APP, default_timeout=30).run()
    app.selectbox(key="scenario").select(scenario).run()
    assert not app.exception
    before = [frame.value.to_numpy().tolist() for frame in app.dataframe]
    app.selectbox(key="language").select("es").run()
    assert not app.exception
    after = [frame.value.to_numpy().tolist() for frame in app.dataframe]
    # Ledger is numeric strings. Strategy names are translated, so compare the
    # numeric columns independently rather than asserting identical labels.
    assert before[0] == after[0]
    for old, new in zip(before[1:], after[1:]):
        normalized = [[TEXT["en"]["not_reached"] if value == TEXT["es"]["not_reached"] else value
                       for value in row[1:]] for row in new]
        assert [row[1:] for row in old] == normalized
    assert app.selectbox(key="scenario").value == scenario


def test_charts_use_actual_ledger_values_and_no_nan_or_infinity():
    app = AppTest.from_file(APP, default_timeout=30).run()
    assert not app.exception
    charts = [json.loads(item.proto.spec) for item in app.get("plotly_chart")]
    assert len(charts) == 8
    waterfall, donut = charts[:2]
    assert waterfall["data"][0]["customdata"] == [4000, -2000, -500, -150, -400, 950]
    assert donut["data"][0]["values"] == [4500, 1950]
    for chart in charts:
        json.dumps(chart, allow_nan=False)


def test_distinct_sessions_do_not_receive_another_profiles_result():
    first = AppTest.from_file(APP, default_timeout=30).run()
    first.number_input(key="income").set_value(7000).run()
    second = AppTest.from_file(APP, default_timeout=30).run()
    assert not first.exception and not second.exception
    assert first.metric[0].value == "$4,350.00"
    assert second.metric[0].value == "$1,350.00"


def test_educational_limitations_are_present_in_both_languages():
    app = AppTest.from_file(APP, default_timeout=30).run()
    for language in ("en", "es"):
        app.selectbox(key="language").select(language).run()
        assert not app.exception
        assert any(item.label == TEXT[language]["about_title"] for item in app.sidebar.expander)
        assert any(item.value == TEXT[language]["wealth_assumptions"] for item in app.info)
        assert any(item.value == TEXT[language]["borrowing_assumption"] for item in app.info)
        assert any(item.value == TEXT[language]["fixed_payment_assumption"] for item in app.info)
