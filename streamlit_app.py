"""FinGuard: one shared financial profile, five bilingual educational tabs."""

import json
from math import isfinite
from pathlib import Path

import streamlit as st

from finguard.assessment import Profile, assess
from finguard.translations import TEXT
from finguard.ui_assessment import render_assessment
from finguard.ui_simulation import emergency_controls, render_emergency, render_recovery
from finguard.ui_wealth import render_wealth
from finguard.user_context import UserContext

st.set_page_config(page_title="FinGuard", page_icon=":material/account_balance:", layout="wide")

sample = json.loads((Path(__file__).parent / "data" / "sample_profile.json").read_text(encoding="utf-8"))
sample.setdefault("apr", 24.0)
sample.setdefault("additional_debt_payment", 0.0)
for field, value in sample.items():
    st.session_state.setdefault(field, float(value))
st.session_state.setdefault("user_context", UserContext())


def reset_profile() -> None:
    for field, value in sample.items():
        st.session_state[field] = float(value)


with st.sidebar:
    st.title(":material/account_balance: FinGuard")
    previous_language = st.session_state.get("copy_language", "en")
    language_hint = st.session_state.get("language", "en")
    language = st.selectbox(TEXT[language_hint]["language_label"], ["en", "es"],
                            format_func=lambda code: {"en": "English", "es": "Español"}[code], key="language")
    text = TEXT[language]
    # Translate the selected tab by index so a language change keeps the same section.
    if language != previous_language:
        old_tabs = TEXT[previous_language]["tabs"]
        old_selection = st.session_state.get("navigation", old_tabs[0])
        index = old_tabs.index(old_selection) if old_selection in old_tabs else 0
        st.session_state["navigation"] = text["tabs"][index]
    st.session_state["copy_language"] = language
    st.caption(text["workspace"])
    st.subheader(text["guide"])
    st.markdown(text["guide_steps"])
    st.button(text["reset"], on_click=reset_profile, key="reset", icon=":material/restart_alt:", width="stretch")
    with st.expander(text["about_title"], icon=":material/info:"):
        st.write(text["about_demo"])
        st.write(text["about_privacy"])
        st.caption(text["notice"])
        st.write(text["footer"])
        st.write(text["borrowing_assumption"])
        st.write(text["wealth_assumptions"])

with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
    st.title("FinGuard")
    st.badge(text["language_indicator"], color="blue")
st.caption(text["product_subtitle"])
st.markdown(f"**{text['welcome']}** {text['introduction']}")
st.subheader(text["greeting"].format(name=st.session_state["user_context"].display_name))
st.markdown(text["personal_welcome"])

# All controls render on each run to retain stable widget state. Pure financial
# computations are deterministic, small, and cached; tab switches have no side effects.
tabs = st.tabs(text["tabs"], key="navigation", on_change="rerun")
with tabs[0]:
    st.subheader(text["inputs"])
    st.caption(text["input_help"])
    groups = [
        ("budget_group", ("income", "essential_expenses", "discretionary_expenses")),
        ("debt_group", ("debt_balance", "apr", "minimum_debt_payment", "additional_debt_payment")),
        ("savings_group", ("savings", "savings_contribution", "target_months")),
    ]
    values = {}
    for column, (group, fields) in zip(st.columns(3, gap="large"), groups):
        with column.container(border=True, height="stretch"):
            st.markdown(f"### {text[group]}")
            for field in fields:
                step = 0.5 if field in ("apr", "target_months") else 50.0
                values[field] = st.number_input(text[field], min_value=0.0, step=step, format="%.2f",
                                                key=field, help=text[f"{field}_help"])
    profile_error = None
    if any(not isfinite(value) or value < 0 for value in values.values()):
        profile_error = text["invalid_input"]
    elif values["minimum_debt_payment"] > values["debt_balance"]:
        profile_error = text["invalid_debt"]
    if profile_error:
        st.error(profile_error)
        profile = result = None
    else:
        profile = Profile(**values)
        try:
            result = assess(profile)
        except ValueError:
            st.error(text["invalid_input"])
            profile = result = None
    st.session_state["profile"] = profile

with tabs[1]:
    if profile is not None:
        render_assessment(profile, result, text)
    else:
        st.info(text["profile_invalid"])

with tabs[2]:
    shock, horizon = emergency_controls(text)
    if profile is not None:
        emergency = render_emergency(profile, shock, horizon, text)
    else:
        emergency = None
        st.info(text["profile_invalid"])

with tabs[3]:
    if profile is not None:
        render_recovery(profile, shock, horizon, text)
    else:
        st.info(text["profile_invalid"])

with tabs[4]:
    if profile is not None:
        render_wealth(profile, result, emergency, text)
    else:
        st.info(text["profile_invalid"])
