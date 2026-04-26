from mf_assistant.pipeline import answer_query_text

history = []

def ask(query):
    print(f"\nUser: {query}")
    ans = answer_query_text(query, history=history)
    print(f"Assistant: {ans}")
    history.append({"role": "user", "content": query})
    history.append({"role": "assistant", "content": ans})

print("--- Testing Follow-up Memory ---")
ask("What is the exit load of HDFC Small Cap Fund?")
ask("What about benchmark?")
ask("And for HDFC Flexi Cap Fund?")
ask("What is the riskometer?")
