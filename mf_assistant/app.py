"""Streamlit UI for the Facts-Only MF Assistant for Kuvera."""
from __future__ import annotations

import sys
import os

# Trace startup
print("DEBUG: app.py starting...")
print(f"DEBUG: Python version: {sys.version}")
print(f"DEBUG: CWD: {os.getcwd()}")

import streamlit as st

print("DEBUG: Streamlit imported. Loading pipeline...")
from mf_assistant.pipeline import answer_query
print("DEBUG: Pipeline loaded. Loading prompts...")
from mf_assistant.prompts import DISCLAIMER, EXAMPLE_QUESTIONS, WELCOME
print("DEBUG: Prompts loaded. Loading responder...")
from mf_assistant.responder import format_response
print("DEBUG: Responder loaded. Loading retriever...")
from mf_assistant.retriever import get_retriever
print("DEBUG: Retriever loaded. Loading thread_store...")
from mf_assistant import thread_store
print("DEBUG: All imports completed successfully.")

st.set_page_config(page_title="Facts-Only MF Assistant for Kuvera", page_icon=":bar_chart:", layout="wide")

st.markdown("""
<style>
button[kind="primary"] {
    background: linear-gradient(135deg, #238636 0%, #2ea043 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(46, 160, 67, 0.4) !important;
}
h1 {
    background: -webkit-linear-gradient(45deg, #58a6ff, #3fb950);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
}
.stChatMessage {
    border-radius: 12px !important;
    padding: 10px !important;
    margin-bottom: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if "current_thread_id" not in st.session_state:
    threads = thread_store.list_threads()
    if threads:
        st.session_state.current_thread_id = threads[0]["thread_id"]
    else:
        st.session_state.current_thread_id = thread_store.create_thread()

if "query" not in st.session_state:
    st.session_state.query = ""

# --- Sidebar ---
with st.sidebar:
    st.title("🗂️ Chat Sessions")
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.current_thread_id = thread_store.create_thread()
        st.session_state.query = ""
        st.rerun()
    
    st.divider()
    
    threads = thread_store.list_threads()
    for t in threads:
        is_active = t["thread_id"] == st.session_state.current_thread_id
        cols = st.columns([0.8, 0.2])
        with cols[0]:
            btn_label = f"💬 {t['title']}" if not is_active else f"👉 {t['title']}"
            if st.button(btn_label, key=f"sel_{t['thread_id']}", use_container_width=True):
                st.session_state.current_thread_id = t["thread_id"]
                st.rerun()
        with cols[1]:
            if st.button("🗑️", key=f"del_{t['thread_id']}", help="Delete thread"):
                thread_store.delete_thread(t["thread_id"])
                # If we deleted the active thread, pick another one
                if is_active:
                    remaining = thread_store.list_threads()
                    st.session_state.current_thread_id = remaining[0]["thread_id"] if remaining else thread_store.create_thread()
                st.rerun()

# --- Main App ---
st.title("Facts-Only MF Assistant for Kuvera")
st.write(WELCOME)
st.caption(DISCLAIMER)

# Load current thread
current_thread = thread_store.get_thread(st.session_state.current_thread_id)
if not current_thread:
    st.session_state.current_thread_id = thread_store.create_thread()
    current_thread = thread_store.get_thread(st.session_state.current_thread_id)

# Display Message History
for msg in current_thread["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- User Input ---
st.markdown("**Try one of these:**")
cols = st.columns(len(EXAMPLE_QUESTIONS))
for i, q in enumerate(EXAMPLE_QUESTIONS):
    with cols[i]:
        if st.button(q, key=f"ex_{i}"):
            st.session_state.query = q

with st.form("query_form", clear_on_submit=True):
    query = st.text_input(
        "Ask a factual question about an approved scheme:",
        value=st.session_state.query if st.session_state.query else "",
        placeholder="e.g. What is the exit load on HDFC Flexi Cap Fund?",
    )

    ANY_SCHEME = "Any scheme"
    
    @st.cache_resource
    def get_cached_retriever():
        return get_retriever()
        
    retriever = get_cached_retriever()
    scheme_options = [ANY_SCHEME] + retriever.list_schemes()
    scheme_choice = st.selectbox(
        "Limit answer to scheme (optional)",
        options=scheme_options,
        index=0,
        help="When set, only documents for the selected fund are used to answer.",
    )

    submit = st.form_submit_button("Ask", type="primary")

if submit and query.strip():
    # Reset suggestion state
    st.session_state.query = ""
    
    # Show user message immediately
    with st.chat_message("user"):
        st.markdown(query)
    
    # Save user message
    thread_store.add_message(st.session_state.current_thread_id, "user", query)
    
    scheme_filter = None if scheme_choice == ANY_SCHEME else scheme_choice
    
    with st.spinner("Analyzing official sources..."):
        response = answer_query(query, scheme_filter=scheme_filter, history=current_thread["messages"])
        ans_text = format_response(response)

    # Save assistant message
    thread_store.add_message(st.session_state.current_thread_id, "assistant", ans_text)
    
    # Display assistant response
    with st.chat_message("assistant"):
        if response.kind == "refuse":
            st.warning(ans_text)
        elif response.kind == "not_found":
            st.info(ans_text)
        else:
            st.markdown(ans_text)
    
    st.rerun()

with st.expander("What this assistant will and won't answer"):
    st.markdown(
        "- **Will answer:** expense ratio, exit load, minimum SIP, lock-in period, "
        "benchmark, riskometer, how to download statements / capital gains statement.\n"
        "- **Will refuse:** investment advice, buy/sell suggestions, recommendations, "
        "portfolio allocation, 'which fund is better', return predictions, performance "
        "comparisons.\n"
        "- **Sources:** AMC factsheets/SIDs, AMFI, SEBI, and official Kuvera help pages only."
    )
