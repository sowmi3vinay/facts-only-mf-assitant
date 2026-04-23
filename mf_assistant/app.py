"""Streamlit UI for the Facts-Only MF Assistant for Kuvera."""
from __future__ import annotations

import streamlit as st

from mf_assistant.pipeline import answer_query
from mf_assistant.prompts import DISCLAIMER, EXAMPLE_QUESTIONS, WELCOME
from mf_assistant.responder import format_response
from mf_assistant.retriever import get_retriever


st.set_page_config(page_title="Facts-Only MF Assistant for Kuvera", page_icon=":bar_chart:")

st.title("Facts-Only MF Assistant for Kuvera")
st.write(WELCOME)
st.caption(DISCLAIMER)

st.markdown("**Try one of these:**")
cols = st.columns(len(EXAMPLE_QUESTIONS))
if "query" not in st.session_state:
    st.session_state.query = ""
for i, q in enumerate(EXAMPLE_QUESTIONS):
    with cols[i]:
        if st.button(q, key=f"ex_{i}"):
            st.session_state.query = q

query = st.text_input(
    "Ask a factual question about an approved scheme:",
    value=st.session_state.query,
    placeholder="e.g. What is the exit load on HDFC Flexi Cap Fund?",
)

ANY_SCHEME = "Any scheme"
retriever = get_retriever()
scheme_options = [ANY_SCHEME] + retriever.list_schemes()
scheme_choice = st.selectbox(
    "Limit answer to scheme (optional)",
    options=scheme_options,
    index=0,
    help="When set, only documents for the selected fund are used to answer.",
)

submit = st.button("Ask", type="primary")

if submit and query.strip():
    scheme_filter = None if scheme_choice == ANY_SCHEME else scheme_choice
    response = answer_query(query, scheme_filter=scheme_filter)

    with st.container(border=True):
        if response.kind == "refuse":
            st.warning(format_response(response))
        elif response.kind == "not_found":
            st.info(format_response(response))
        else:
            st.markdown(format_response(response))

with st.expander("What this assistant will and won't answer"):
    st.markdown(
        "- **Will answer:** expense ratio, exit load, minimum SIP, lock-in period, "
        "benchmark, riskometer, how to download statements / capital gains statement.\n"
        "- **Will refuse:** investment advice, buy/sell suggestions, recommendations, "
        "portfolio allocation, 'which fund is better', return predictions, performance "
        "comparisons.\n"
        "- **Sources:** AMC factsheets/SIDs, AMFI, SEBI, and official Kuvera help pages only."
    )
