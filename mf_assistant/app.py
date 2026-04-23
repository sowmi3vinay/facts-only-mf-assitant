"""Streamlit UI for the Facts-Only MF Assistant for Kuvera."""
from __future__ import annotations

import streamlit as st

from mf_assistant.prompts import (
    DISCLAIMER,
    EXAMPLE_QUESTIONS,
    REFUSAL_ADVICE,
    REFUSAL_PII,
    WELCOME,
)
from mf_assistant.responder import compose, format_for_display
from mf_assistant.retriever import get_retriever
from mf_assistant.router import route


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
    placeholder="e.g. What is the exit load on Demo Flexi Cap Fund?",
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
    decision = route(query)

    with st.container(border=True):
        if decision.decision == "refuse_pii":
            st.warning(REFUSAL_PII)
        elif decision.decision == "refuse_advice":
            st.warning(REFUSAL_ADVICE)
        elif decision.decision == "refuse_scope":
            st.info("Please enter a factual question about an approved scheme.")
        else:
            scheme_filter = None if scheme_choice == ANY_SCHEME else scheme_choice
            hits = retriever.search(query, top_k=4, scheme_name=scheme_filter)
            if not hits and scheme_filter:
                st.info(
                    f"No indexed documents matched **{scheme_filter}** for this question. "
                    "Try 'Any scheme' or rephrase."
                )
            else:
                answer = compose(hits, query=query)
                st.markdown(format_for_display(answer))

with st.expander("What this assistant will and won't answer"):
    st.markdown(
        "- **Will answer:** expense ratio, exit load, minimum SIP, lock-in period, "
        "benchmark, riskometer, how to download statements / capital gains statement.\n"
        "- **Will refuse:** investment advice, buy/sell suggestions, recommendations, "
        "portfolio allocation, 'which fund is better', return predictions, performance "
        "comparisons.\n"
        "- **Sources:** AMC factsheets/SIDs, AMFI, SEBI, and official Kuvera help pages only."
    )
