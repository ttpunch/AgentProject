import requests
import json
import sys

API_URL = "http://localhost:8000"

def test_hitl():
    print("--- Testing HITL Flow ---")
    
    # 1. Start Stream
    print("\n1. Starting Spark Request...")
    url = f"{API_URL}/agent/stream"
    payload = {
        "question": "Run spark analysis for CNC-001",
        "thread_id": "test_thread_1"
    }
    
    approval_needed = False
    next_node = None
    
    try:
        with requests.post(url, json=payload, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    data = json.loads(line)
                    if data.get("type") == "status":
                        print(f"Status: {data['content']}")
                    elif data.get("type") == "approval_needed":
                        print(f"\n⚠️ Approval Needed for: {data['next_node']}")
                        approval_needed = True
                        next_node = data['next_node']
                        break # Stop consuming stream to simulate pause
                        
    except Exception as e:
        print(f"Error in stream: {e}")
        return

    if not approval_needed:
        print("❌ Failed: Did not receive approval request.")
        return

    # 2. Approve
    print("\n2. Sending Approval...")
    approve_url = f"{API_URL}/agent/approve"
    approve_payload = {
        "thread_id": "test_thread_1",
        "approved": True
    }
    
    try:
        resp = requests.post(approve_url, json=approve_payload)
        result = resp.json()
        
        if result.get("status") == "resumed":
            print("✅ Resumed Successfully!")
            final_answer = result['result']['final_answer']
            print("\nFinal Answer:")
            print(final_answer)
            
            if "Spark Big Data Analysis Report" in final_answer:
                print("\n✅ HITL Verification Passed!")
            else:
                print("\n❌ Failed: Did not get Spark report.")
        else:
            print(f"\n❌ Failed to resume: {result}")
            
    except Exception as e:
        print(f"Error in approval: {e}")

if __name__ == "__main__":
    test_hitl()
