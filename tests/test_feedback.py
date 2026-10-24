"""Feedback follows audited outputs and never invents recovery guarantees."""

from dataclasses import replace
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from finguard.assessment import Profile, assess
from finguard.feedback import assessment_feedback, emergency_feedback, recovery_feedback, wealth_feedback
from finguard.recovery import compare_strategies
from finguard.simulation import Shock, simulate
from finguard.translations import TEXT

BASE = Profile(4000, 2000, 500, 4500, 3000, 150, 400)


def test_default_feedback_uses_verified_results():
    items = assessment_feedback(BASE, assess(BASE))
    assert items[0].explanation == "fb_cash_available"
    assert items[0].values["amount"] == 950
    assert items[1].values["gap"] == 1950
    assert items[1].values["percent"] == pytest.approx(69.76744186046511)
    assert items[1].values["months"] == pytest.approx(4500 / 2150)
    assert items[2].values["interest"] == 60


@pytest.mark.parametrize("changes,key", [
    ({"income": 0}, "fb_cash_deficit"),
    ({"savings_contribution": 2000}, "fb_saving_unfunded"),
    ({"savings_contribution": 1350}, "fb_cash_zero"),
])
def test_cash_feedback_distinguishes_actual_deficit_from_unfunded_saving(changes, key):
    profile = replace(BASE, **changes)
    assert assessment_feedback(profile, assess(profile))[0].explanation == key


@pytest.mark.parametrize("changes,key", [
    ({"savings": 7000}, "fb_fund_met"),
    ({"target_months": 0}, "fb_target_undefined"),
    ({"essential_expenses": 0, "minimum_debt_payment": 0}, "fb_target_undefined"),
    ({"savings": 0}, "fb_fund_gap"),
])
def test_target_feedback_handles_zero_and_excess_savings(changes, key):
    profile = replace(BASE, **changes)
    assert assessment_feedback(profile, assess(profile))[1].explanation == key


def test_debt_feedback_does_not_confuse_minimum_payment_with_extra_payments():
    profile = replace(BASE, minimum_debt_payment=10, additional_debt_payment=500)
    assert assessment_feedback(profile, assess(profile))[-1].explanation == "fb_debt_growing"
    no_debt = replace(BASE, debt_balance=0, minimum_debt_payment=0)
    assert len(assessment_feedback(no_debt, assess(no_debt))) == 2


def test_shock_feedback_uses_month_one_and_does_not_invent_recovery_time():
    result = simulate(BASE, Shock(expense=10000), horizon=24)
    first, recovery = emergency_feedback(result)
    assert first.values == {"remaining": 0, "draw": 4500, "borrowed": 4150}
    assert recovery.explanation == "fb_recovery_unreached"
    assert recovery.values["horizon"] == 24
    reached = simulate(BASE, Shock(expense=2500))
    assert emergency_feedback(reached)[1].values["month"] == 9


def test_strategy_feedback_describes_actual_interest_difference_and_ties():
    paths = compare_strategies(BASE, Shock(expense=2500), 24, 400)
    item = recovery_feedback(paths)[0]
    assert item.explanation == "fb_interest_tradeoff"
    assert item.values["spread"] == pytest.approx(571.8757381555953 - 257.6680156031413, abs=.01)
    tied = compare_strategies(replace(BASE, apr=0), Shock(), 24, 400)
    assert recovery_feedback(tied)[0].explanation == "fb_interest_equal"
    unreachable = compare_strategies(replace(BASE, savings=0), Shock(expense=10000), 1, 0)
    assert recovery_feedback(unreachable)[1].explanation == "fb_all_targets_unreached"


def test_every_generated_template_formats_in_both_languages():
    profiles = [BASE, replace(BASE, income=0), replace(BASE, savings_contribution=2000),
                replace(BASE, savings_contribution=1350), replace(BASE, savings=10000),
                replace(BASE, target_months=0), replace(BASE, minimum_debt_payment=1)]
    insights = [item for profile in profiles for item in assessment_feedback(profile, assess(profile))]
    insights += list(emergency_feedback(simulate(BASE, Shock(expense=10000))))
    insights += list(emergency_feedback(simulate(BASE, Shock(expense=2500))))
    for args in [(1000, 50000, 2000, 950), (1000, 50000, 200, 950), (50000, 50000, 200, 950)]:
        insights += list(wealth_feedback(*args))
    for language in ("en", "es"):
        for insight in insights:
            assert TEXT[language][insight.explanation].format(**insight.values)
            assert TEXT[language][insight.next_step].format(**insight.values)


@pytest.mark.parametrize("ending,goal,monthly,capacity,key", [
    (50000, 50000, 2000, 950, "fb_projection_unfunded"),
    (32501.53, 50000, 200, 950, "fb_projection_gap"),
    (50000, 50000, 200, 950, "fb_projection_met"),
    (1000, 50000, 0, 0, "fb_projection_gap"),
])
def test_wealth_feedback_prioritizes_affordability_over_projected_goal(ending, goal, monthly, capacity, key):
    assert wealth_feedback(ending, goal, monthly, capacity)[0].explanation == key


def test_bilingual_feedback_recalculates_with_user_inputs_without_changing_metrics():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py"), default_timeout=30).run()
    assert not app.exception
    assert any("What your results mean for you" == heading.value for heading in app.subheader)
    assert any("69.77%" in item.value and "$1,950.00" in item.value for item in app.markdown)
    app.number_input(key="income").set_value(1000).run()
    app.selectbox(key="language").select("es").run()
    assert not app.exception
    assert app.metric[0].value == "-$1,650.00"
    assert any("Te faltan" in item.value and "$1,650.00" in item.value for item in app.markdown)
    assert any(TEXT["es"]["feedback_next"] in item.value for item in app.markdown)
