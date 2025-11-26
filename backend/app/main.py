from fastapi import FastAPI, HTTPException
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

@app.get("/")
def read_root():
    logger.info("Root endpoint called")
    return {"message": "CNC Predictive Maintenance System Operational"}

@app.get("/health")
def health_check():
    logger.debug("Health check called")
    return {"status": "healthy"}

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

@app.post("/agent/stream")
async def agent_stream(request: QuestionRequest):
    """
    Streams the agent's execution steps and final answer.
    """
    from app.agent_core import stream_question
    return StreamingResponse(
        stream_question(request.question, request.chat_history, request.llm_provider, request.thread_id),
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
