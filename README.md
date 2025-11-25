# CNC Predictive Maintenance System

A scalable system for analyzing CNC machine data using PostgreSQL, MongoDB, PySpark, and FastAPI.

## Architecture
*   **Backend**: FastAPI (API), PySpark (Data Processing)
*   **Frontend**: React + Vite
*   **Database**: PostgreSQL (Metadata), MongoDB (Sensor Logs)
*   **Infrastructure**: Docker Compose

## Prerequisites
*   Docker & Docker Compose
*   16GB+ RAM (Recommended)

## Getting Started

1.  **Start the System**:
    ```bash
    docker-compose up --build
    ```

2.  **Generate Dummy Data**:
    Once the containers are running, execute the generator script inside the backend container:
    ```bash
    docker-compose exec backend python processing/data_generator.py
    ```
    This will populate Postgres with machines and MongoDB with sensor logs.

3.  **Run Analysis Pipeline**:
    Trigger the Spark job to train the anomaly detection model:
    ```bash
    docker-compose exec backend python processing/pipeline.py
    ```

4.  **Access the API**:
    *   API Docs: http://localhost:8000/docs
    *   Frontend: http://localhost:5173

## Features
*   **Out-of-Core Processing**: Uses PySpark and MongoDB Aggregation to handle large datasets.
*   **Anomaly Detection**: Isolation Forest model to detect unusual machine behavior.
*   **Scalable**: Designed to be deployed on a cluster if needed.
