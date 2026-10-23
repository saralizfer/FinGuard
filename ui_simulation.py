"""Emergency controls, monthly ledgers, and recovery comparisons."""

from dataclasses import asdict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from finguard.recovery import STRATEGIES, compare_strategies
from finguard.simulation import Shock, simulate
from finguard.ui_common import card, chart_style, money

cached_simulate = st.cache_data(max_entries=64, show_spinner=False, scope="session")(simulate)
cached_compare = st.cache_data(max_entries=64, show_spinner=False, scope="session")(compare_strategies)


def month_text(value, text, missing="not_reached"):
    return text[missing] if value is None else f"{value}"


def emergency_controls(text):
    st.subheader(text["tabs"][2])
    st.write(text["simulate_help"])
    choices = ["medical", "vehicle", "income_loss", "reduced_income", "living_cost"]
    left, right = st.columns(2)
    with left:
        scenario = st.selectbox(text["scenario"], choices, format_func=lambda value: text[value], key="scenario")
        expense = increase = reduction = 0.0
        duration = 1
        if scenario in ("medical", "vehicle"):
            expense = st.number_input(text["shock_amount"], min_value=0.0, value=2500.0,
                                      step=100.0, key=f"expense_{scenario}", persist_state="session")
        if scenario == "reduced_income":
            reduction = st.slider(text["reduction_percent"], 0, 100, 30,
                                  key="income_reduction", persist_state="session") / 100
        if scenario == "income_loss":
            reduction = 1.0
        if scenario == "living_cost":
            increase = st.number_input(text["expense_increase"], min_value=0.0, value=300.0,
                                       step=50.0, key="living_increase", persist_state="session")
    with right:
        if scenario not in ("medical", "vehicle"):
            duration = st.number_input(text["duration"], min_value=1, max_value=120, value=3,
                                       key="shock_duration", persist_state="session")
        horizon = st.number_input(text["horizon"], min_value=24, max_value=120, value=24, key="horizon")
    return Shock(expense, reduction, increase, int(duration)), int(horizon)


def render_emergency(profile, shock, horizon, text):
    if horizon < shock.duration:
        st.error(text["duration_error"])
        return None
    try:
        result = cached_simulate(profile, shock, horizon)
    except ValueError:
        st.error(text["simulation_invalid"])
        return None
    end = result.months[-1]
    shock_total = shock.expense + (profile.income * shock.income_reduction + shock.essential_increase) * shock.duration
    entries = [
        ("initial_savings", money(profile.savings)), ("shock_total", money(shock_total)),
        ("end_savings", money(end.savings)), ("end_debt", money(end.debt)),
        ("borrowing", money(result.total_borrowing)), ("interest_paid", money(result.total_interest_paid)),
        ("interest_accrued", money(result.total_interest)),
        ("depletion", month_text(result.depletion_month, text, "not_depleted")),
        ("recovery_time", month_text(result.recovery_month, text)),
    ]
    for start in range(0, len(entries), 2):
        for column, (label, value) in zip(st.columns(2), entries[start:start + 2]):
            with column:
                card(text[label], value)
    st.caption(text["interest_note"])
    st.caption(text["baseline_policy"])
    st.info(text["fixed_payment_assumption"])
    st.info(text["borrowing_assumption"])
    st.caption(text["recovery_definition"])
    timeline = go.Figure()
    for attribute, label, color in (("savings", "savings_line", "#0F766E"), ("debt", "debt_line", "#2563EB")):
        timeline.add_scatter(x=[row.month for row in result.months],
                             y=[getattr(row, attribute) for row in result.months],
                             name=text[label], mode="lines", line=dict(color=color, width=3),
                             hovertemplate=f"{text[label]}: $%{{y:,.2f}}<extra></extra>")
    st.subheader(text["timeline"])
    st.plotly_chart(chart_style(timeline, text), key="emergency_timeline", alt=text["timeline"])
    cash = go.Figure(go.Bar(x=[row.month for row in result.months[1:]],
                            y=[row.cash_flow for row in result.months[1:]],
                            marker_color=["#0F766E" if row.cash_flow >= 0 else "#BE123C" for row in result.months[1:]],
                            hovertemplate="$%{y:,.2f}<extra></extra>"))
    st.subheader(text["cash_flow_sim"])
    st.plotly_chart(chart_style(cash, text, 260), key="emergency_cash", alt=text["cash_flow_sim"])
    with st.expander(text["ledger"]):
        data = []
        aliases = {"savings": "closing_savings", "savings_contribution": "ledger_contribution",
                   "unallocated_cash": "unallocated", "cash_flow": "cash_flow_sim"}
        for row in result.months:
            data.append({text[aliases.get(key, key)]: (value if key == "month" else money(value))
                         for key, value in asdict(row).items()})
        st.dataframe(pd.DataFrame(data), hide_index=True, alt=text["ledger"])
    return result


