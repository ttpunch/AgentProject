import os
from typing import TypedDict, Annotated, List, Union, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from connectors.postgres_connector import PostgresConnector
from connectors.mongo_connector import MongoConnector
import pandas as pd
import json
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from sklearn.linear_model import LinearRegression
import numpy as np
import re
from datetime import datetime, timedelta
from app.rag_manager import rag_manager
from app.agents.data_scientist import DataScienceAgent
from app.mcp_manager import mcp_manager

# --- Configuration ---
LLM_BASE_URL = "http://host.docker.internal:12434/engines/v1"
LLM_API_KEY = "docker"
LLM_MODEL = "ai/qwen3:8B-Q4_K_M"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = "tngtech/deepseek-r1t2-chimera:free" # Example model

# --- LLM Client Helper ---
def get_llm(provider: str = "local"):
    """Returns the appropriate LLM instance based on provider."""
    if provider == "openrouter":
        return ChatOpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
            model=OPENROUTER_MODEL,
            temperature=0,
            streaming=True
        )
    else:
        # Default to Local Docker LLM
        return ChatOpenAI(
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY,
            model=LLM_MODEL,
            temperature=0,
            streaming=True
        )

# --- State Definition ---
class AgentState(TypedDict):
    question: str
    schema_context: str
    sql_query: str
    query_result: str
    error: str
    final_answer: str
    retry_count: int
    chat_history: List[Dict[str, str]]
    target_node: str
    chat_history: List[Dict[str, str]]
    target_node: str
    chart_data: List[Dict[str, Union[str, float]]]
    llm_provider: str
    chart_type: str
    mcp_tool_name: str
    mcp_server_name: str
    mcp_arguments: Dict[str, Any]

# --- Nodes ---

def schema_loader(state: AgentState):
    """Loads schema from Postgres and Mongo to provide context."""
    print("--- Loading Schema ---")
    # Postgres Schema
    pg = PostgresConnector()
    try:
        # Dynamic schema extraction
        query = """
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            ORDER BY table_name, ordinal_position
        """
        df = pg.fetch_query(query)
        
        # Format schema as text
        schema_lines = []
        current_table = None
        for _, row in df.iterrows():
            if row['table_name'] != current_table:
                current_table = row['table_name']
                schema_lines.append(f"\nTable: {current_table}")
            schema_lines.append(f"  - {row['column_name']} ({row['data_type']})")
            
        pg_schema = "Postgres Schema:\n" + "\n".join(schema_lines)
    except Exception as e:
        pg_schema = f"Postgres Error: {e}"
    finally:
        pg.close()

    # Mongo Schema
    mongo = MongoConnector()
    try:
        # Simplified mongo schema
        mongo_schema = "MongoDB Collection 'sensor_logs' has fields: timestamp, machine_id, vibration, temperature, pressure."
    except Exception as e:
        mongo_schema = f"Mongo Error: {e}"
    finally:
        mongo.close()

    combined_schema = f"{pg_schema}\n{mongo_schema}"
    return {"schema_context": combined_schema}

