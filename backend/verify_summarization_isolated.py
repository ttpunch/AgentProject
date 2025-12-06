
from typing import List, Dict
from unittest.mock import MagicMock

# Copied from agent_core.py to avoid import issues
def summarize_history(history: List[Dict[str, str]], llm) -> List[Dict[str, str]]:
    """Summarizes older chat history to save tokens."""
    MAX_HISTORY = 10
    if len(history) <= MAX_HISTORY:
        return history
    
    print(f"--- Summarizing History (Length: {len(history)}) ---")
    
    # Keep the last 5 messages intact
    recent_messages = history[-5:]
    older_messages = history[:-5]
    
    # Convert older messages to string for summarization
    history_text = "\n".join([f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in older_messages])
    
    prompt = f"""
    Summarize the following conversation history concisely. 
    Preserve key details like machine IDs, specific issues, and user preferences.
    
    History:
    {history_text}
    """
    
    try:
        # Mocking the HumanMessage import for this isolated test
        class HumanMessage:
            def __init__(self, content):
                self.content = content
                
        response = llm.invoke([HumanMessage(content=prompt)])
        summary = response.content.strip()
        print(f"DEBUG: Generated Summary: {summary}")
        
        # Create a summary message
        summary_message = {"role": "system", "content": f"Previous conversation summary: {summary}"}
        
        return [summary_message] + recent_messages
    except Exception as e:
        print(f"Error summarizing history: {e}")
        return history[-MAX_HISTORY:] # Fallback to simple truncation

# Mock LLM
class MockLLM:
    def invoke(self, messages):
        return MagicMock(content="Summary of the conversation: User asked about X, Agent answered Y.")

def test_summarization():
    print("Testing Summarization Logic (Isolated)...")
    
    # Create a long history (15 messages)
    history = []
    for i in range(15):
        role = "user" if i % 2 == 0 else "assistant"
        history.append({"role": role, "content": f"Message {i+1}"})
    
    print(f"Original History Length: {len(history)}")
    
    # Run summarization
    llm = MockLLM()
    new_history = summarize_history(history, llm)
    
    print(f"New History Length: {len(new_history)}")
    
    # Verify structure
    # Should have 1 summary message + 5 recent messages = 6 total
    if len(new_history) == 6:
        print("PASS: History length reduced to 6 (1 summary + 5 recent)")
    else:
        print(f"FAIL: Expected length 6, got {len(new_history)}")
        
    # Verify first message is summary
    if new_history[0]["role"] == "system" and "Previous conversation summary" in new_history[0]["content"]:
        print("PASS: First message is the summary")
    else:
        print(f"FAIL: First message is not summary. Got: {new_history[0]}")

    # Verify last message is the most recent one
    if new_history[-1]["content"] == "Message 15":
        print("PASS: Last message preserved")
    else:
        print(f"FAIL: Last message incorrect. Got: {new_history[-1]['content']}")

if __name__ == "__main__":
    test_summarization()
