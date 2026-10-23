"""Small shared presentation helpers; no financial rules live here."""

import streamlit as st


def money(value: float) -> str:
    return f"{'-' if value < 0 else ''}${abs(value):,.2f}"


def prose(value: str) -> None:
    # Dollar-delimited numbers are currency, never inline LaTeX.
    st.markdown(value.replace("$", r"\$"))


def card(label: str, value: str, help_text: str | None = None) -> None:
    with st.container(border=True, height="stretch"):
        # A native Markdown heading wraps rather than ellipsizing like metric labels.
        st.markdown(f"**{label}**")
        if len(value) > 22:
            st.markdown(value)
            if help_text:
                st.caption(help_text)
        else:
            st.metric(label, value, label_visibility="collapsed", help=help_text)


def chart_style(figure, text: dict, height: int = 360):
    figure.update_layout(height=height, margin=dict(l=15, r=25, t=20, b=30),
                         hovermode="x unified",
                         legend=dict(orientation="h", y=-0.28, x=0, xanchor="left", yanchor="top"),
                         xaxis_title=text["month"], yaxis_title=text["amount"])
    figure.update_yaxes(tickprefix="$", tickformat=",.0f", automargin=True)
    return figure