def router_node(state: AgentState):
    """Decides where to route the question using static context."""
    print("--- Router Node ---")
    question = state["question"]
    chat_history = state.get("chat_history", [])
    
    # Static description of the system for routing without loading schema
    system_context = """
    You are a smart database router for a CNC Machine Predictive Maintenance System.
    
    System Capabilities:
    1. Postgres Database ('POSTGRES'):
       - Contains structured data about machines, production logs, and sensor readings.
       - I have access to the full schema including table names and columns.
       - Use this for questions about "how many", "list", "status of", "average", "max/min" on structured data.
       
    2. MongoDB ('MONGO'):
       - Contains collection 'sensor_logs' with fields: timestamp, machine_id, vibration, temperature, pressure.
       - Stores high-frequency time-series sensor data and logs.
       
    3. General Chat ('CHAT'):
       - Handles greetings, jokes, personal questions, and clarifications.
       
    4. Knowledge Base ('RAG'):
       - Contains maintenance manuals and troubleshooting guides.
       - Handles "how to", "fix", "repair", "replace", "manual", "guide" questions.

    5. MCP Tools ('MCP'):
       - External tools provided by MCP servers (e.g., Filesystem).
       - Use this if the user asks to perform an action outside the database (e.g., "list files", "read file").
    """
    
    prompt = f"""
    {system_context}
    
    Chat History:
    {chat_history}
    
    Current Question: {question}
    
    Task: Decide where to route the question.
    
    Rules:
    1. Return 'POSTGRES' if the question is about:
       - Machines (list, status, metadata, models)
       - Static information
       - Counting machines
       - "List them" or "Show me" referring to machines in history.
       - Any mention of "cotmac_iiot" table.
       - Explicit mention of "Postgres" or "PostgreSQL".
       
    2. Return 'MONGO' if the question is about:
       - Sensor data (vibration, temperature, pressure)
       - Time-series logs
       - Anomalies
       - "Highest vibration", "Average temperature"
       - Explicit mention of "Mongo" or "MongoDB".
       
    3. Return 'RAG' if the question is about:
       - How to fix/repair/replace something
       - Troubleshooting specific issues (overheating, fault)
       - "What does the manual say?"
       - "What is in the uploaded file?"
       - "Summarize the document"
       - Procedures
       - Any question about "vectors" or "embeddings"
       
    4. Return 'FORECAST' if the question is about:
       - Future predictions ("When will it fail?", "RUL")
       - "Remaining life", "How long until breakdown"
       - "Predict"
       
    5. Return 'CHAT' if the question is:
       - General greeting ("Hi", "Hello")
       - Personal questions ("Who are you?", "What is your name?")
       - Jokes or small talk
       - Clarifications not related to data
       
     6. Return 'DATA_SCIENCE' if the question is about:
       - "Anomaly detection", "Outliers", "Weird behavior"
       - "RUL", "Remaining Useful Life", "Time to failure"
       - "Forecast", "Predict future", "What will happen next"
       - "Correlation", "FFT", "Frequency analysis"

     7. Return 'MCP' if the question requires external tools (filesystem, etc.).
       
    Output ONLY one word: POSTGRES, MONGO, RAG, FORECAST, CHAT, DATA_SCIENCE, or MCP.
    """
    llm = get_llm(state.get("llm_provider"))
    response = llm.invoke([HumanMessage(content=prompt)])
    decision = response.content.strip().upper()
    
    print(f"DEBUG: Router Node decision: {decision}")
    
    # Default to CHAT if unclear
    if decision not in ["POSTGRES", "MONGO", "CHAT", "RAG", "FORECAST", "DATA_SCIENCE", "MCP"]:
        decision = "CHAT"
        
    return {"target_node": decision}


