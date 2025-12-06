from sqlalchemy import create_engine, text
import pandas as pd
import os
from typing import Optional, Generator
from utils.logger import setup_logger

logger = setup_logger("PostgresConnector")

class PostgresConnector:
    _engine = None

    def __init__(self):
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.database = os.getenv("POSTGRES_DB", "cnc_db")
        self.user = os.getenv("POSTGRES_USER", "user")
        self.password = os.getenv("POSTGRES_PASSWORD", "password")
        self.port = os.getenv("POSTGRES_PORT", "5432")
        
        if PostgresConnector._engine is None:
            self._initialize_engine()

    def _initialize_engine(self):
        """Initialize SQLAlchemy engine with connection pooling."""
        try:
            db_url = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            PostgresConnector._engine = create_engine(
                db_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                connect_args={"options": "-c statement_timeout=60000"}
            )
            logger.info(f"Initialized PostgreSQL engine at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Error initializing PostgreSQL engine: {e}")
            raise

    def connect(self):
        """No-op for SQLAlchemy as engine manages connections."""
        pass

    def close(self):
        """No-op as we want to keep the pool alive."""
        pass

    def fetch_query(self, query: str) -> pd.DataFrame:
        """Fetch all results for a query into a DataFrame."""
        if not query or not query.strip():
            raise ValueError("Empty query provided to fetch_query")
        try:
            with PostgresConnector._engine.connect() as connection:
                return pd.read_sql_query(text(query), connection)
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise

    def fetch_batch(self, query: str, batch_size: int = 10000) -> Generator[pd.DataFrame, None, None]:
        """Yields batches of data from a query."""
        try:
            with PostgresConnector._engine.connect() as connection:
                # Use execution_options for server-side cursor if needed, 
                # but pandas read_sql_query with chunksize is easier for batching
                for chunk in pd.read_sql_query(text(query), connection, chunksize=batch_size):
                    yield chunk
        except Exception as e:
            logger.error(f"Error executing batch query: {e}")
            raise
