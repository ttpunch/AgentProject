from pymongo import MongoClient
import pandas as pd
import os
from typing import List, Dict, Any
from utils.logger import setup_logger

logger = setup_logger("MongoConnector")

class MongoConnector:
    def __init__(self):
        self.uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/cnc_logs")
        self.client = None
        self.db = None

    def connect(self):
        """Establish connection to MongoDB."""
        try:
            self.client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=30000,  # 30 second server selection timeout
                connectTimeoutMS=30000,  # 30 second connection timeout
                socketTimeoutMS=60000  # 60 second socket timeout
            )
            # Extract db name from URI or default
            db_name = self.uri.split('/')[-1] or "cnc_logs"
            self.db = self.client[db_name]
            logger.info(f"Connected to MongoDB: {db_name}")
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            raise

    def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

    def insert_data(self, collection: str, data: List[Dict[str, Any]]):
        """Insert list of dicts into collection."""
        if not self.client:
            self.connect()
        self.db[collection].insert_many(data)

    def insert_one(self, collection: str, document: Dict[str, Any]):
        """Insert a single document into collection."""
        if not self.client:
            self.connect()
        self.db[collection].insert_one(document)

    def aggregate(self, collection: str, pipeline: List[Dict[str, Any]]) -> pd.DataFrame:
        """Run aggregation pipeline and return DataFrame."""
        if not self.client:
            self.connect()
        
        cursor = self.db[collection].aggregate(pipeline)
        return pd.DataFrame(list(cursor))
