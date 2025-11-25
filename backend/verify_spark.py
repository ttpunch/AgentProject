import sys
import os
from app.agent_core import process_question

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_spark_routing():
    print("\n--- Testing Spark Routing ---")
    # Question that should trigger Spark
    question = "Run spark analysis for CNC-001 to get monthly stats"
    
    try:
        result = process_question(question)
        print("\nResult:")
        print(result)
        
        if "Spark Big Data Analysis Report" in result['final_answer']:
            print("\n✅ Spark Routing & Execution Successful!")
        else:
            print("\n❌ Spark Routing Failed.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    test_spark_routing()
