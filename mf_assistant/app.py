"""Streamlit UI for the Facts-Only MF Assistant for Kuvera."""
from __future__ import annotations

import sys
import os

# Ensure the root is in the path
sys.path.insert(0, os.getcwd())

import streamlit as st

# MUST be first Streamlit command
st.set_page_config(page_title="Facts-Only MF Assistant for Kuvera", page_icon=":bar_chart:", layout="wide")

# --- LAZY IMPORTS ---
# We load these inside the app to prevent startup crashes on the cloud
@st.cache_resource
def load_core_modules():
    print("DEBUG: Lazy loading core modules...")
    from mf_assistant.pipeline import answer_query
    from mf_assistant.responder import format_response
    from mf_assistant.retriever import get_retriever
    from mf_assistant import thread_store
    from mf_assistant.prompts import DISCLAIMER, EXAMPLE_QUESTIONS, WELCOME
    from mf_assistant.config import CLOUD_LIGHT_MODE
    return {
        "answer_query": answer_query,
        "format_response": format_response,
        "get_retriever": get_retriever,
        "thread_store": thread_store,
        "WELCOME": WELCOME,
        "DISCLAIMER": DISCLAIMER,
        "EXAMPLES": EXAMPLE_QUESTIONS,
        "LIGHT_MODE": CLOUD_LIGHT_MODE
    }

# Display a loading message while imports happen
with st.spinner("Initializing Assistant..."):
    mods = load_core_modules()

# Extract for convenience
answer_query = mods["answer_query"]
format_response = mods["format_response"]
get_retriever = mods["get_retriever"]
thread_store = mods["thread_store"]
WELCOME = mods["WELCOME"]
DISCLAIMER = mods["DISCLAIMER"]
EXAMPLES = mods["EXAMPLES"]
LIGHT_MODE = mods["LIGHT_MODE"]

if LIGHT_MODE:
    st.info("☁️ Running in **Cloud Light Mode** (Keyword Search enabled for stability).")

st.markdown("""
<style>
button[kind="primary"] {
    background: linear-gradient(135deg, #238636 0%, #2ea043 100%) !important;
    color: white !important;
}
h1 {
    background: -webkit-linear-gradient(45deg, #58a6ff, #3fb950);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
}
.stChatMessage {
    border-radius: 12px !important;
}
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if "current_thread_id" not in st.session_state:
    threads = thread_store.list_threads()
    st.session_state.current_thread_id = threads[0]["thread_id"] if threads else thread_store.create_thread()

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
        if st.button(f"💬 {t['title']}", key=f"sel_{t['thread_id']}", use_container_width=True):
            st.session_state.current_thread_id = t["thread_id"]
            st.rerun()

# --- Main App ---
st.title("Facts-Only MF Assistant for Kuvera")
st.write(WELCOME)
st.caption(DISCLAIMER)

# Load current thread
current_thread = thread_store.get_thread(st.session_state.current_thread_id)
for msg in (current_thread["messages"] if current_thread else []):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- User Input ---
cols = st.columns(len(EXAMPLES))
for i, q in enumerate(EXAMPLES):
    with cols[i]:
        if st.button(q, key=f"ex_{i}"):
            st.session_state.query = q

with st.form("query_form", clear_on_submit=True):
    query = st.text_input("Ask a question:", value=st.session_state.query or "")
    submit = st.form_submit_button("Ask", type="primary")

if submit and query.strip():
    st.session_state.query = ""
    with st.chat_message("user"):
        st.markdown(query)
    thread_store.add_message(st.session_state.current_thread_id, "user", query)
    
    with st.spinner("Analyzing official sources..."):
        response = answer_query(query, history=current_thread["messages"])
        ans_text = format_response(response)

    thread_store.add_message(st.session_state.current_thread_id, "assistant", ans_text)
    with st.chat_message("assistant"):
        st.markdown(ans_text)
    st.rerun()
