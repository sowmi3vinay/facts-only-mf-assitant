import os
import re
from typing import Optional
from dotenv import load_dotenv

from groq import Groq
from .prompts import LLM_SYSTEM_PROMPT

load_dotenv()

_groq_client = None

def get_client() -> Optional[Groq]:
    global _groq_client
    if _groq_client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return None
        _groq_client = Groq(api_key=api_key)
    return _groq_client

def _extract_entities(text: str) -> set[str]:
    """Find capitalized words (potential entities) in text."""
    # Exclude common sentence starters and format labels
    # We'll just look for words starting with Uppercase followed by lowercase/digits
    return set(re.findall(r"\b[A-Z][A-Za-z0-9]+\b", text))

def generate_answer(query: str, context: str, source_url: str, last_updated: str) -> Optional[str]:
    """
    Call Groq to generate a final answer based on the provided context.
    Returns the formatted string if successful and post-validation passes, else None.
    """
    client = get_client()
    if not client:
        return None

    last_updated_str = last_updated if last_updated else "Not stated on source page"

    user_prompt = f"""
User Query: {query}
Context: {context}
Source URL: {source_url}
Last Updated: {last_updated_str}
"""

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.0,
            max_tokens=250,
        )
        
        output = response.choices[0].message.content.strip()

        # POST-VALIDATION
        lines = [line.strip() for line in output.split("\n") if line.strip()]
        
        # 1. Format check
        ans_line = next((line for line in lines if line.startswith("Answer:")), None)
        if not ans_line or not any(line.startswith("Source:") for line in lines):
            return None

        ans_body = ans_line.replace("Answer:", "").strip()

        # 2. Advice check
        advice_keywords = ["recommend", "buy", "sell", "should invest", "allocate", "good investment", "better fund"]
        if any(k in ans_body.lower() for k in advice_keywords):
            print("DEBUG: LLM rejected due to advice/recommendation detected.")
            return None

        # 3. Entity Grounding Check (STRICT)
        entities = _extract_entities(ans_body)
        ctx_lower = context.lower()
        
        # Blacklist check (user specific request)
        blacklist = {"CAMS", "KFintech", "MFCentral", "MF Central", "Karvy"}
        for b in blacklist:
            if b.lower() in ans_body.lower():
                print(f"DEBUG: LLM rejected due to blacklisted entity '{b}' detected.")
                return None

        # Words to ignore (sentence starters, common pronouns, format labels)
        ignore = {
            "Answer", "The", "You", "Investors", "Please", "Refer", "Official", "Source", "Context",
            "They", "This", "It", "We", "He", "She", "Their", "Your", "Our", "And", "But", "For"
        }
        for ent in entities:
            if ent in ignore:
                continue
            if ent.lower() not in ctx_lower:
                # Entity not in context! Hallucination detected.
                print(f"DEBUG: LLM rejected due to hallucinated entity '{ent}' not in context.")
                return None
        
        # 4. Number Grounding Check
        numbers = re.findall(r"\b\d+(?:\.\d+)?%?\b", ans_body)
        for num in numbers:
            if num not in context:
                print(f"DEBUG: LLM rejected due to hallucinated number '{num}' not in context.")
                return None

        return output

    except Exception as e:
        print(f"Groq LLM Error: {e}")
        return None

def llm_rewrite_query(query: str, history: list[dict]) -> Optional[str]:
    """
    Call Groq to rewrite a query based on history.
    """
    from .prompts import REWRITE_SYSTEM_PROMPT
    client = get_client()
    if not client:
        return None

    history_str = ""
    for msg in history[-3:]:  # Last 3 messages as requested
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        history_str += f"{role}: {content}\n"

    user_prompt = f"History:\n{history_str}\nLatest Query: {query}"

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.0,
            max_tokens=100,
        )
        return response.choices[0].message.content.strip().strip('"')
    except Exception as e:
        print(f"Groq Rewrite Error: {e}")
        return None
