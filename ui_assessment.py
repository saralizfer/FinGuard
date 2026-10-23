"""Existing assessment dashboard, reused inside the assessment tab."""
from dataclasses import replace
import plotly.graph_objects as go
import streamlit as st
from finguard.assessment import assess
from finguard.ui_common import card, money, prose


def render_assessment(profile, result, text):
    st.subheader(text["snapshot"])
    with st.container(border=True):
        positive = result.unallocated_cash >= 0
        prose(f"### :material/{'check_circle' if positive else 'info'}: {text['positive_title' if positive else 'negative_title']}")
        prose(text["positive_summary" if positive else "negative_summary"].format(
            amount=money(abs(result.unallocated_cash))))
    row = st.columns(3)
    with row[0]:
        card(text["cash_flow"], money(result.cash_flow), help_text=text["cash_help"])
    with row[1]:
        card(text["unallocated_cash"], money(result.unallocated_cash), help_text=text["available_help"])
    with row[2]:
        card(text["coverage_months"],
                  text["undefined"] if result.coverage_months is None else text["coverage_value"].format(value=result.coverage_months),
                  help_text=text["coverage_help"])
    row = st.columns(3)
    with row[0]:
        card(text["savings_target"], money(result.savings_target), help_text=text["target_help"])
    with row[1]:
        card(text["savings_shortfall"], money(result.savings_shortfall), help_text=text["shortfall_help"])
    with row[2]:
        card(text["debt_payment_ratio"],
                  text["undefined"] if result.debt_payment_ratio is None else f"{result.debt_payment_ratio:.2%}",
                  help_text=text["ratio_help"])

    if profile.additional_debt_payment > 0:
        prose(text["extra_note"].format(extra=money(profile.additional_debt_payment),
                                       available=money(result.unallocated_cash - profile.additional_debt_payment)))

    if result.cash_flow < 0:
        st.warning(text["deficit"].format(amount=money(-result.cash_flow)))
    elif result.unallocated_cash < 0:
        st.warning(text["unfunded"].format(amount=money(-result.unallocated_cash)))
    if result.coverage_months is None:
        st.info(text["zero_obligations"])
    if result.debt_payment_ratio is None:
        st.info(text["zero_income"])
    if profile.debt_balance > 0 and profile.minimum_debt_payment == 0:
        st.warning(text["zero_payment"])
    if result.savings_shortfall > 0:
        st.info(text["shortfall"].format(amount=money(result.savings_shortfall)))
    elif profile.essential_expenses + profile.minimum_debt_payment > 0 and profile.target_months > 0:
        st.success(text["target_met"])

    flow_column, fund_column = st.columns([3, 2], gap="medium")
    with flow_column.container(border=True, height="stretch"):
        st.subheader(text["chart"])
        labels = text["water_labels"]
        chart = go.Figure(go.Waterfall(
            orientation="h", y=labels,
            x=[profile.income, -profile.essential_expenses, -profile.discretionary_expenses,
               -profile.minimum_debt_payment, -profile.savings_contribution, 0],
            measure=["absolute", "relative", "relative", "relative", "relative", "total"],
            customdata=[profile.income, -profile.essential_expenses, -profile.discretionary_expenses,
                        -profile.minimum_debt_payment, -profile.savings_contribution, result.unallocated_cash],
            hovertemplate="%{y}<br>$%{customdata:,.2f}<extra></extra>",
            increasing=dict(marker_color="#0F766E"),
            decreasing=dict(marker_color="#B45309"),
            totals=dict(marker_color="#2563EB"),
            connector=dict(line=dict(color="#94A3B8")),
        ))
        chart.update_layout(height=420, showlegend=False, xaxis_title=text["amount"],
                            xaxis=dict(tickprefix="$", tickformat=",.0f"), yaxis=dict(autorange="reversed", automargin=True),
                            margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(chart, key="cash_flow_chart", alt=text["chart"])
        st.caption(text["chart_note"])

    with fund_column.container(border=True, height="stretch"):
        st.subheader(text["fund_title"])
        if result.savings_target > 0:
            funded = min(profile.savings, result.savings_target)
            fraction = funded / result.savings_target
            ring = go.Figure(go.Pie(
                labels=[text["saved_label"], text["gap_label"]],
                values=[funded, result.savings_shortfall], hole=0.78, sort=False,
                marker=dict(colors=["#0F766E", "#CBD5E1"]), textinfo="none",
                hovertemplate="%{label}<br>$%{value:,.2f}<extra></extra>",
            ))
            ring.update_layout(height=245, showlegend=False,
                               margin=dict(l=10, r=10, t=10, b=10),
                               annotations=[dict(text=f"{fraction:.2%}", x=0.5, y=0.5,
                                                 showarrow=False, font=dict(size=36, color="#0F766E"))])
            st.plotly_chart(ring, key="savings_chart", alt=text["fund_title"])
            st.progress(float(fraction), text=text["fund_progress"].format(percent=fraction * 100))
            prose(text["fund_detail"].format(saved=money(profile.savings), target=money(result.savings_target)))
            if profile.savings > result.savings_target:
                st.caption(text["fund_excess"].format(amount=money(profile.savings - result.savings_target)))
        else:
            st.info(text["fund_zero"])
        if result.coverage_months is not None:
            prose(text["fund_takeaway"].format(months=result.coverage_months))

    st.subheader(text["explore"])
    with st.container(border=True):
        controls, preview = st.columns([2, 3], gap="large")
        with controls:
            st.write(text["explore_help"])
            reduction = st.slider(text["cut"], min_value=0, max_value=100, value=0,
                                  step=5, format="%d%%", key="spending_reduction")
            cut = profile.discretionary_expenses * reduction / 100
            alternative = assess(replace(profile, discretionary_expenses=profile.discretionary_expenses - cut))
            prose(text["explore_result"].format(cut=money(cut), available=money(alternative.unallocated_cash)))
        with preview:
            comparison = go.Figure(go.Bar(
                x=[result.unallocated_cash, alternative.unallocated_cash],
                y=[text["current"], text["alternative"]], orientation="h",
                marker_color=["#64748B", "#0F766E"],
                text=[money(result.unallocated_cash), money(alternative.unallocated_cash)],
                textposition="auto", hovertemplate="%{y}<br>$%{x:,.2f}<extra></extra>",
            ))
            comparison.update_layout(height=240, xaxis_title=text["amount"],
                                     margin=dict(l=10, r=30, t=10, b=10), showlegend=False)
            comparison.add_vline(x=0, line_color="#94A3B8", line_width=1)
            st.plotly_chart(comparison, key="spending_comparison", alt=text["comparison"])
        st.caption(text["explore_note"])

    st.subheader(text["learn"])
    for column, title, body, icon in zip(
        st.columns(2), ("lesson_cash", "lesson_fund"),
        ("lesson_cash_text", "lesson_fund_text"), ("swap_horiz", "savings"),
    ):
        with column.container(border=True, height="stretch"):
            prose(f"### :material/{icon}: {text[title]}")
            st.write(text[body])

    with st.expander(text["formulas"]):
        prose(text["formula_text"])

