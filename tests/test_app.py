"""Check observable interface behavior against the financial contract."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from finguard.translations import TEXT
from finguard.user_context import UserContext

APP = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")


def test_sample_and_language_switch_preserve_edited_profile():
    app = AppTest.from_file(APP, default_timeout=15).run()
    assert not app.exception
    assert [metric.value for metric in app.metric][:6] == [
        "$1,350.00", "$950.00", "2.09 months", "$6,450.00", "$1,950.00", "3.75%",
    ]
    app.number_input(key="income").set_value(5000).run()
    app.selectbox(key="language").select("es").run()
    assert not app.exception
    assert app.number_input(key="income").value == 5000
    assert app.metric[0].label == "Flujo mensual antes de ahorrar"
    assert app.metric[0].value == "$2,350.00"
    app.button(key="reset").click().run()
    assert not app.exception
    assert app.number_input(key="income").value == 4000
    assert app.selectbox(key="language").value == "es"


def test_inconsistent_debt_is_explained_without_rendering_metrics():
    app = AppTest.from_file(APP, default_timeout=15).run()
    app.number_input(key="debt_balance").set_value(0).run()
    assert not app.exception
    assert app.error
    assert not app.metric


def test_zero_income_and_zero_obligations_are_not_rendered_as_zero_ratios():
    app = AppTest.from_file(APP, default_timeout=15).run()
    for field in ("income", "essential_expenses", "minimum_debt_payment"):
        app.number_input(key=field).set_value(0)
    app.run()
    assert not app.exception
    assert app.metric[2].value == "Not defined"
    assert app.metric[5].value == "Not defined"
    assert app.warning


def test_unfunded_savings_plan_displays_warning():
    app = AppTest.from_file(APP, default_timeout=15).run()
    app.number_input(key="savings_contribution").set_value(2000).run()
    assert not app.exception
    assert app.metric[1].value == "-$650.00"
    assert "exceeds available" in app.warning[0].value


def test_spending_explorer_is_separate_from_profile_and_translates():
    app = AppTest.from_file(APP, default_timeout=15).run()
    app.slider(key="spending_reduction").set_value(50).run()
    assert not app.exception
    assert app.number_input(key="discretionary_expenses").value == 500
    assert app.metric[1].value == "$950.00"
    assert any("$250.00" in item.value and "$1,200.00" in item.value for item in app.markdown)
    app.selectbox(key="language").select("es").run()
    assert not app.exception
    assert app.slider(key="spending_reduction").value == 50
    assert any("Reducir gastos flexibles" in item.value and "$1,200.00" in item.value for item in app.markdown)


def test_zero_target_shows_explanation_instead_of_percentage():
    app = AppTest.from_file(APP, default_timeout=15).run()
    app.number_input(key="target_months").set_value(0).run()
    assert not app.exception
    assert any("Choose a target greater than zero" in item.value for item in app.info)
    assert app.metric[4].value == "$0.00"


def test_five_tabs_share_profile_and_keep_active_section_when_translated():
    app = AppTest.from_file(APP, default_timeout=30).run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "My financial profile", "Financial assessment", "Emergency simulator",
        "Recovery strategies", "Wealth readiness",
    ]
    app.number_input(key="income").set_value(5000).run()
    app.number_input(key="apr").set_value(12).run()
    app.session_state["navigation"] = "Emergency simulator"
    app.run()
    assert not app.exception
    assert app.session_state["profile"].income == 5000
    ledger = app.dataframe[0].value
    assert ledger.iloc[1]["Interest accrued"] == "$30.00"
    app.selectbox(key="language").select("es").run()
    assert not app.exception
    assert app.session_state["navigation"] == "Simulador de emergencias"
    assert app.number_input(key="apr").value == 12
    assert app.session_state["profile"].income == 5000
    assert app.dataframe[0].value.iloc[1]["Interés del mes"] == "$30.00"


def test_income_loss_controls_and_scenario_specific_amounts_persist():
    app = AppTest.from_file(APP, default_timeout=30).run()
    app.number_input(key="expense_medical").set_value(700).run()
    app.selectbox(key="scenario").select("income_loss").run()
    app.number_input(key="shock_duration").set_value(2).run()
    assert not app.exception
    ledger = app.dataframe[0].value
    assert ledger.iloc[1]["Monthly take-home income"] == "$0.00"
    assert ledger.iloc[2]["Monthly take-home income"] == "$0.00"
    assert ledger.iloc[3]["Monthly take-home income"] == "$4,000.00"
    app.selectbox(key="scenario").select("medical").run()
    assert not app.exception
    assert app.number_input(key="expense_medical").value == 700


def test_recovery_budget_and_wealth_assumptions_recalculate_without_changing_profile():
    app = AppTest.from_file(APP, default_timeout=30).run()
    before = app.dataframe[1].value.copy()
    app.number_input(key="recovery_budget").set_value(1000).run()
    assert not app.exception
    assert not app.dataframe[1].value.equals(before)
    assert app.number_input(key="savings_contribution").value == 400
    app.number_input(key="wealth_return").set_value(0).run()
    assert not app.exception
    end_metric = next(item for item in app.metric if item.label == "Illustrative value at horizon end")
    assert end_metric.value == "$25,000.00"
    app.number_input(key="wealth_monthly").set_value(2000).run()
    assert not app.exception
    assert any("unfunded scenario" in item.value for item in app.warning)


def test_invalid_reserve_and_projection_pause_have_local_errors():
    app = AppTest.from_file(APP, default_timeout=30).run()
    app.number_input(key="reserve").set_value(10000).run()
    assert not app.exception
    assert any("reserve cannot exceed" in item.value for item in app.error)
    app.number_input(key="wealth_pause").set_value(200).run()
    assert not app.exception
    assert any("Check projection" in item.value for item in app.error)
    assert app.metric[0].value == "$1,350.00"  # assessment stays usable


def test_personal_greeting_defaults_and_discreet_bilingual_about_section():
    app = AppTest.from_file(APP, default_timeout=30).run()
    assert not app.exception
    assert any(item.value == "Welcome, Carlos" for item in app.subheader)
    expected = dict(income=4000, essential_expenses=2000, discretionary_expenses=500,
                    debt_balance=3000, minimum_debt_payment=150, savings=4500,
                    savings_contribution=400, target_months=3, apr=24,
                    additional_debt_payment=0)
    for field, value in expected.items():
        assert app.number_input(key=field).value == value
    assert any(item.label == "About FinGuard" for item in app.sidebar.expander)
    assert any(item.value == TEXT["en"]["footer"] for item in app.sidebar.markdown)
    assert all(item.value != TEXT["en"]["footer"] for item in app.caption)
    app.number_input(key="income").set_value(4700).run()
    app.selectbox(key="language").select("es").run()
    assert not app.exception
    assert any(item.value == "Bienvenido, Carlos" for item in app.subheader)
    assert any(item.value == "Tu situación financiera" for item in app.subheader)
    assert any(item.label == "Acerca de FinGuard" for item in app.sidebar.expander)
    assert any(item.value == TEXT["es"]["footer"] for item in app.sidebar.markdown)
    assert app.session_state["profile"].income == 4700
    assert len(app.tabs) == 5


def test_display_identity_is_independent_of_financial_profile_and_reset():
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["user_context"] = UserContext(display_name="Ana")
    app.run()
    assert not app.exception
    assert any(item.value == "Welcome, Ana" for item in app.subheader)
    assert app.metric[0].value == "$1,350.00"
    app.number_input(key="savings").set_value(6000).run()
    app.button(key="reset").click().run()
    assert not app.exception
    assert app.number_input(key="savings").value == 4500
    assert app.session_state["user_context"].display_name == "Ana"
    app.selectbox(key="language").select("es").run()
    assert not app.exception
    assert any(item.value == "Bienvenido, Ana" for item in app.subheader)
