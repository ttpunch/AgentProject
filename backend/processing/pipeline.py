from pyspark.sql import SparkSession
from pyspark.sql.functions import col, window, avg, stddev
from connectors.mongo_connector import MongoConnector
from models.anomaly_detector import AnomalyDetector
from utils.logger import setup_logger
import pandas as pd
import os

logger = setup_logger("AnalysisPipeline")

def get_spark_session():
    return SparkSession.builder \
        .appName("CNC_Maintenance_Analysis") \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "2g") \
        .getOrCreate()

def run_pipeline():
    logger.info("Starting Analysis Pipeline...")
    
    # 1. Fetch Data (Push-down aggregation to handle 'billions' scale)
    # We aggregate raw logs to 1-minute intervals before loading to Spark/Pandas
    mongo = MongoConnector()
    pipeline = [
        {
            "$group": {
                "_id": {
                    "machine_id": "$machine_id",
                    "timestamp": {
                        "$dateTrunc": {"date": "$timestamp", "unit": "minute"}
                    }
                },
                "avg_vibration": {"$avg": "$vibration"},
                "avg_temp": {"$avg": "$temperature"},
                "avg_speed": {"$avg": "$spindle_speed"}
            }
        },
        {"$sort": {"_id.timestamp": 1}}
    ]
    
    logger.info("Fetching aggregated data from MongoDB...")
    df_agg = mongo.aggregate("sensor_logs", pipeline)
    
    if df_agg.empty:
        logger.warning("No data found. Please run data generator first.")
        return

    # Flatten the _id field
    df_agg['machine_id'] = df_agg['_id'].apply(lambda x: x['machine_id'])
    df_agg['timestamp'] = df_agg['_id'].apply(lambda x: x['timestamp'])
    df_agg = df_agg.drop(columns=['_id'])
    
    logger.info(f"Loaded {len(df_agg)} aggregated records.")

    # 2. Feature Engineering with Spark
    # Even though we aggregated, we might want rolling windows over the aggregated data
    spark = get_spark_session()
    sdf = spark.createDataFrame(df_agg)
    
    # Example: Calculate 1-hour moving average of vibration
    # For simplicity in this demo, we'll just use the aggregated values directly
    # but here is where you'd add complex Spark window functions.
    
    # 3. Train Anomaly Detector
    # We convert back to Pandas for sklearn model (Hybrid approach)
    # In a real 'billion row' scenario, we would sample here.
    pdf_train = sdf.toPandas()
    
    detector = AnomalyDetector()
    features = ['avg_vibration', 'avg_temp', 'avg_speed']
    detector.train(pdf_train, features)
    
    # 4. Predict
    results = detector.predict(pdf_train, features)
    
    # 5. Save Results (e.g., back to Postgres or Mongo)
    # For now, just print anomalies
    anomalies = results[results['is_anomaly'] == 1]
    logger.info(f"Detected {len(anomalies)} anomalies.")
    if not anomalies.empty:
        logger.info(f"Sample anomalies:\n{anomalies.head()}")
    
    spark.stop()
    logger.info("Pipeline finished.")

if __name__ == "__main__":
    run_pipeline()
