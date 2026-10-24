"""Independent hypothetical goal planning with transparent return assumptions."""

from math import isfinite

import plotly.graph_objects as go
import streamlit as st

from finguard.ui_common import card, chart_style, money, prose, render_feedback
from finguard.feedback import wealth_feedback
from finguard.wealth import project
from finguard.simulation import simulate

cached_project = st.cache_data(max_entries=128, show_spinner=False, scope="session")(project)


def render_wealth(profile, assessment, emergency, text):
    st.subheader(text["tabs"][4])
    st.write(text["wealth_help"])
    for column, key, value in zip(st.columns(3),
                                  ["savings_shortfall", "debt_line", "unallocated_cash"],
                                  [assessment.savings_shortfall, profile.debt_balance, assessment.unallocated_cash]):
        with column:
            card(text[key], money(value))
    st.caption(text["minimum_debt_payment"] + ": " + money(profile.minimum_debt_payment))
    st.selectbox(text["goals"], ["home", "long_savings", "portfolio", "retirement"],
                 format_func=lambda value: text[value], key="wealth_goal")
    left, right = st.columns(2)
    with left:
        goal = st.number_input(text["goal_amount"], min_value=0.0, value=50000.0, step=1000.0, key="goal_amount")
        initial = st.number_input(text["initial_amount"], min_value=0.0, value=1000.0, step=100.0, key="wealth_initial")
        monthly = st.number_input(text["monthly_investment"], min_value=0.0, value=200.0, step=25.0, key="wealth_monthly")
    with right:
        years = st.number_input(text["years"], min_value=1, max_value=50, value=10, key="wealth_years")
        rate = st.number_input(text["annual_return"], min_value=-99.0, max_value=100.0,
                               value=5.0, step=0.5, key="wealth_return")
        pause = st.number_input(text["pause"], min_value=0, max_value=600, value=3,
                                help=text["pause_help"], key="wealth_pause")
    try:
        if not isfinite(goal) or goal < 0:
            raise ValueError("Invalid goal")
        assumed = cached_project(initial, monthly, int(years), rate)
        zero = cached_project(initial, monthly, int(years), 0)
        paused = cached_project(initial, monthly, int(years), rate, int(pause))
    except ValueError:
        st.error(text["projection_invalid"])
        return
    # Reuse the validated monthly engine without an emergency to cap the extra
    # payment by cash available and debt still owed after interest/minimum payment.
    # Preserve the assessment's definition of cash after PLANNED savings.
    try:
        feasible_extra = simulate(profile, horizon=1).months[1].additional_payment
    except ValueError:
        st.error(text["simulation_invalid"])
        return
    capacity = max(0, assessment.unallocated_cash - feasible_extra)
    if monthly > capacity:
        st.warning(text["capacity_warning"])
    final = assumed[-1]
    render_feedback(wealth_feedback(final.value, goal, monthly, capacity), text)
    reached = next((row.month for row in assumed if row.value >= goal), None)
    items = [("projection_end", money(final.value)), ("contributed", money(final.contributed)),
             ("growth", money(final.value - final.contributed)),
             ("goal_timing", text["not_reached"] if reached is None else str(reached))]
    for start in (0, 2):
        for column, (key, value) in zip(st.columns(2), items[start:start + 2]):
            with column:
                card(text[key], value)
    chart = go.Figure()
    for rows, name, color in ((zero, "contributions_only", "#64748B"),
                               (assumed, "assumed_return", "#0F766E"),
                               (paused, "paused_path", "#7C3AED")):
        chart.add_scatter(x=[row.month for row in rows], y=[row.value for row in rows],
                          mode="lines", name=text[name], line=dict(color=color, width=3),
                          hovertemplate=f"{text[name]}: $%{{y:,.2f}}<extra></extra>")
    chart.add_hline(y=goal, line_dash="dot", line_color="#A16207")
    st.subheader(text["projection"])
    st.plotly_chart(chart_style(chart, text, 400), key="wealth_projection", alt=text["projection"])
    st.info(text["wealth_assumptions"])
    st.caption(text["pause_help"])
    if emergency is not None:
        prose(text["tradeoff_projection"].format(difference=money(final.value - paused[-1].value),
                                                 interest=money(emergency.total_interest),
                                                 months=len(emergency.months) - 1))