def mcp_agent(state: AgentState):
    """Handles MCP tool execution."""
    print("--- MCP Agent ---")
    question = state["question"]
    
    import asyncio
    
    async def execute_mcp():
        # 1. Get available tools
        tools = await mcp_manager.get_all_tools()
        tools_desc = "\n".join([f"- {t['name']} (Server: {t['server_name']}): {t.get('description', 'No description')}" for t in tools])
        
        # 2. Select tool
        prompt = f"""
        You are an agent with access to the following external tools:
        {tools_desc}
        
        IMPORTANT PATH INFORMATION:
        - The user's Desktop is mounted at: /mnt/desktop
        - When the user asks about "desktop" or "my desktop", use the path: /mnt/desktop
        - Do NOT use paths like /root/Desktop or ~/Desktop
        
        User Question: {question}
        
        Task: Select the best tool to answer the question and provide the arguments.
        
        CRITICAL: The "server_name" in your response MUST EXACTLY MATCH the server name shown in parentheses above.
        For example, if you see "- list_directory (Server: filesystem)", then server_name must be "filesystem".
        
        Output JSON format:
        {{
            "tool_name": "exact tool name from the list above",
            "server_name": "exact server name from the list above",
            "arguments": {{ "arg1": "value1", ... }}
        }}
        
        Example: If user asks "list files on my desktop", use:
        {{
            "tool_name": "list_directory",
            "server_name": "filesystem",
            "arguments": {{ "path": "/mnt/desktop" }}
        }}
        """
        
        llm = get_llm(state.get("llm_provider"))
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        
        # Log the raw response for debugging
        print(f"DEBUG: LLM raw response: {content[:200]}...")
        
        # Extract JSON from code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        print(f"DEBUG: Extracted JSON: {content}")
            
        try:
            tool_selection = json.loads(content)
            tool_name = tool_selection["tool_name"]
            server_name = tool_selection["server_name"]
            arguments = tool_selection["arguments"]
            
            print(f"DEBUG: Selected tool={tool_name}, server={server_name}, args={arguments}")
            
            # 3. Execute Tool
            result = await mcp_manager.call_tool(server_name, tool_name, arguments)
            
            # 4. Extract text from MCP response
            formatted_result = ""
            if hasattr(result, 'content') and result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        formatted_result += item.text
            else:
                formatted_result = str(result)
            
            # 5. Format result nicely
            format_prompt = f"""
            The user asked: {question}
            
            Tool executed: {tool_name}
            Raw result:
            {formatted_result}
            
            Task: Format this result in a user-friendly way. 
            - Use markdown formatting
            - Make lists readable with bullet points or numbered lists
            - Keep it concise and clear
            - Don't include technical details about the tool execution
            """
            
            format_response = llm.invoke([HumanMessage(content=format_prompt)])
            
            return {
                "mcp_tool_name": tool_name,
                "mcp_server_name": server_name,
                "mcp_arguments": arguments,
                "query_result": formatted_result,
                "final_answer": format_response.content
            }
        except Exception as e:
            return {"final_answer": f"Error executing MCP tool: {e}"}
    
    # Run the async function synchronously
    try:
        # Try to get existing event loop, otherwise create new one
        try:
            loop = asyncio.get_running_loop()
            # We're already in an async context, just await
            return loop.run_until_complete(execute_mcp())
        except RuntimeError:
            # No running loop, use asyncio.run()
            return asyncio.run(execute_mcp())
    except Exception as e:
        print(f"ERROR in MCP agent: {e}")
        import traceback
        traceback.print_exc()
        return {"final_answer": f"Error in MCP agent: {e}"}






def postgres_agent(state: AgentState):
    """Generates and executes SQL."""
    print("--- Postgres Agent ---")
    question = state["question"]
    schema = state["schema_context"]
    
    # Generation
    if state.get("error") and state.get("sql_query"):
        print(f"--- Postgres Agent (Retry {state.get('retry_count')}) ---")
        prompt = f"""
        You are an expert SQL Data Analyst. Your previous query failed.
        
        Database Schema:
        {schema}
        
        User Question: {question}
        
        Previous Query: {state['sql_query']}
        Error Message: {state['error']}
        
        CRITICAL INSTRUCTIONS:
        1. Analyze the Error Message. It tells you exactly what went wrong.
        2. If the error is "syntax error at end of input", it means you likely left a trailing comma or the query is incomplete. REMOVE trailing commas.
        3. If the error mentions a missing function (like ROUND with certain types), check data types and cast if necessary (e.g., ::numeric).
        4. If the error mentions a missing column, check the Schema again.
        5. DO NOT include comments (starting with --) in the SQL.
        6. Generate a CORRECTED SQL query that resolves the error.
        
        Return ONLY the corrected raw SQL query. No markdown, no explanations, no comments.
        """
    else:
        print("--- Postgres Agent ---")
        prompt = f"""
        You are an expert SQL Data Analyst.
        
        Database Schema:
        {schema}
        
        User Question: {question}
        
        Instructions:
        1. Use ONLY the tables and columns defined in the Schema above.
        2. Pay close attention to data types (e.g., don't compare strings to numbers).
        3. If the user asks for "machines", use the 'machines' table.
        4. If the user asks for sensor data, check if it's in 'cotmac_iiot' or other tables.
        5. DO NOT include comments (starting with --) in the SQL.
        6. DO NOT end the query with a trailing comma.
        7. Return ONLY the raw SQL query. No markdown, no explanations.
        """
    
    llm = get_llm(state.get("llm_provider"))
    response = llm.invoke([HumanMessage(content=prompt)])
    query = response.content.strip().replace("```sql", "").replace("```", "").strip()
    
    # Post-processing to remove comments and trailing commas
    query_lines = [line for line in query.split('\n') if not line.strip().startswith('--')]
    query = " ".join(query_lines).strip()
    if query.endswith(','):
        query = query[:-1]
    
    # Execution
    pg = PostgresConnector()
    try:
        df = pg.fetch_query(query)
        result = df.to_string()
        # Clear error on success
        return {"sql_query": query, "query_result": result, "error": None}
    except Exception as e:
        return {"sql_query": query, "error": str(e), "retry_count": state.get("retry_count", 0) + 1}
    finally:
        pg.close()

