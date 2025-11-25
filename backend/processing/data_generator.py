import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from connectors.postgres_connector import PostgresConnector
from connectors.mongo_connector import MongoConnector
from utils.logger import setup_logger

logger = setup_logger("DataGenerator")

def generate_machine_metadata(n_machines=10):
    """Generate static machine data for Postgres."""
    machines = []
    for i in range(n_machines):
        machines.append({
            "machine_id": f"CNC-{i:03d}",
            "model": random.choice(["Model-A", "Model-B", "Model-X"]),
            "install_date": datetime.now() - timedelta(days=random.randint(300, 1000)),
            "location": f"Zone-{random.randint(1, 5)}"
        })
    return pd.DataFrame(machines)

def generate_sensor_logs(machine_ids, n_readings=1000):
    """Generate time-series sensor data for MongoDB."""
    logs = []
    start_time = datetime.now() - timedelta(days=1)
    
    for mid in machine_ids:
        # Simulate a degradation curve for one machine
        is_faulty = random.random() < 0.2
        
        for i in range(n_readings):
            timestamp = start_time + timedelta(minutes=i)
            
            # Base values
            vibration = random.gauss(0.5, 0.1)
            temp = random.gauss(60, 5)
            
            # Add anomaly/trend if faulty
            if is_faulty and i > n_readings * 0.8:
                vibration += (i - n_readings * 0.8) * 0.01 # Linear increase
                temp += (i - n_readings * 0.8) * 0.05
                
            logs.append({
                "machine_id": mid,
                "timestamp": timestamp,
                "vibration": vibration,
                "temperature": temp,
                "pressure": random.gauss(100, 10), # Added pressure
                "spindle_speed": random.gauss(12000, 200),
                "status": "running"
            })
    return logs

def populate_databases():
    logger.info("Starting data generation...")
    
    # 1. Postgres Data
    pg = PostgresConnector()
    try:
        pg.connect()
        # Create table if not exists
        with pg.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS machines (
                    machine_id VARCHAR(50) PRIMARY KEY,
                    model VARCHAR(50),
                    install_date TIMESTAMP,
                    location VARCHAR(50)
                );
            """)
            pg.conn.commit()
            
            # Check if empty
            cur.execute("SELECT count(*) FROM machines")
            if cur.fetchone()[0] == 0:
                df_machines = generate_machine_metadata()
                # Simple insert loop for demo
                for _, row in df_machines.iterrows():
                    cur.execute(
                        "INSERT INTO machines (machine_id, model, install_date, location) VALUES (%s, %s, %s, %s)",
                        (row['machine_id'], row['model'], row['install_date'], row['location'])
                    )
                pg.conn.commit()
                logger.info("Populated Postgres 'machines' table.")
            else:
                logger.info("Postgres 'machines' table already has data.")
                
    except Exception as e:
        logger.error(f"Postgres Error: {e}")
    finally:
        pg.close()

    # 2. Mongo Data
    mongo = MongoConnector()
    try:
        mongo.connect()
        if mongo.db.sensor_logs.count_documents({}) == 0:
            # Get machine IDs (mocking fetching from PG)
            machine_ids = [f"CNC-{i:03d}" for i in range(10)]
            logs = generate_sensor_logs(machine_ids)
            mongo.insert_data("sensor_logs", logs)
            logger.info(f"Inserted {len(logs)} sensor logs into MongoDB.")
        else:
            logger.info("MongoDB 'sensor_logs' collection already has data.")
    except Exception as e:
        logger.error(f"Mongo Error: {e}")
    finally:
        mongo.close()

if __name__ == "__main__":
    populate_databases()
