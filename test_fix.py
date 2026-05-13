import json
from src.core.runner import DialogueRunner

def test_case_001():
    try:
        with open("data/fact_sheets.json", "r", encoding="utf-8") as f:
            all_facts = json.load(f)
        
        runner = DialogueRunner(model_name="gemini-3.1-flash-lite") # Use newest lite model
        result = runner.run_conversation("CASE_001", all_facts["CASE_001"], "Reflection", "Polite")
        
        print("\n--- Test Completed ---")
        print(f"Status: {result['metadata']['status']}")
        
        # Check if internal thoughts leaked into the conversation log
        for turn in result['conversation']:
            customer_msg = turn['customer']['content']
            service_msg = turn['service_agent']['final_answer']
            
            if "Reflection Process" in service_msg or "Initial Draft" in service_msg:
                print("FAILURE: Internal thoughts leaked into the final answer!")
            else:
                print("SUCCESS: No leakage detected in this turn.")
                
    except Exception as e:
        print(f"Test failed with error: {e}")

if __name__ == "__main__":
    test_case_001()
