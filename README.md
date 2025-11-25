# AI-Powered CNC Predictive Maintenance System

A scalable, AI-driven system for monitoring and analyzing CNC machine data. This project integrates real-time data processing, anomaly detection, and a Generative AI agent to provide actionable maintenance insights.

## 🏗️ Architecture

*   **Frontend**: React + Vite (Interactive Dashboard & Chat Interface)
*   **Backend**: FastAPI (REST API & WebSocket)
*   **AI Engine**:
    *   **RAG (Retrieval Augmented Generation)**: LangChain + ChromaDB for querying technical manuals.
    *   **Agent**: Custom LangGraph-based agent for routing queries (SQL vs. Vector Store).
    *   **LLM**: Supports local LLMs (via Ollama) and Cloud LLMs (via OpenRouter).
*   **Data Processing**: PySpark (Batch Processing & Analytics)
*   **Database**:
    *   **PostgreSQL**: Relational metadata (Machines, Models).
    *   **MongoDB**: Time-series sensor logs (Vibration, Temperature, etc.).
*   **Infrastructure**: Docker Compose.

## 🚀 Features

*   **Real-time Monitoring**: Dashboard visualizing sensor metrics (Vibration, Temperature, Pressure).
*   **AI Data Agent**: Chat with your data! Ask questions like "Which machines have high vibration?" or "How do I fix error code X?".
*   **RAG Knowledge Base**: Upload PDF manuals and query them using the AI agent.
*   **Anomaly Detection**: Isolation Forest model to detect unusual machine behavior.
*   **Scalable**: Designed with out-of-core processing capabilities.

## 📋 Prerequisites

*   Docker & Docker Compose
*   16GB+ RAM (Recommended for running local LLMs and Spark)

## 🛠️ Getting Started

### 1. Start the System
```bash
docker-compose up --build
```

### 2. Manage Data
**Generate Dummy Data**:
Populate the databases with simulated machine and sensor data:
```bash
docker-compose exec backend python -m processing.data_generator
```

**Clear Data**:
Remove all generated data while keeping the schema intact:
```bash
docker-compose exec backend python -m processing.clear_data
```

### 3. Run Analysis Pipeline
Trigger the Spark job to train the anomaly detection model:
```bash
docker-compose exec backend python processing/pipeline.py
```

### 4. Access the Application
*   **Frontend Dashboard**: [http://localhost:5173](http://localhost:5173)
*   **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

## 📂 Project Structure

```
├── backend/
│   ├── app/                # FastAPI Application & Agents
│   ├── connectors/         # DB Connectors (Postgres, Mongo)
│   ├── processing/         # Spark Jobs & Data Scripts
│   ├── chroma_db/          # Vector Store
│   └── data/               # Uploaded Documents
├── frontend/
│   ├── src/
│   │   ├── components/     # React Components
│   │   └── pages/          # Dashboard & Chat Pages
└── docker-compose.yml
```
