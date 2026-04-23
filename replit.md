# Workspace

## Overview

This project hosts the **Facts-Only MF Assistant for Kuvera**, a Python Streamlit
RAG chatbot in `mf_assistant/` that answers only factual mutual fund questions
from official sources (AMC factsheets/SIDs, AMFI, SEBI, Kuvera help). It refuses
investment advice, recommendations, return predictions, and any input containing
PII.

## Run

The app runs via the workflow `Start application`:

```bash
streamlit run mf_assistant/app.py --server.port 5000
```

## Project files

See `mf_assistant/README.md` for full structure, setup, and how to load real
sources via `ingest.py` + `build_index.py`.

## Notes

- The repo also contains a pnpm workspace scaffold (`artifacts/`, `lib/`) from
  the template; it is not used by the Streamlit app.