def mongo_agent(state: AgentState):
    """Generates and executes Mongo Pipeline."""
    print("--- Mongo Agent ---")
    question = state["question"]
    
    mongo = MongoConnector()
    
    # Generation
    if state.get("error") and state.get("retry_count", 0) > 0:
        print(f"--- Mongo Agent (Retry {state.get('retry_count')}) ---")
        prompt = f"""
        You are an expert MongoDB Data Analyst. Your previous pipeline failed.
        
        User Question: {question}
        
        Previous Error: {state['error']}
        
        Collection: 'sensor_logs'
        Fields: timestamp, machine_id, vibration, temperature, pressure
        
        Task: Correct the MongoDB aggregation pipeline.
        - Ensure correct JSON syntax.
        - Ensure operators like $sort, $match, $limit are used correctly.
        - Return ONLY the raw JSON list for the pipeline.
        """
    else:
        prompt = f"""
        You are an expert MongoDB Data Analyst.
        
        User Question: {question}
        
        Collection: 'sensor_logs'
        Fields: timestamp, machine_id, vibration, temperature, pressure
        
        Task: Generate a MongoDB aggregation pipeline to answer the question.
        - Return ONLY the raw JSON list for the pipeline.
        - Example: [{{"$match": ...}}, {{"$sort": ...}}]
        """

    try:
        # If it's a retry, we ask the LLM to fix it. 
        # For the first attempt, we use the hardcoded logic for visualization if applicable, 
        # OR we could fully switch to LLM generation. 
        # Given the "ReAct" request, let's try to use LLM generation for flexibility, 
        # but keep the hardcoded fallback for simple "show me data" requests if needed.
        # For now, let's stick to the specific request: "ReAct agent for Mongo".
        
        # NOTE: The original code had hardcoded pipeline for visualization. 
        # To make it a true agent, we should let the LLM generate the pipeline, 
        # but maybe hint it to include sorting for charts.
        
        llm = get_llm(state.get("llm_provider"))
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        
        # Extract JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        pipeline = json.loads(content)
        
        df = mongo.aggregate("sensor_logs", pipeline)
        
        # Convert to list of dicts for chart_data
        if not df.empty:
            if '_id' in df.columns:
                df['_id'] = df['_id'].astype(str)
            if 'timestamp' in df.columns:
                df['timestamp'] = df['timestamp'].astype(str)
            chart_data = df.to_dict(orient='records')
        else:
            chart_data = []
            
        result = df.to_string()
        return {"query_result": result, "chart_data": chart_data, "error": None}
        
    except Exception as e:
        return {"error": str(e), "retry_count": state.get("retry_count", 0) + 1}
    finally:
        mongo.close()

