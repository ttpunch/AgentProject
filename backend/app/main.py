from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from utils.logger import setup_logger
from connectors.postgres_connector import PostgresConnector
from connectors.mongo_connector import MongoConnector
import pandas as pd
from typing import List, Dict, Any
from fastapi import UploadFile, File
import shutil
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.rag_manager import rag_manager
from app.utils.chat_history import (
    save_message, get_history, 
    create_thread, get_threads, get_thread_history, update_thread_title, delete_thread
)
from app.auth import (
    UserCreate, UserLogin, Token, UserResponse, PasswordReset,
    create_user, get_user_by_username, verify_password, create_access_token,
    get_current_user, get_admin_user, get_all_users, update_user_password
)

logger = setup_logger("API")

app = FastAPI(title="CNC Predictive Maintenance API")

# Enable CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting CNC Predictive Maintenance API...")

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker monitoring."""
    return {"status": "ok"}

@app.get("/")
def read_root():
    logger.info("Root endpoint called")
    return {"message": "CNC Predictive Maintenance System Operational"}

@app.get("/health")
def health_check():
    logger.debug("Health check called")
    return {"status": "healthy"}

# --- Auth Endpoints ---
@app.post("/auth/register", response_model=dict)
def register(user: UserCreate):
    """Register a new user."""
    result = create_user(user.username, user.email, user.password)
    return {"message": "User registered successfully", "user": result}

@app.post("/auth/login", response_model=Token)
def login(user: UserLogin):
    """Authenticate and return JWT token."""
    db_user = get_user_by_username(user.username)
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": db_user["id"], "role": db_user["role"]})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        role=current_user["role"]
    )

# --- Admin Endpoints ---
@app.get("/admin/users")
async def list_users(admin: dict = Depends(get_admin_user)):
    """List all users (admin only)."""
    return get_all_users()

@app.put("/admin/users/{user_id}/password")
async def reset_user_password(
    user_id: str,
    password_data: PasswordReset,
    admin: dict = Depends(get_admin_user)
):
    """Reset a user's password (admin only)."""
    success = update_user_password(user_id, password_data.new_password)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Password updated successfully"}

@app.get("/machines")
def get_machines():
    """Get list of all machines and their metadata."""
    pg = PostgresConnector()
    try:
        df = pg.fetch_query("SELECT * FROM machines")
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error fetching machines: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        pg.close()

