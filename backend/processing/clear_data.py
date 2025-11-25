import logging
from connectors.postgres_connector import PostgresConnector
from connectors.mongo_connector import MongoConnector
from utils.logger import setup_logger

logger = setup_logger("ClearData")

def clear_databases():
    logger.info("Clearing data from databases...")
    
    # 1. Clear Postgres Data
    pg = PostgresConnector()
    try:
        pg.connect()
        with pg.conn.cursor() as cur:
            # Check if table exists first
            cur.execute("SELECT to_regclass('public.machines')")
            if cur.fetchone()[0]:
                cur.execute("TRUNCATE TABLE machines")
                pg.conn.commit()
                logger.info("Cleared Postgres 'machines' table.")
            else:
                logger.info("Postgres 'machines' table does not exist.")
    except Exception as e:
        logger.error(f"Postgres Error: {e}")
    finally:
        pg.close()

    # 2. Clear Mongo Data
    mongo = MongoConnector()
    try:
        mongo.connect()
        # Delete all documents from sensor_logs
        result = mongo.db.sensor_logs.delete_many({})
        logger.info(f"Deleted {result.deleted_count} documents from MongoDB 'sensor_logs'.")
    except Exception as e:
        logger.error(f"Mongo Error: {e}")
    finally:
        mongo.close()

if __name__ == "__main__":
    clear_databases()
