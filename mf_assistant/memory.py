import re
from typing import List, Optional, Tuple
from .fact_intent import detect_field, detect_scheme
from .facts_store import get_facts_store

def _get_history_context(history: List[dict]) -> Tuple[Optional[str], Optional[str]]:
    """Scan history (last to first) to find the most recent scheme and field."""
    schemes = get_facts_store().schemes()
    last_scheme = None
    last_field = None
    
    # We only look at the last 5 messages (user or assistant)
    recent = history[-5:] if len(history) > 5 else history
    
    for msg in reversed(recent):
        content = msg.get("content", "")
        role = msg.get("role", "")
        
        # Detect from content
        f = detect_field(content)
        s = detect_scheme(content, schemes)
        
        if not last_field and f:
            last_field = f
        if not last_scheme and s:
            last_scheme = s
            
        if last_field and last_scheme:
            break
            
    return last_scheme, last_field

def rewrite_query(query: str, history: List[dict]) -> str:
    """
    Rewrite an incomplete query into a standalone one based on thread history.
    Example: 'What about exit load?' -> 'What is the exit load of HDFC Flexi Cap Fund?'
    """
    if not history:
        return query
    
    from .config import USE_LLM_REWRITE
    from .llm_client import llm_rewrite_query
    
    if USE_LLM_REWRITE:
        llm_rewritten = llm_rewrite_query(query, history)
        if llm_rewritten:
            print(f"DEBUG [LLM]: Original: '{query}' -> Rewritten: '{llm_rewritten}'")
            return llm_rewritten
        else:
            print(f"DEBUG: LLM rewrite failed, falling back to rule-based logic.")
    
    # RULE-BASED FALLBACK
    q_lower = query.lower().strip()
    schemes = get_facts_store().schemes()
    
    current_field = detect_field(query)
    current_scheme = detect_scheme(query, schemes)
    
    # If it's already a full query (has both), return as is
    if current_field and current_scheme:
        return query
    
    # Heuristic for incomplete/referential queries
    referential_starters = ["what about", "how about", "and for", "and what is", "what is the", "tell me about", "and"]
    is_short = len(q_lower.split()) <= 5
    is_referential = any(q_lower.startswith(s) for s in referential_starters)
    
    if not is_referential and not is_short and current_scheme and not current_field:
        # e.g. "Tell me more about HDFC Top 100" - maybe they want the last field?
        pass
    elif not is_referential and not is_short and current_field and not current_scheme:
        # e.g. "What is the benchmark?" - likely referential
        is_referential = True

    if is_referential or is_short:
        last_scheme, last_field = _get_history_context(history)
        
        # Case 1: Has field, missing scheme -> Use last scheme
        if current_field and not current_scheme and last_scheme:
            # Map field back to a natural name for the query
            field_map = {
                "lock_in_period": "lock-in period",
                "exit_load": "exit load",
                "benchmark": "benchmark",
                "minimum_sip": "minimum SIP",
                "minimum_lumpsum": "minimum investment",
                "expense_ratio": "expense ratio",
                "riskometer": "riskometer"
            }
            f_name = field_map.get(current_field, "details")
            rewritten = f"What is the {f_name} of {last_scheme}?"
            print(f"DEBUG: Rewrote '{query}' to '{rewritten}'")
            return rewritten
            
        # Case 2: Has scheme, missing field -> Use last field
        if current_scheme and not current_field and last_field:
            field_map = {
                "lock_in_period": "lock-in period",
                "exit_load": "exit load",
                "benchmark": "benchmark",
                "minimum_sip": "minimum SIP",
                "minimum_lumpsum": "minimum investment",
                "expense_ratio": "expense ratio",
                "riskometer": "riskometer"
            }
            f_name = field_map.get(last_field, "details")
            rewritten = f"What is the {f_name} of {current_scheme}?"
            print(f"DEBUG: Rewrote '{query}' to '{rewritten}'")
            return rewritten
            
        # Case 3: Missing both (e.g. "What about benchmark?") 
        # But wait, detect_field should have caught 'benchmark'.
        # If they just say "What about it?" or something very vague:
        if not current_field and not current_scheme and last_scheme and last_field:
            if any(word in q_lower for word in ["it", "this", "that"]):
                 field_map = {
                    "lock_in_period": "lock-in period",
                    "exit_load": "exit load",
                    "benchmark": "benchmark",
                    "minimum_sip": "minimum SIP",
                    "minimum_lumpsum": "minimum investment",
                    "expense_ratio": "expense ratio",
                    "riskometer": "riskometer"
                }
                 f_name = field_map.get(last_field, "details")
                 rewritten = f"What is the {f_name} of {last_scheme}?"
                 print(f"DEBUG: Rewrote '{query}' to '{rewritten}'")
                 return rewritten

    return query
