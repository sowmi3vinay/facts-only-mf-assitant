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

# One official educational source we cite in refusals so the user has somewhere
# legitimate to learn more without us giving advice.
EDUCATIONAL_SOURCE_URL = "https://investor.sebi.gov.in/"

REFUSAL_ADVICE = (
    "I can only share factual information from official sources. I don't provide "
    "investment advice, recommendations, buy/sell guidance, portfolio allocation "
    "help, or return predictions. For investor education, see the SEBI investor "
    "portal."
)

REFUSAL_PII = (
    "For your safety, I do not accept or store personal identifiers such as PAN, "
    "Aadhaar, account numbers, OTPs, phone numbers, or email addresses. Please "
    "remove these details and ask a factual scheme question instead."
)

NOT_FOUND_MESSAGE = (
    "I couldn't verify this from the official sources I have indexed. Please "
    "check the AMC factsheet, AMFI, or SEBI investor portal for the latest details."
)

# Kept for backward compatibility with older imports.
REFUSAL_OUT_OF_SCOPE = NOT_FOUND_MESSAGE

DISCLAIMER = "Facts-only. No investment advice."

WELCOME = (
    "Ask factual questions about approved mutual fund schemes — sourced only from "
    "official AMC, AMFI, SEBI, and Kuvera help pages."
)

EXAMPLE_QUESTIONS = [
    "What is the lock-in period for HDFC ELSS Tax Saver Fund?",
    "What is the benchmark of HDFC Top 100 Fund?",
    "What is the exit load on HDFC Flexi Cap Fund?",
]
