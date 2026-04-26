# Facts-Only MF Assistant – Phase-wise Architecture

## Project Overview
The **Facts-Only Mutual Fund FAQ Assistant** is a high-precision, compliance-first information retrieval system designed to provide accurate answers to queries regarding HDFC Mutual Fund schemes. The assistant uses a small-corpus retrieval pipeline over official sources, with deterministic extraction for common mutual-fund fact fields to improve precision. The system utilizes a hybrid retrieval-backed architecture, where Large Language Models (LLMs) are strictly confined to query understanding (rewriting) while maintaining a structured extraction path for core facts to eliminate hallucinations.

---

## Phase 1: Scope & Corpus
The system focuses on a curated selection of HDFC Mutual Fund schemes to ensure high data quality and relevance.

*   **AMC:** HDFC Mutual Fund
*   **Schemes:**
    *   HDFC Top 100 Fund
    *   HDFC Flexi Cap Fund
    *   HDFC ELSS Tax Saver Fund
    *   HDFC Mid Cap Fund
    *   HDFC Small Cap Fund
*   **Sources:**
    *   Official HDFC scheme pages and Key Information Memorandums (KIM).
    *   Regulatory and auxiliary data from AMFI and SEBI.
    *   Help resources from Kuvera.

---

## Phase 2: Ingestion
Automated data gathering from authoritative sources.

*   **Source Management:** Allowlisted URLs are managed in `sources.csv`.
*   **Data Fetching:** Python-based crawlers fetch HTML content and download PDF documents.
*   **Storage:** Raw data is persisted for auditing, and processed data is stored in a structured filesystem layout.

---

## Phase 3: Parsing & Normalization
Converting heterogeneous data formats into a unified internal representation.

*   **Extraction:** Clean text extraction from HTML (BeautifulSoup) and PDFs (PyMuPDF/pdfplumber).
*   **Metadata Preservation:** Every parsed document retains:
    *   `source_url`: Original location of the data.
    *   `scheme_name`: The specific mutual fund scheme.
    *   `page_type`: Nature of the content (e.g., Factsheet, FAQ, Legal).
    *   `last_updated`: Timestamp of ingestion or document date.

---

## Phase 4: Chunking
Optimizing content for retrieval granularity.

*   **Strategy:** Documents are split into semantic chunks of approximately **500–800 words**.
*   **Contextual Enrichment:** Each chunk is tagged with its parent document's metadata to ensure traceability during retrieval.

---

## Phase 5: Embedding & Vector Store
Enabling semantic understanding of user queries.

*   **Model:** Utilization of `sentence-transformers` (e.g., `all-MiniLM-L6-v2`) for generating high-dimensional vector embeddings.
*   **Storage:** Embeddings are indexed using **FAISS (Facebook AI Similarity Search)** for efficient nearest-neighbor searches.

---

## Phase 6: Hybrid Retrieval
Combining semantic depth with keyword precision.

*   **Vector Search:** Identifies conceptually related chunks.
*   **Keyword Search:** Uses TF-IDF or BM25 to find exact terminology (e.g., specific scheme names or financial terms).
*   **Re-ranking:** Results from both methods are merged and ranked to prioritize the most relevant context.

---

## Phase 7: Structured Fact Extraction
Deterministic data processing for high-frequency attributes.

*   **Key Fields Extracted:** `exit_load`, `benchmark`, `SIP`, `lock-in`, `expense_ratio`, and `riskometer`.
*   **Storage:** Facts are stored in `facts.jsonl` to allow for $O(1)$ lookups during query processing, bypassing the need for complex retrieval for standard metrics.

---

## Phase 8: Query Router
Determining the intent and feasibility of a query.

*   **Classification:**
    *   `ANSWER`: Query can be fulfilled using the internal corpus.
    *   `REFUSE`: Query violates safety or scope constraints.
    *   `NOT_FOUND`: Query is out of distribution or data is missing.

---

## Phase 9: Memory Layer
Maintaining conversational continuity.

*   **Context Window:** Tracks the last **3–5 messages** in the current thread.
*   **LLM-Powered Rewriting:** Utilizing a controlled LLM layer to rewrite incomplete or coreferent queries (e.g., "What about its exit load?") into standalone, fully-specified questions.
*   **Safety Constraints:** The rewriter is forbidden from answering queries or adding outside information; it only restores context from history.
*   **Rule-based Fallback:** If the LLM layer fails or returns ambiguous results, the system falls back to a heuristic rule-based rewriter.

---

## Phase 10: Multi-thread Sessions
Isolating user interactions for privacy and clarity.

*   **Architecture:**
    *   `thread_id`: Unique identifier for each session.
    *   `messages`: Sequence of interactions within a thread.
*   **Constraint:** No cross-thread memory; each session is independent.

---

## Phase 11: Response Generation
A deterministic approach to ensure compliance.

*   **Pipeline:**
    1.  **Structured Extraction:** High-precision data extraction for common fields (e.g., exit load, SIP) using validated templates.
    2.  **Retrieval Fallback:** Contextual answers derived directly from retrieved chunks for broader factual queries.
*   **Deterministic Core:** The final output for facts is generated via code-based templates, bypassing LLM generation to eliminate hallucination risks.
*   **Optional Polishing:** A strictly validated LLM layer can be enabled to "polish" extractive snippets, subject to rigorous entity and numeric grounding checks against the source context.

---

## Phase 12: Safety Layer
Enforcing strict boundaries on AI assistance.

*   **Refusals:** The system explicitly refuses to provide financial advice, recommendations, or subjective comparisons.
*   **Constraints:**
    *   Responses are limited to **$\le$ 3 sentences**.
    *   Every response must include exactly **one source link**.

---

## Phase 13: UI Layer
A user-friendly interface for seamless interaction.

*   **Framework:** Built with **Streamlit**.
*   **Components:** Input box for queries, example query buttons for onboarding, and a persistent legal disclaimer.

---

## Phase 14: Evaluation
Quantifying system performance and reliability.

*   **Test Suite:** A diverse set of `factual`, `follow-up`, and `refusal` test cases.
*   **Metrics:**
    *   **Accuracy:** Factual correctness against the ground truth.
    *   **Citation Correctness:** Verification that the provided link supports the answer.
    *   **Safety Compliance:** Rate of correct refusals for out-of-scope queries.

---

## Summary
The **Facts-Only MF Assistant** represents a hybrid architecture that balances the flexibility of RAG with the reliability of deterministic data systems. By prioritizing structured fact extraction and enforcing a no-LLM generation policy, the system ensures that every piece of information provided to the user is grounded, cited, and compliant with financial information standards.
