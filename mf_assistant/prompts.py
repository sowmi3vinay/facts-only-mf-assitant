"""Prompts and canned text used by the responder and router.

This app does not call an external LLM by default. The "prompt" templates here
are used to format grounded answers that quote retrieved chunks verbatim.
If you later wire in an LLM, pass these system rules in the system prompt.
"""

SYSTEM_RULES = """You are a facts-only mutual fund assistant.
You answer ONLY factual questions about a small set of approved schemes.
You MUST:
- Use only the provided context chunks.
- Never fabricate facts. If unsure, say so and refuse.
- Keep answers to 3 sentences or less.
- Include exactly 1 source URL.
- End with a line: "Last updated from sources: <date>".
You MUST refuse:
- Investment advice, recommendations, buy/sell suggestions.
- Portfolio allocation, "which fund is better", return predictions, performance comparisons.
- Anything requesting or storing PII (PAN, Aadhaar, account numbers, OTP, phone, email).
"""

REFUSAL_ADVICE = (
    "I can only share factual information from official sources, not investment advice "
    "or recommendations. For guidance on suitability or returns, please refer to the "
    "official AMC factsheet and SEBI investor education portal."
)

REFUSAL_PII = (
    "For your safety, I do not accept or store personal identifiers such as PAN, "
    "Aadhaar, account numbers, OTPs, phone numbers, or email addresses. Please "
    "remove these details and ask a factual scheme question instead."
)

REFUSAL_OUT_OF_SCOPE = (
    "I couldn't find this in the approved official sources I have access to. "
    "Please check the AMC factsheet, AMFI, or SEBI investor portal for verified details."
)

DISCLAIMER = "Facts-only. No investment advice."

WELCOME = "Ask factual questions about approved mutual fund schemes — sourced only from official AMC, AMFI, SEBI, and Kuvera help pages."

EXAMPLE_QUESTIONS = [
    "What is the expense ratio of Demo Large Cap Fund - Direct Growth?",
    "What is the exit load on Demo Flexi Cap Fund?",
    "How do I download my capital gains statement on Kuvera?",
]
