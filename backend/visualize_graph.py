import sys
import os

# Add the parent directory to sys.path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.agent_core import app_graph
    print(app_graph.get_graph().draw_mermaid())
except Exception as e:
    print(f"Error generating graph: {e}")
