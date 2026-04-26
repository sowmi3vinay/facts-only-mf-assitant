import json
import os
import sys
import re
from typing import List, Dict

# Add root to path
sys.path.append(os.getcwd())

from mf_assistant.pipeline import answer_query
from mf_assistant.responder import format_response

TEST_CASES_FILE = "evaluation/test_cases.json"
RESULTS_FILE = "evaluation/results.json"

def run_evaluation():
    if not os.path.exists(TEST_CASES_FILE):
        print(f"Error: {TEST_CASES_FILE} not found.")
        return

    with open(TEST_CASES_FILE, "r") as f:
        test_cases = json.load(f)

    results = []
    passed_count = 0
    
    print(f"--- Running Evaluation ({len(test_cases)} tests) ---")
    
    for case in test_cases:
        print(f"Running test {case['id']}...")
        query = case["query"]
        follow_up = case.get("follow_up")
        expected_type = case["expected_type"]
        expected_keywords = case.get("expected_keywords", [])
        
        history = []
        
        # Initial query
        resp = answer_query(query, history=history)
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": format_response(resp)})
        
        # If follow-up exists, use the result of the follow-up for evaluation
        if follow_up:
            query_to_eval = follow_up
            resp = answer_query(follow_up, history=history)
        else:
            query_to_eval = query
            
        full_text = format_response(resp)
        
        # --- Checks ---
        # Extract only the first line/answer part for sentence count
        ans_part = full_text.split("\n")[0]
        
        checks = {
            "type_match": resp.kind == expected_type,
            "has_source": bool(resp.url) if resp.kind != "not_found" else True,
            "keywords_match": all(k.lower() in full_text.lower() for k in expected_keywords),
            "sentence_count_ok": len(re.findall(r'[.!?]+', ans_part)) <= 4
        }
        
        is_passed = all(checks.values())
        if is_passed:
            passed_count += 1
            
        results.append({
            "id": case["id"],
            "query": query_to_eval,
            "category": case["category"],
            "passed": is_passed,
            "checks": checks,
            "actual_type": resp.kind,
            "response": full_text
        })
        
        status = "PASS" if is_passed else "FAIL"
        print(f"[{case['category']}] Test {case['id']}: {status}")
        if not is_passed:
            print(f"   Failed checks: {[k for k, v in checks.items() if not v]}")

    # Summary
    summary = {
        "total": len(test_cases),
        "passed": passed_count,
        "failed": len(test_cases) - passed_count,
        "accuracy": (passed_count / len(test_cases)) * 100 if test_cases else 0
    }
    
    print("\n--- Summary ---")
    print(f"Total Tests: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Accuracy: {summary['accuracy']:.1f}%")
    
    with open(RESULTS_FILE, "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)
    
    print(f"\nDetailed results saved to {RESULTS_FILE}")

if __name__ == "__main__":
    run_evaluation()
