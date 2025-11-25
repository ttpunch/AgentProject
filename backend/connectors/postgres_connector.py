import psycopg2
import pandas as pd
import os
from typing import Optional, Generator
from utils.logger import setup_logger

logger = setup_logger("PostgresConnector")

class PostgresConnector:
    def __init__(self):
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.database = os.getenv("POSTGRES_DB", "cnc_db")
        self.user = os.getenv("POSTGRES_USER", "user")
        self.password = os.getenv("POSTGRES_PASSWORD", "password")
        self.port = os.getenv("POSTGRES_PORT", "5432")
        self.conn = None

    def connect(self):
        """Establish connection to PostgreSQL."""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
            logger.info(f"Connected to PostgreSQL at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL: {e}")
            raise

    def close(self):
        """Close the connection."""
        if self.conn:
            self.conn.close()
            logger.info("PostgreSQL connection closed")

    def fetch_query(self, query: str) -> pd.DataFrame:
        """Fetch all results for a query into a DataFrame."""
        if not self.conn:
            self.connect()
        return pd.read_sql_query(query, self.conn)

    def fetch_batch(self, query: str, batch_size: int = 10000) -> Generator[pd.DataFrame, None, None]:
        """Yields batches of data from a query."""
        if not self.conn:
            self.connect()
        
        with self.conn.cursor() as cursor:
            cursor.execute(query)
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                cols = [desc[0] for desc in cursor.description]
                yield pd.DataFrame(rows, columns=cols)
