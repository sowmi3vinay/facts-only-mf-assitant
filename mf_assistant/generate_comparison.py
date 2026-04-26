import os
from mf_assistant.pipeline import answer_query_text
import mf_assistant.llm_client

queries = [
    "What is the benchmark of HDFC Flexi Cap Fund?",
    "What is the exit load of HDFC Small Cap Fund?",
    "How do I download a consolidated account statement?",
    "Where do HDFC Flexi cap invest?",
    "Should I invest in HDFC Small Cap Fund?"
]

results = []

# 1. Get Template Answers (Force LLM disable)
orig_key = os.environ.get("GROQ_API_KEY")
os.environ["GROQ_API_KEY"] = ""
mf_assistant.llm_client._groq_client = None

print("Generating Template-based answers...")
for q in queries:
    ans = answer_query_text(q)
    results.append({"query": q, "template": ans})

# 2. Get LLM Answers (Restore key)
os.environ["GROQ_API_KEY"] = orig_key
mf_assistant.llm_client._groq_client = None

print("Generating LLM-powered answers...")
for i, q in enumerate(queries):
    ans = answer_query_text(q)
    results[i]["llm"] = ans

# 3. Format into Markdown
md = "# LLM vs Template Comparison\n\n"
md += "This document compares the original extractive template responses with the new synthesized LLM responses.\n\n"

for i, res in enumerate(results, 1):
    md += f"## {i}. {res['query']}\n\n"
    
    md += "### 📝 Previous (Template-based)\n"
    md += f"```text\n{res['template']}\n```\n\n"
    
    md += "### 🤖 New (LLM-powered)\n"
    md += f"```text\n{res['llm']}\n```\n\n"
    
    md += "---\n\n"

with open("mf_assistant/comparison_results.md", "w", encoding="utf-8") as f:
    f.write(md)

print("Successfully generated mf_assistant/comparison_results.md")