def rag_agent(state: AgentState):
    """Retrieves information from the manual."""
    print("--- RAG Agent ---")
    question = state["question"]
    
    try:
        # Retrieve from persistent store
        retrieved_docs = rag_manager.query(question)
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        
        prompt = f"""
        You are a technical support assistant. Use the following manual context to answer the question.
        
        Manual Context:
        {context}
        
        Question: {question}
        
        Answer concisely based ONLY on the manual.
        """
        llm = get_llm(state.get("llm_provider"))
        response = llm.invoke([HumanMessage(content=prompt)])
        
        return {"final_answer": response.content}
        
    except Exception as e:
        return {"final_answer": f"Error retrieving manual: {e}"}

def forecaster(state: AgentState):
    """Predicts Remaining Useful Life (RUL) and detects anomalies."""
    print("--- Forecaster ---")
    question = state["question"]
    
    # Extract Machine ID
    match = re.search(r"(CNC-\d{3})", question, re.IGNORECASE)
    if not match:
        return {"final_answer": "I need a valid Machine ID (e.g., CNC-001) to make a prediction."}
    
    machine_id = match.group(1).upper()
    
    mongo = MongoConnector()
    try:
        # Fetch last 100 records
        pipeline = [
            {"$match": {"machine_id": machine_id}},
            {"$sort": {"timestamp": -1}},
            {"$limit": 100},
            {"$sort": {"timestamp": 1}}
        ]
        df = mongo.aggregate("sensor_logs", pipeline)
        
        if df.empty:
             return {"final_answer": f"No data found for {machine_id} to generate a prediction."}
             
        # --- Data Analysis ---
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        start_time = df['timestamp'].min()
        df['minutes'] = (df['timestamp'] - start_time).dt.total_seconds() / 60
        
        X = df[['minutes']].values
        y = df['vibration'].values
        
        # Statistics
        current_vibration = y[-1]
        avg_vibration = np.mean(y)
        max_vibration = np.max(y)
        std_dev = np.std(y)
        
        # Anomaly Detection (Z-Score > 2)
        z_scores = (y - avg_vibration) / std_dev
        anomalies = np.where(np.abs(z_scores) > 2)[0]
        num_anomalies = len(anomalies)
        
        # Regression for RUL
        model = LinearRegression()
        model.fit(X, y)
        slope = model.coef_[0]
        intercept = model.intercept_
        
        THRESHOLD = 100.0
        rul_days = "Infinite (Stable)"
        failure_date = "N/A"
        
        if slope > 0:
            minutes_to_failure = (THRESHOLD - intercept) / slope
            current_minutes = X[-1][0]
            remaining_minutes = minutes_to_failure - current_minutes
            
            if remaining_minutes < 0:
                rul_days = "0 (Already Exceeded)"
            else:
                days = remaining_minutes / (24 * 60)
                rul_days = f"{days:.1f} days"
                failure_time = start_time + timedelta(minutes=minutes_to_failure)
                failure_date = failure_time.strftime('%Y-%m-%d %H:%M')
        
        # --- LLM Synthesis ---
        prompt = f"""
        You are an expert predictive maintenance analyst.
        Analyze the following data for machine {machine_id} and provide a report.
        
        Data Analysis:
        - Current Vibration: {current_vibration:.2f}
        - Average Vibration: {avg_vibration:.2f}
        - Max Vibration: {max_vibration:.2f}
        - Trend Slope: {slope:.4f} ({'Increasing' if slope > 0 else 'Stable/Decreasing'})
        - Anomalies Detected (last 100 points): {num_anomalies}
        - Critical Threshold: {THRESHOLD}
        
        Prediction:
        - Estimated RUL: {rul_days}
        - Predicted Failure Date: {failure_date}
        
        User Question: {question}
        
        Task:
        1. Summarize the current status.
        2. Explain the RUL prediction clearly.
        3. Mention any anomalies if present.
        4. Provide a recommendation (e.g., "Schedule maintenance" or "Monitor closely").
        
        Keep the tone professional and concise. Use Markdown for formatting.
        """
        
        llm = get_llm(state.get("llm_provider"))
        response = llm.invoke([HumanMessage(content=prompt)])
        return {"final_answer": response.content}
        
    except Exception as e:
        return {"final_answer": f"Error generating prediction: {e}"}
    finally:
        mongo.close()