def render_recovery(profile, shock, horizon, text):
    st.subheader(text["tabs"][3])
    st.write(text["recovery_help"])
    st.caption(text["scenario"] + ": " + text[st.session_state["scenario"]])
    st.caption(text["fixed_payment_assumption"])
    left, right = st.columns(2)
    with left:
        budget = st.number_input(text["budget"], min_value=0.0,
                                 value=float(profile.savings_contribution + profile.additional_debt_payment),
                                 step=50.0, key="recovery_budget", help=text["budget_help"], persist_state="session")
    with right:
        reserve = st.number_input(text["reserve"], min_value=0.0, value=0.0, step=100.0,
                                  key="reserve", help=text["reserve_help"], persist_state="session")
    if reserve > profile.target_months * (profile.essential_expenses + profile.minimum_debt_payment):
        st.error(text["reserve_error"])
        return
    if horizon < shock.duration:
        st.error(text["duration_error"])
        return
    try:
        results = cached_compare(profile, shock, horizon, budget, reserve)
    except ValueError:
        st.error(text["simulation_invalid"])
        return
    summary = []
    for strategy, result in results.items():
        summary.append({text["strategy"]: text[strategy],
                        text["target_time"]: month_text(result.target_month, text),
                        text["recovery_time"]: month_text(result.recovery_month, text),
                        text["end_savings"]: money(result.months[-1].savings),
                        text["end_debt"]: money(result.months[-1].debt),
                        text["interest_paid"]: money(result.total_interest_paid),
                        text["interest_accrued"]: money(result.total_interest),
                        text["borrowing"]: money(result.total_borrowing)})
    st.dataframe(pd.DataFrame(summary), hide_index=True, alt=text["tabs"][3])
    st.caption(text["interest_note"])
    st.caption(text["recovery_definition"])
    for attribute, title in (("savings", "comparison_savings"), ("debt", "comparison_debt")):
        chart = go.Figure()
        for strategy, color in zip(STRATEGIES, ["#0F766E", "#2563EB", "#7C3AED"]):
            result = results[strategy]
            chart.add_scatter(x=[row.month for row in result.months],
                              y=[getattr(row, attribute) for row in result.months],
                              mode="lines", name=text[strategy], line=dict(color=color, width=3),
                              hovertemplate=f"{text[strategy]}: $%{{y:,.2f}}<extra></extra>")
        st.subheader(text[title])
        st.plotly_chart(chart_style(chart, text), key=f"recovery_{attribute}", alt=text[title])
    st.subheader(text["snapshot12"])
    snapshots = []
    for strategy, result in results.items():
        for month in (12, 24):
            row = result.months[month]
            snapshots.append({text["strategy"]: text[strategy], text["month"]: month,
                              text["closing_savings"]: money(row.savings), text["debt"]: money(row.debt),
                              text["cumulative_interest"]: money(sum(item.interest for item in result.months[:month + 1])),
                              text["cash_flow_sim"]: money(row.cash_flow), text["unallocated"]: money(row.unallocated_cash)})
    st.dataframe(pd.DataFrame(snapshots), hide_index=True, alt=text["snapshot12"])
    for column, label in zip(st.columns(3), ["trade_savings", "trade_debt", "trade_balanced"]):
        with column.container(border=True, height="stretch"):
            st.write(text[label])
