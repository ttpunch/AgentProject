from pyspark.sql import DataFrame
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.clustering import KMeans # Using KMeans as simple anomaly detector proxy if IF not available, but IF is in 3.0+
# Note: IsolationForest is available in Spark 3.0+
# For this demo, we'll use a simple statistical approach or KMeans if IF is tricky to setup without proper jars
# Let's try to use a simple thresholding on moving averages first for robustness, 
# or use sklearn on collected data if Spark is too heavy for the container without tuning.
# Actually, let's use Spark SQL for feature engineering and sklearn for the actual model to save memory.

from sklearn.ensemble import IsolationForest
import pandas as pd
import joblib
import os
from utils.logger import setup_logger

logger = setup_logger("AnomalyDetector")

class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.model_path = "models/saved/isolation_forest.joblib"

    def train(self, df: pd.DataFrame, features: list):
        """Train Isolation Forest on Pandas DataFrame."""
        logger.info(f"Training Isolation Forest on {len(df)} records...")
        X = df[features]
        self.model.fit(X)
        logger.info("Training complete.")
        
        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        logger.info(f"Model saved to {self.model_path}")

    def predict(self, df: pd.DataFrame, features: list) -> pd.DataFrame:
        """Predict anomalies."""
        X = df[features]
        predictions = self.model.predict(X)
        # -1 is anomaly, 1 is normal. Map to 1 (anomaly) and 0 (normal)
        df['is_anomaly'] = [1 if x == -1 else 0 for x in predictions]
        return df