def analyst(state: AgentState):
    """Synthesizes the answer."""
    print("--- Analyst ---")
    question = state["question"]
    result = state.get("query_result", "")
    error = state.get("error")
    
    if error:
        return {"final_answer": f"I encountered an error while querying the database: {error}"}
        
    prompt = f"""
    You are a data analyst.
    Question: {question}
    Chat History: {state.get('chat_history', [])}
    Data:
    {result}
    
    Provide a concise natural language answer based on the data.
    Use Markdown formatting to make the answer easy to read.
    - Use **bold** for key values or machine names.
    - Use lists for multiple items.
    - Use tables if presenting multiple rows of data.
    """
    llm = get_llm(state.get("llm_provider"))
    response = llm.invoke([HumanMessage(content=prompt)])
    
    # Pass chart_data through if it exists
    return {
        "final_answer": response.content,
        "chart_data": state.get("chart_data")
    }

def general_chat(state: AgentState):
    """Handles general chit-chat."""
    print("--- General Chat ---")
    question = state['question'].lower()
    
    # Check if user is asking about MCP tools/capabilities
    if any(keyword in question for keyword in ['mcp', 'tool', 'capability', 'capabilities', 'what can you do']):
        import asyncio
        
        async def get_mcp_info():
            # Get all tools from all connected servers
            tools = await mcp_manager.get_all_tools()
            
            # Group tools by server
            servers = {}
            for tool in tools:
                server_name = tool.get('server_name', 'unknown')
                if server_name not in servers:
                    servers[server_name] = []
                servers[server_name].append({
                    'name': tool.get('name', 'unknown'),
                    'description': tool.get('description', 'No description')
                })
            
            # Format the response
            if not servers:
                return "No MCP servers are currently connected."
            
            response = f"**Connected MCP Servers: {len(servers)}**\n\n"
            
            for server_name, server_tools in servers.items():
                response += f"### {server_name.title()} Server\n"
                response += f"**Tools available: {len(server_tools)}**\n\n"
                for tool in server_tools:
                    response += f"- **{tool['name']}** - {tool['description']}\n"
                response += "\n"
            
            return response
        
        try:
            mcp_info = asyncio.run(get_mcp_info())
            return {"final_answer": mcp_info}
        except Exception as e:
            return {"final_answer": f"Error fetching MCP information: {e}"}
    
    # Regular chat
    prompt = f"""
    You are a helpful assistant for a CNC Predictive Maintenance System.
    Chat History: {state.get('chat_history', [])}
    User said: {state['question']}
    """
    llm = get_llm(state.get("llm_provider"))
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"final_answer": response.content}

def ds_router(state: AgentState):
    """Routes to Spark or Pandas engine."""
    print("--- Data Science Router ---")
    llm = get_llm(state.get("llm_provider"))
    agent = DataScienceAgent(llm)
    decision = agent.determine_next_step(state)
    print(f"DEBUG: DS Router Decision: {decision}")
    return {"target_node": decision}

def spark_engine(state: AgentState):
    """Executes Spark Analysis."""
    print("--- Spark Engine ---")
    # Update status for user visibility
    # Note: In LangGraph, we can't easily yield from a node to the stream directly if we also return state.
    # The stream output captures state updates. We'll rely on the stream_question function to detect this node.
    
    llm = get_llm(state.get("llm_provider"))
    agent = DataScienceAgent(llm)
    result = agent.run_spark_analysis(state)
    return result

def pandas_engine(state: AgentState):
    """Executes Pandas Analysis."""
    print("--- Pandas Engine ---")
    llm = get_llm(state.get("llm_provider"))
    agent = DataScienceAgent(llm)
    result = agent.run_pandas_analysis(state)
    return result



# --- Graph Construction ---
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("router_node", router_node)
workflow.add_node("schema_loader", schema_loader)
workflow.add_node("postgres_agent", postgres_agent)
workflow.add_node("mongo_agent", mongo_agent)
workflow.add_node("rag_agent", rag_agent)
workflow.add_node("forecaster", forecaster)
workflow.add_node("analyst", analyst)
workflow.add_node("general_chat", general_chat)
workflow.add_node("mcp_agent", mcp_agent)


