import sys
import os
import pandas as pd
from unittest.mock import MagicMock

# Add backend directory to path
sys.path.append(os.path.abspath("backend"))

# Mock LLM
class MockLLM:
    def invoke(self, messages):
        content = messages[0].content
        if "Classify" in content:
            if "anomaly" in content.lower():
                return MagicMock(content="ANOMALY")
            elif "rul" in content.lower():
                return MagicMock(content="RUL")
            elif "forecast" in content.lower():
                return MagicMock(content="FORECAST")
        return MagicMock(content="Mock Analysis Result")

# Mock Mongo
class MockMongo:
    def aggregate(self, collection, pipeline):
        # Generate synthetic data
        dates = pd.date_range(start='2023-01-01', periods=100, freq='T')
        data = {
            'timestamp': dates,
            'vibration': [0.5 + (i * 0.01) for i in range(100)], # Increasing vibration
            'temperature': [50 + (i * 0.1) for i in range(100)],
            'pressure': [100 for _ in range(100)],
            'machine_id': 'CNC-001'
        }
        return pd.DataFrame(data)
    
    def close(self):
        pass

# Patch MongoConnector
import connectors.mongo_connector
connectors.mongo_connector.MongoConnector = MockMongo

from app.agents.data_scientist import DataScienceAgent

def test_anomaly():
    print("Testing Anomaly Detection...")
    agent = DataScienceAgent(MockLLM())
    state = {"question": "Detect anomalies for CNC-001"}
    
    # Force determination (since we mocked LLM to be simple)
    # But let's rely on the mock logic
    result = agent.analyze(state)
    
    if "chart_data" in result and result.get("chart_type") == "scatter_anomaly":
        print("✅ Anomaly Detection: Success (Chart Data returned)")
    else:
        print(f"❌ Anomaly Detection: Failed. Result: {result}")

def test_rul():
    print("\nTesting RUL Prediction...")
    agent = DataScienceAgent(MockLLM())
    state = {"question": "Calculate RUL for CNC-001"}
    
    result = agent.analyze(state)
    
    if "Estimated RUL" in result["final_answer"]:
        print("✅ RUL Prediction: Success")
    else:
        print(f"❌ RUL Prediction: Failed. Result: {result}")

def test_forecast():
    print("\nTesting Forecasting...")
    agent = DataScienceAgent(MockLLM())
    state = {"question": "Forecast vibration for CNC-001"}
    
    result = agent.analyze(state)
    
    if "chart_data" in result and result.get("chart_type") == "forecast":
        print("✅ Forecasting: Success (Chart Data returned)")
    else:
        print(f"❌ Forecasting: Failed. Result: {result}")

if __name__ == "__main__":
    try:
        test_anomaly()
        test_rul()
        test_forecast()
    except Exception as e:
        print(f"❌ Verification Failed with Error: {e}")
        import traceback
        traceback.print_exc()
