---
title: Facts-Only Mutual Fund FAQ Assistant
emoji: 📊
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: 1.56.0
app_file: app.py
pinned: false
license: mit
---

# Facts-Only Mutual Fund FAQ Assistant (Kuvera Context)
This repository includes pre-built data (chunks, index, facts) so the application can run without rebuilding the pipeline.

## Overview
The **Facts-Only Mutual Fund FAQ Assistant** is a specialized information retrieval system designed to provide accurate, non-generative answers to questions about mutual fund schemes. The assistant uses a small-corpus retrieval pipeline over official sources, with deterministic extraction for common mutual-fund fact fields to improve precision. It is built to ensure 100% factual groundedness by relying exclusively on official documentation and removing probabilistic elements from the final response generation.

*   **Facts-Only:** No hallucinated content; every answer is derived from verified data.
*   **Official Sources Only:** Data is pulled directly from AMC, AMFI, and SEBI portals.
*   **No Investment Advice:** The system strictly refuses to provide recommendations, comparisons, or personalized financial guidance.

## Deployment Modes
- **Local Mode**: Uses the full retrieval stack, including `sentence-transformers` for semantic vector search and `FAISS` for nearest-neighbor retrieval.
- **Cloud Light Mode**: Automatically activated on Streamlit Community Cloud. It uses a lightweight retrieval engine (TF-IDF keyword search) to ensure fast startup and avoid memory-related crashes on limited cloud resources. All core features (structured facts, memory, refusals) remain fully functional.

---

## Scope
The assistant is currently optimized for a select group of high-priority HDFC Mutual Fund schemes.

### AMC: HDFC Mutual Fund
### Schemes Covered:
1.  **HDFC Top 100 Fund**
2.  **HDFC Flexi Cap Fund**
3.  **HDFC ELSS Tax Saver Fund**
4.  **HDFC Mid Cap Fund**
5.  **HDFC Small Cap Fund**

---

## Data Sources
The system's knowledge base is constructed from the following authoritative sources:
*   **HDFC Scheme Pages:** Official product details and performance disclosures.
*   **KIM PDFs:** Key Information Memorandums providing legal and technical specifics.
*   **AMFI:** Association of Mutual Funds in India investor education resources.
*   **SEBI:** Securities and Exchange Board of India regulatory guidelines.
*   **Kuvera Help Pages:** Platform-specific operational guidance.

---

## Architecture
The system employs a **Hybrid Retrieval-Backed** architecture to prioritize precision over fluency.

### 1. Structured Extraction for Precision
For common mutual-fund fact fields (e.g., exit load, SIP amounts, benchmarks), the system uses a structured extraction layer that lookups pre-validated facts from `facts.jsonl`, ensuring $O(1)$ precision.

### 2. Retrieval Fallback for Broader Factual Queries
For more complex or descriptive queries, the system utilizes a retrieval fallback mechanism:
*   **Vector Search:** Powered by FAISS and `sentence-transformers`.
*   **Keyword Search:** BM25/TF-IDF for terminology matching.

### 3. Controlled LLM Integration
While the core response generation remains deterministic, the system optionally uses an LLM (e.g., Llama 3 via Groq) for **Contextual Query Rewriting**. This layer converts follow-up queries like "What about its benchmark?" into standalone questions ("What is the benchmark for HDFC Flexi Cap Fund?") using conversational memory.

### 4. Deterministic Core
The final output for structured facts is generated via code-based templates, bypassing probabilistic LLM generation to ensure 100% fidelity to source documents. An optional "polishing" layer can be enabled, which is subject to strict entity and numeric grounding checks to prevent hallucinations.

---

## Features
*   **Factual Q&A:** Instant answers for `exit_load`, `SIP`, `benchmark`, `lock-in`, `expense_ratio`, and `riskometer`.
*   **One Source Link:** Every response is accompanied by exactly one link to the official source document.
*   **Memory-based Follow-ups:** Maintains context for the last 3–5 messages to handle coreferences (e.g., "What about its exit load?").
*   **Multi-thread Sessions:** Independent chat threads identified by `thread_id` to keep conversations isolated.
*   **Refusal Handling:** Robust classification to reject out-of-scope or sensitive (PII/Advice) queries.

---

## Query Handling
The system classifies and routes queries into four primary categories:
1.  **Structured Extraction Queries:** Directly addressed via the pre-validated fact store.
2.  **Retrieval Fallback Queries:** Addressed via the hybrid semantic search engine.
3.  **Follow-up Queries:** Rewritten using the memory layer to become standalone retrieval queries.
4.  **Refusal Queries:** Handled by the safety layer to provide a standardized refusal message and redirect to SEBI.

---

## Setup Instructions

### 1. Install Dependencies
Ensure you have Python 3.9+ and install the required packages:
```bash
pip install -r requirements.txt
```

### 2. Run the Application
Start the Streamlit interface:
```bash
streamlit run mf_assistant/app.py
```

### 3. Optional: Rebuild Data
If you modify `sources.csv`, update the system's knowledge base:
```bash
python -m mf_assistant.ingest
python -m mf_assistant.chunker
python -m mf_assistant.build_facts
python -m mf_assistant.build_index
```

---

## Example Queries
1.  "What is the exit load of HDFC Mid Cap Fund?"
2.  "What is the minimum SIP for HDFC Top 100 Fund?"
3.  "Does HDFC ELSS Tax Saver Fund have a lock-in period?"
4.  "How do I download my capital gains report from Kuvera?"
5.  "Should I invest in HDFC Small Cap Fund for high returns?" (Triggers Refusal)

---

## Known Limitations
*   **Limited Scope:** Currently only covers the 5 listed HDFC schemes.
*   **No Real-time Updates:** Knowledge is as current as the last ingestion cycle.
*   **No Personalized Advice:** Cannot analyze user portfolios or suggest allocations.

---

## Design Choice: Controlled LLM Usage
Traditional RAG pipelines often suffer from hallucinations because the LLM is responsible for synthesizing final answers. In this project, we re-introduced the LLM only where it adds significant value without compromising accuracy:
1.  **Query Rewriting:** LLMs are excellent at understanding context and coreferences. Using them to rewrite queries significantly improves the success rate of retrieval for follow-up questions.
2.  **Strict Grounding:** Any LLM usage in the output path is guarded by:
    *   **Entity Check:** Every capitalized word in the output must exist in the source context.
    *   **Numeric Check:** Every number or percentage must exist in the source context.
    *   **Fallback:** The system always maintains a rule-based fallback to ensure availability even if the LLM layer is unavailable.

---

## Disclaimer
**Facts-only. No investment advice.** All information is provided for educational purposes based on official scheme documents. Always consult with a SEBI-registered investment advisor before making financial decisions.