@app.get("/machines/{machine_id}/metrics")
def get_machine_metrics(machine_id: str, limit: int = 100):
    """Get recent sensor logs for a specific machine."""
    mongo = MongoConnector()
    try:
        # Simple find query, sorted by timestamp desc
        pipeline = [
            {"$match": {"machine_id": machine_id}},
            {"$sort": {"timestamp": -1}},
            {"$limit": limit},
            {"$sort": {"timestamp": 1}} # Return in chronological order for charts
        ]
        df = mongo.aggregate("sensor_logs", pipeline)
        if df.empty:
            return []
        
        # Convert timestamp to string for JSON serialization
        df['timestamp'] = df['timestamp'].astype(str)
        
        # Drop _id
        if '_id' in df.columns:
            df = df.drop(columns=['_id'])
            
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error fetching metrics for {machine_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        mongo.close()

@app.get("/anomalies")
def get_anomalies():
    """
    Get recent anomalies. 
    Note: In a real system, we would query a dedicated 'anomalies' table/collection.
    For this demo, we'll just return a mock response or query high vibration logs.
    """
    mongo = MongoConnector()
    try:
        # Mocking anomalies by finding high vibration
        pipeline = [
            {"$match": {"vibration": {"$gt": 0.8}}}, # Threshold
            {"$sort": {"timestamp": -1}},
            {"$limit": 20}
        ]
        df = mongo.aggregate("sensor_logs", pipeline)
        if df.empty:
            return []
        
        df['timestamp'] = df['timestamp'].astype(str)
        if '_id' in df.columns:
            df = df.drop(columns=['_id'])
            
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error fetching anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        mongo.close()

@app.get("/ai/report")
def get_ai_report():
    """
    Generates an AI-powered maintenance report based on current system state.
    """
    pg = PostgresConnector()
    mongo = MongoConnector()
    
    try:
        # Fetch data for context
        machines_df = pg.fetch_query("SELECT * FROM machines")
        machines = machines_df.to_dict(orient="records")
        
        # Re-use anomaly logic (simplified for this endpoint)
        pipeline = [
            {"$match": {"vibration": {"$gt": 0.8}}},
            {"$sort": {"timestamp": -1}},
            {"$limit": 20}
        ]
        anomalies_df = mongo.aggregate("sensor_logs", pipeline)
        anomalies = []
        if not anomalies_df.empty:
            # Clean up for consumption
            if '_id' in anomalies_df.columns:
                anomalies_df = anomalies_df.drop(columns=['_id'])
            anomalies_df['timestamp'] = anomalies_df['timestamp'].astype(str)
            anomalies = anomalies_df.to_dict(orient="records")
            
        from app.ai_generator import generate_maintenance_report
        report = generate_maintenance_report(machines, anomalies)
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating AI report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        pg.close()
        mongo.close()
@app.post("/agent/chat")
async def agent_chat(request: Dict[str, Any]):
    """
    Endpoint for the AI Data Agent.
    Expects JSON: {"question": "..."}
    """
    print(f"DEBUG: Received chat request: {request}")
    question = request.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    
    try:
        from app.agent_core import process_question
        result = process_question(question)
        response = {"answer": result.get("final_answer")}
        if "chart_data" in result:
            response["chart_data"] = result["chart_data"]
        if "chart_type" in result:
            response["chart_type"] = result["chart_type"]
        return response
    except Exception as e:
        print(f"DEBUG: Error in agent_chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        logger.error(f"Agent Error: {e}")
        return {"answer": "I'm sorry, I encountered an internal error while processing your request."}

        return {"answer": "I'm sorry, I encountered an internal error while processing your request."}

class QuestionRequest(BaseModel):
    question: str
    chat_history: List[Dict[str, str]] = []
    llm_provider: str = "local"
    thread_id: str = "1" # Default thread ID
    user_id: str = "default_user" # Added user_id for persistence

@app.get("/chat/history/{user_id}")
def get_chat_history(user_id: str):
    """
    Retrieves chat history for a specific user.
    """
    return get_history(user_id)

@app.get("/chat/my-history")
async def get_my_chat_history(current_user: dict = Depends(get_current_user)):
    """
    Retrieves chat history for the authenticated user.
    """
    return get_history(current_user["id"])

# --- Thread Management Endpoints ---

@app.get("/threads")
async def list_threads(current_user: dict = Depends(get_current_user)):
    """List all threads for the authenticated user."""
    return get_threads(current_user["id"])

@app.post("/threads")
async def create_new_thread(current_user: dict = Depends(get_current_user)):
    """Create a new thread and return its ID."""
    thread_id = create_thread(current_user["id"], "New Chat")
    if not thread_id:
        raise HTTPException(status_code=500, detail="Failed to create thread")
    return {"thread_id": thread_id, "title": "New Chat"}

@app.get("/threads/{thread_id}")
async def get_thread_messages(thread_id: str, current_user: dict = Depends(get_current_user)):
    """Get messages for a specific thread."""
    return get_thread_history(current_user["id"], thread_id)

@app.delete("/threads/{thread_id}")
async def remove_thread(thread_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a thread and all its messages."""
    success = delete_thread(current_user["id"], thread_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete thread")
    return {"message": "Thread deleted successfully"}

@app.post("/agent/stream")
async def agent_stream(request: QuestionRequest):
    """
    Streams the agent's execution steps and final answer.
    """
    from app.agent_core import stream_question
    
    # Use user_id from request (for backward compatibility)
    user_id = request.user_id
    
    # Determine if this is the first message in the thread (BEFORE saving new message)
    is_first_message = False
    if request.thread_id:
        existing_msgs = get_thread_history(user_id, request.thread_id)
        is_first_message = len(existing_msgs) == 0
        print(f"DEBUG: Pre-save check - is_first_message={is_first_message}, thread_id={request.thread_id}, existing_count={len(existing_msgs)}")
    
    # Save user question with thread_id
    save_message(user_id, "user", request.question, request.thread_id)
    
    def stream_with_persistence():
        full_answer = ""
        chart_data = None
        
        # Limit chat history to last 10 messages for performance
        limited_history = request.chat_history[-10:] if request.chat_history else []
        
        for chunk in stream_question(request.question, limited_history, request.llm_provider, request.thread_id, user_id):
            yield chunk
            
            # Parse chunk to accumulate answer
            try:
                import json
                data = json.loads(chunk)
                if data.get("type") == "token":
                    # Accumulate streaming tokens
                    full_answer += data.get("content", "")
                elif data.get("type") == "answer":
                    # Direct answer (non-streaming)
                    full_answer = data.get("content", "")
                    chart_data = data.get("chart_data")
                elif data.get("type") == "answer_end":
                    # Streaming complete - chart_data might be here
                    if data.get("chart_data"):
                        chart_data = data.get("chart_data")
            except:
                pass
        
        # Save agent answer at the end
        print(f"DEBUG: Saving agent answer, length={len(full_answer)}, thread_id={request.thread_id}")
        if full_answer:
            metadata = {}
            if chart_data:
                metadata["chart_data"] = chart_data
            save_message(user_id, "agent", full_answer, request.thread_id, metadata)
        
        # Update thread title if this is the first message
        print(f"DEBUG: is_first_message={is_first_message}, thread_id={request.thread_id}")
        if is_first_message and request.thread_id:
            print(f"DEBUG: Updating thread title to: {request.question[:50]}")
            update_thread_title(request.thread_id, request.question)

    return StreamingResponse(
        stream_with_persistence(),
        media_type="application/x-ndjson"
    )



@app.post("/upload-doc")
async def upload_document(file: UploadFile = File(...)):
    """
    Uploads a document (PDF or TXT) and indexes it into the RAG vector store.
    """
    try:
        file_location = f"./data/{file.filename}"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
            
        # Index the document
        num_chunks = rag_manager.add_document(file_location, file.filename)
        
        return {"message": f"Successfully uploaded and indexed {file.filename}", "chunks": num_chunks}
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete-doc")
def delete_document(filename: str):
    """
    Deletes a document from the RAG vector store and filesystem.
    """
    try:
        rag_manager.delete_document(filename)
        return {"message": f"Successfully deleted {filename}"}
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vectors")
def get_vectors():
    """
    Returns a sample of vectors from the store for visualization.
    """
    try:
        return rag_manager.get_vector_sample()
    except Exception as e:
        logger.error(f"Error fetching vectors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
def get_documents():
    """
    Returns a list of indexed documents.
    """
    try:
        return rag_manager.list_documents()
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