# Data Science Nodes
workflow.add_node("ds_router", ds_router)
workflow.add_node("spark_engine", spark_engine)
workflow.add_node("pandas_engine", pandas_engine)

# Set Entry Point
workflow.set_entry_point("router_node")

def route_after_router(state):
    target = state.get("target_node")
    if target == "CHAT":
        return "general_chat"
    if target == "RAG":
        return "rag_agent"
    if target == "FORECAST":
        return "forecaster"
    if target == "DATA_SCIENCE":
        return "ds_router"
    if target == "MCP":
        return "mcp_agent"
    return "schema_loader"

def route_after_schema(state):
    target = state.get("target_node")
    if target == "POSTGRES":
        return "postgres_agent"
    if target == "MONGO":
        return "mongo_agent"
    return "general_chat" # Fallback

workflow.add_conditional_edges(
    "router_node",
    route_after_router,
    {
        "general_chat": "general_chat",
        "rag_agent": "rag_agent",
        "forecaster": "forecaster",
        "ds_router": "ds_router",
        "mcp_agent": "mcp_agent",
        "schema_loader": "schema_loader"
    }
)

workflow.add_conditional_edges(
    "schema_loader",
    route_after_schema,
    {
        "postgres_agent": "postgres_agent",
        "mongo_agent": "mongo_agent",
        "general_chat": "general_chat"
    }
)

# DS Router Edges
workflow.add_conditional_edges(
    "ds_router",
    lambda x: x["target_node"],
    {
        "spark_engine": "spark_engine",
        "pandas_engine": "pandas_engine"
    }
)

def should_retry(state: AgentState):
    error = state.get("error")
    retry_count = state.get("retry_count", 0)
    target = state.get("target_node") # We need to know which agent failed
    
    if error and retry_count < 3:
        if target == "POSTGRES":
            return "postgres_agent"
        if target == "MONGO":
            return "mongo_agent"
            
    return "analyst"

workflow.add_conditional_edges(
    "postgres_agent",
    should_retry,
    {
        "postgres_agent": "postgres_agent",
        "analyst": "analyst"
    }
)

workflow.add_conditional_edges(
    "mongo_agent",
    should_retry,
    {
        "mongo_agent": "mongo_agent",
        "analyst": "analyst"
    }
)

workflow.add_edge("rag_agent", END) # RAG answers directly for now
workflow.add_edge("forecaster", END) # Forecaster answers directly
workflow.add_edge("analyst", END)
workflow.add_edge("general_chat", END)
workflow.add_edge("spark_engine", END)
workflow.add_edge("pandas_engine", END)
workflow.add_edge("mcp_agent", END)

# Compile
app_graph = workflow.compile()

def process_question(question: str, thread_id: str = "1"):
    """Entry point for the API."""
    print(f"DEBUG: Processing question: {question} with thread_id: {thread_id}")
    try:
        inputs = {"question": question, "retry_count": 0, "llm_provider": "local"} # Default to local
        config = {"configurable": {"thread_id": thread_id}}
        result = app_graph.invoke(inputs, config=config)
        print(f"DEBUG: Result: {result}")
        return result
    except Exception as e:
        print(f"DEBUG: Error in process_question: {e}")
        import traceback
        traceback.print_exc()
        raise e



