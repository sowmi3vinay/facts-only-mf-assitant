"""Root entry point for Streamlit Cloud deployment."""
from __future__ import annotations
import sys
import os

# Ensure the logs are flushed immediately
def log(msg):
    print(f"DEBUG: {msg}")
    sys.stdout.flush()

log("streamlit_app.py starting...")
log(f"CWD: {os.getcwd()}")
log(f"Python Version: {sys.version}")

# Add the current directory to path explicitly
sys.path.insert(0, os.getcwd())

try:
    log("Attempting to import mf_assistant.app...")
    import mf_assistant.app as app
    log("Successfully imported mf_assistant.app.")
except Exception as e:
    log(f"CRITICAL ERROR during import: {e}")
    import traceback
    log(traceback.format_exc())
    sys.exit(1)

log("Executing app logic...")
# Since mf_assistant.app is designed to run as a script, 
# importing it already triggered the Streamlit UI code.
