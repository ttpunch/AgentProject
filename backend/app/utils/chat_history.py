from connectors.mongo_connector import MongoConnector
from datetime import datetime
import uuid

def save_message(user_id: str, role: str, content: str, metadata: dict = None):
    """
    Saves a chat message to the MongoDB 'chat_history' collection.
    """
    mongo = MongoConnector()
    try:
        document = {
            "user_id": user_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow(),
            "message_id": str(uuid.uuid4())
        }
        if metadata:
            document["metadata"] = metadata
            
        mongo.insert_one("chat_history", document)
    except Exception as e:
        print(f"Error saving chat message: {e}")
    finally:
        mongo.close()

def get_history(user_id: str, limit: int = 50):
    """
    Retrieves chat history for a specific user, sorted by timestamp.
    """
    mongo = MongoConnector()
    try:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"timestamp": 1}}, # Ascending order for chat display
            # {"$limit": limit} # Optional: limit history
        ]
        
        df = mongo.aggregate("chat_history", pipeline)
        
        if df.empty:
            return []
            
        # Convert to list of dicts
        if '_id' in df.columns:
            df = df.drop(columns=['_id'])
            
        # Convert timestamp to string
        if 'timestamp' in df.columns:
            df['timestamp'] = df['timestamp'].astype(str)
            
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error fetching chat history: {e}")
        return []
    finally:
        mongo.close()
