import sys
import os
from dotenv import load_dotenv

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load env vars
load_dotenv()

from voz_turista.application.workflow import build_workflow

def main():
    print("Building workflow...")
    app = build_workflow()
    
    initial_state = {
        "town": "Tulum", # Using a likely town name
        "reviews_hotel": [],
        "reviews_restaurant": [],
        "reviews_attraction": [],
        "insights_hotel": [],
        "insights_restaurant": [],
        "insights_attraction": [],
        "final_report": {},
        "audit_result": {}
    }
    
    print(f"Invoking workflow for {initial_state['town']}...")
    try:
        final_state = app.invoke(initial_state)
        
        print("\n--- Final Report ---")
        print(final_state.get("final_report"))
        
        print("\n--- Audit Result ---")
        print(final_state.get("audit_result"))
        
    except Exception as e:
        print(f"Error executing workflow: {e}")

if __name__ == "__main__":
    main()
