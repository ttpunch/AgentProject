from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import sys

print("--- Checking Local LLM Connectivity ---")

LLM_BASE_URL = "http://host.docker.internal:12434/engines/v1" # Try host.docker.internal first
# If running locally (not in docker), use localhost
# LLM_BASE_URL = "http://localhost:12434/engines/v1" 

print(f"Target URL: {LLM_BASE_URL}")

try:
    llm = ChatOpenAI(
        base_url=LLM_BASE_URL,
        api_key="docker",
        model="ai/qwen3:8B-Q4_K_M",
        temperature=0
    )
    
    print("Sending request...")
    response = llm.invoke([HumanMessage(content="Say 'Hello World'")])
    print(f"Response: {response.content}")
    print("--- SUCCESS ---")
except Exception as e:
    print(f"--- FAILED ---")
    print(f"Error: {e}")
