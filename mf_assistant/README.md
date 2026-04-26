# Facts-Only MF Assistant for Kuvera

This project is a facts-only mutual fund FAQ assistant using official AMC, AMFI, and SEBI sources with deterministic, citation-backed responses.

A small, RAG-based Streamlit chatbot that answers **only factual** questions
about a limited set of mutual fund schemes, using **official public sources**
only (AMC factsheets/SIDs, AMFI, SEBI, and Kuvera help pages).

> **Facts-only. No investment advice.**

## What it answers

- expense ratio
- exit load
- minimum SIP
- lock-in period
- benchmark
- riskometer
- how to download statements / capital gains statement

## What it refuses

- investment advice
- buy / sell suggestions
- recommendations
- portfolio allocation
- "which fund is better"
- return prediction / performance comparison
- any input containing PII (PAN, Aadhaar, account numbers, OTPs, phone, email)

## Project structure

```
mf_assistant/
├── app.py            # Streamlit UI
├── sources.csv       # Approved official URLs (the only sources allowed)
├── ingest.py         # Download + parse pipeline
├── parser.py         # HTML and PDF text extraction
├── chunker.py        # Text chunking
├── build_index.py    # TF-IDF index builder (with demo fallback data)
├── retriever.py      # Loads the index and runs cosine search
├── router.py         # Decides answer vs refuse (PII / advice)
├── responder.py      # Composes grounded, ≤3-sentence answers + 1 source
├── prompts.py        # System rules, refusal text, welcome text
├── README.md
└── sample_qa.md
```

## Setup

```bash
# Install dependencies (already installed in this Replit project):
pip install streamlit scikit-learn numpy pandas requests beautifulsoup4 pypdf
```

## Run

The Streamlit app is wired up to a workflow in this Replit project. To run it
manually:

```bash
streamlit run mf_assistant/app.py --server.port 5000
```

On first launch the app builds an index from **demo data** (see
`DEMO_CHUNKS` in `build_index.py`) so you can try it immediately.

## Loading real sources

1. Edit `sources.csv` and add only **official** URLs (AMC, AMFI, SEBI, Kuvera
   help). Remove the demo rows.
2. Download and parse:
   ```bash
   python -m mf_assistant.ingest
   ```
3. Build the retrieval index:
   ```bash
   python -m mf_assistant.build_index
   ```
4. Restart the Streamlit app.

> The `TODO` markers in `sources.csv` and `build_index.py` show exactly where
> manual configuration is needed.

## Safety

- No PII is collected or stored. The router refuses any input that looks like
  PAN, Aadhaar, phone, email, OTP, or account number.
- Answers are **extractive**: built from retrieved chunks only, capped at 3
  sentences, with exactly one source link and a `Last updated from sources:`
  date.
- No third-party blogs are allowed in `sources.csv`.

## Sample Q&A

See `sample_qa.md` for example queries and expected behaviors.
