import streamlit as st
import os
import sys

# DEBUG VERSION - NO HEAVY IMPORTS
st.set_page_config(page_title="Debug Mode")

st.title("🛠️ Assistant Debug Mode")
st.success("If you can see this, Streamlit is rendering correctly!")

st.write("### System Info")
st.write(f"- **Python**: {sys.version}")
st.write(f"- **CWD**: {os.getcwd()}")
st.write(f"- **Cloud**: {os.path.exists('/mount/src')}")

st.write("### Files in Root")
st.write(os.listdir("."))

st.info("Attempting a safe import of config...")
try:
    from mf_assistant.config import CLOUD_LIGHT_MODE
    st.write(f"Cloud Light Mode: {CLOUD_LIGHT_MODE}")
    st.write("Logic config imported successfully!")
except Exception as e:
    st.error(f"Error importing config: {e}")

st.warning("If this page is visible, but the main app wasn't, then the issue is in the pipeline imports.")
