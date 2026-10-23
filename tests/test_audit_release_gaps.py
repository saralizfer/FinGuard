"""Regression tests for the two approved audit corrections."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")


def test_audit_gap_01_requested_fund_percentage_has_two_decimal_places():
    app = AppTest.from_file(APP, default_timeout=30).run()
    assert not app.exception
    donut = next(json.loads(item.proto.spec) for item in app.get("plotly_chart")
                 if json.loads(item.proto.spec)["data"][0]["type"] == "pie")
    assert donut["layout"]["annotations"][0]["text"] == "69.77%"
    assert app.get("progress")[0].proto.text == "69.77% of your selected target funded"
    app.selectbox(key="language").select("es").run()
    assert not app.exception
    assert app.get("progress")[0].proto.text == "69.77% de tu meta seleccionada cubierto"


def test_audit_gap_02_zero_debt_does_not_reduce_investment_capacity_for_impossible_extra_payment():
    app = AppTest.from_file(APP, default_timeout=30).run()
    app.number_input(key="debt_balance").set_value(0)
    app.number_input(key="minimum_debt_payment").set_value(0)
    app.number_input(key="additional_debt_payment").set_value(1500)
    app.run()
    assert not app.exception
    # The monthly engine actually pays $0 extra when no debt is owed; cash after
    # $400 planned savings is $1,100. A separate $200 contribution is affordable.
    assert app.metric[1].value == "$1,100.00"
    assert not any("unfunded scenario" in item.value for item in app.warning)


@pytest.mark.parametrize("apr,monthly,warning_expected", [
    (0, 1000, False),  # minimum payment pays all debt; no extra payment possible
    (24, 998, False),  # $100 + $2 interest - $100 minimum = $2 feasible extra
    (24, 999, True),
])
def test_extra_payment_cap_respects_payoff_interest_and_capacity_boundary(apr, monthly, warning_expected):
    app = AppTest.from_file(APP, default_timeout=30).run()
    for key, value in dict(debt_balance=100, minimum_debt_payment=100, apr=apr,
                           additional_debt_payment=1500, wealth_monthly=monthly).items():
        app.number_input(key=key).set_value(value)
    app.run()
    assert not app.exception
    assert any("unfunded scenario" in item.value for item in app.warning) == warning_expected
    app.selectbox(key="language").select("es").run()
    assert not app.exception
    assert any("sin financiación suficiente" in item.value for item in app.warning) == warning_expected