def stream_question(question: str, chat_history: List[Dict[str, str]] = [], llm_provider: str = "local", thread_id: str = "1"):
    """Streams the execution steps of the agent."""
    print(f"DEBUG: Streaming question: {question} with history length: {len(chat_history)} using {llm_provider} thread: {thread_id}")
    inputs = {"question": question, "chat_history": chat_history, "retry_count": 0, "llm_provider": llm_provider}
    config = {"configurable": {"thread_id": thread_id}}
    
    # Yield initial status
    yield json.dumps({"type": "status", "content": "Starting Agent..."}) + "\n"
    
    try:
        for output in app_graph.stream(inputs, config=config):
            # output is a dict where key is node name and value is state update
            for node_name, state_update in output.items():
                if node_name == "router_node":
                     yield json.dumps({"type": "status", "content": "Routing Question..."}) + "\n"
                elif node_name == "schema_loader":
                    yield json.dumps({"type": "status", "content": "Loading Database Schema..."}) + "\n"
                elif node_name == "rag_agent":
                    yield json.dumps({"type": "status", "content": "Consulting Knowledge Base..."}) + "\n"
                    if "final_answer" in state_update:
                        yield json.dumps({"type": "answer", "content": state_update["final_answer"]}) + "\n"
                elif node_name == "forecaster":
                    yield json.dumps({"type": "status", "content": "Calculating Prediction..."}) + "\n"
                    if "final_answer" in state_update:
                        yield json.dumps({"type": "answer", "content": state_update["final_answer"]}) + "\n"
                elif node_name == "postgres_agent":
                    yield json.dumps({"type": "status", "content": "Querying Postgres Database..."}) + "\n"
                    if "sql_query" in state_update:
                         if state_update.get("error"):
                             yield json.dumps({"type": "log", "content": f"SQL Error: {state_update['error']}. Retrying..."}) + "\n"
                         else:
                             yield json.dumps({"type": "log", "content": f"SQL: {state_update['sql_query']}"}) + "\n"
                elif node_name == "mongo_agent":
                    yield json.dumps({"type": "status", "content": "Querying MongoDB..."}) + "\n"
                elif node_name == "analyst":
                    yield json.dumps({"type": "status", "content": "Analyzing Data..."}) + "\n"
                    if "final_answer" in state_update:
                        response_payload = {"type": "answer", "content": state_update["final_answer"]}
                        if "chart_data" in state_update and state_update["chart_data"]:
                            response_payload["chart_data"] = state_update["chart_data"]
                        yield json.dumps(response_payload) + "\n"
                elif node_name == "general_chat":
                    if "final_answer" in state_update:
                        yield json.dumps({"type": "answer", "content": state_update["final_answer"]}) + "\n"
                elif node_name == "ds_router":
                    yield json.dumps({"type": "status", "content": "Routing Data Science Task..."}) + "\n"
                elif node_name == "spark_engine":
                    yield json.dumps({"type": "status", "content": "Processing step: spark_engine..."}) + "\n"
                    if "final_answer" in state_update:
                        response_payload = {"type": "answer", "content": state_update["final_answer"]}
                        if "chart_data" in state_update:
                            response_payload["chart_data"] = state_update["chart_data"]
                        if "chart_type" in state_update:
                             response_payload["chart_type"] = state_update["chart_type"]
                        yield json.dumps(response_payload) + "\n"
                elif node_name == "pandas_engine":
                    yield json.dumps({"type": "status", "content": "Running Advanced Analytics (Pandas)..."}) + "\n"
                    if "final_answer" in state_update:
                        response_payload = {"type": "answer", "content": state_update["final_answer"]}
                        if "chart_data" in state_update:
                            response_payload["chart_data"] = state_update["chart_data"]
                        if "chart_type" in state_update:
                             response_payload["chart_type"] = state_update["chart_type"]
                        if "chart_type" in state_update:
                             response_payload["chart_type"] = state_update["chart_type"]
                        yield json.dumps(response_payload) + "\n"
                elif node_name == "mcp_agent":
                    yield json.dumps({"type": "status", "content": "Consulting MCP Tools..."}) + "\n"
                    if "final_answer" in state_update:
                        yield json.dumps({"type": "answer", "content": state_update["final_answer"]}) + "\n"
                        
    except Exception as e:
        print(f"Streaming Error: {e}")
        import traceback
        traceback.print_exc()
        yield json.dumps({"type": "error", "content": str(e)}) + "\n"
    finally:
        print(f"DEBUG: Stream finished for question: {question}")
