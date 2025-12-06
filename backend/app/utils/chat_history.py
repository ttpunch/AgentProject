from connectors.mongo_connector import MongoConnector
from datetime import datetime
import uuid

def save_message(user_id: str, role: str, content: str, thread_id: str = None, metadata: dict = None):
    """
    Saves a chat message to the MongoDB 'chat_history' collection.
    """
    mongo = MongoConnector()
    try:
        document = {
            "user_id": user_id,
            "thread_id": thread_id,
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

# --- Thread Management Functions ---

def create_thread(user_id: str, title: str = "New Chat"):
    """
    Creates a new thread for a user.
    Returns the new thread_id.
    """
    mongo = MongoConnector()
    try:
        thread_id = str(uuid.uuid4())
        document = {
            "thread_id": thread_id,
            "user_id": user_id,
            "title": title[:50] + "..." if len(title) > 50 else title,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        mongo.insert_one("threads", document)
        return thread_id
    except Exception as e:
        print(f"Error creating thread: {e}")
        return None
    finally:
        mongo.close()

def get_threads(user_id: str):
    """
    Returns all threads for a user, sorted by most recent first.
    Also migrates any orphan messages (without thread_id) to a 'General Chat' thread.
    """
    mongo = MongoConnector()
    try:
        mongo.connect()  # Must connect before accessing db
        # Safety check for mongo.db
        if mongo.db is None:
            print("Warning: MongoDB connection not established")
            return []
        
        # Check for orphan messages (no thread_id or null thread_id)
        try:
            orphan_check = mongo.db["chat_history"].find_one({
                "user_id": user_id,
                "$or": [{"thread_id": None}, {"thread_id": {"$exists": False}}]
            })
            
            if orphan_check:
                # Create a 'General Chat' thread for orphan messages
                general_thread_id = str(uuid.uuid4())
                from datetime import datetime
                mongo.db["threads"].insert_one({
                    "thread_id": general_thread_id,
                    "user_id": user_id,
                    "title": "General Chat (Legacy)",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                # Migrate all orphan messages to this thread
                mongo.db["chat_history"].update_many(
                    {"user_id": user_id, "$or": [{"thread_id": None}, {"thread_id": {"$exists": False}}]},
                    {"$set": {"thread_id": general_thread_id}}
                )
                print(f"Migrated orphan messages to General Chat thread: {general_thread_id}")
        except Exception as migration_err:
            print(f"Warning: Orphan migration failed: {migration_err}")
        
        # Now fetch all threads
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"updated_at": -1}}
        ]
        df = mongo.aggregate("threads", pipeline)
        
        if df.empty:
            return []
        
        if '_id' in df.columns:
            df = df.drop(columns=['_id'])
        
        # Convert timestamps
        for col in ['created_at', 'updated_at']:
            if col in df.columns:
                df[col] = df[col].astype(str)
        
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error fetching threads: {e}")
        return []
    finally:
        mongo.close()

def get_thread_history(user_id: str, thread_id: str):
    """
    Returns messages for a specific thread.
    """
    mongo = MongoConnector()
    try:
        print(f"DEBUG get_thread_history: user_id={user_id}, thread_id={thread_id}")
        pipeline = [
            {"$match": {"user_id": user_id, "thread_id": thread_id}},
            {"$sort": {"timestamp": 1}}
        ]
        df = mongo.aggregate("chat_history", pipeline)
        
        print(f"DEBUG get_thread_history: Found {len(df)} messages")
        
        if df.empty:
            return []
        
        if '_id' in df.columns:
            df = df.drop(columns=['_id'])
        if 'timestamp' in df.columns:
            df['timestamp'] = df['timestamp'].astype(str)
        
        result = df.to_dict(orient="records")
        print(f"DEBUG get_thread_history: Returning {len(result)} messages")
        return result
    except Exception as e:
        print(f"Error fetching thread history: {e}")
        return []
    finally:
        mongo.close()

def update_thread_title(thread_id: str, title: str):
    """
    Updates the title and updated_at timestamp for a thread.
    """
    print(f"DEBUG update_thread_title: thread_id={thread_id}, title={title[:50]}")
    mongo = MongoConnector()
    try:
        mongo.connect()  # Must connect before accessing db
        result = mongo.db["threads"].update_one(
            {"thread_id": thread_id},
            {"$set": {
                "title": title[:50] + "..." if len(title) > 50 else title,
                "updated_at": datetime.utcnow()
            }}
        )
        print(f"DEBUG update_thread_title: modified_count={result.modified_count}")
    except Exception as e:
        print(f"Error updating thread title: {e}")
    finally:
        mongo.close()

def delete_thread(user_id: str, thread_id: str):
    """
    Deletes a thread and all its messages.
    """
    mongo = MongoConnector()
    try:
        mongo.connect()  # Must connect before accessing db
        if mongo.db is None:
            print("Warning: MongoDB connection not established for delete")
            return False
        # Delete thread
        mongo.db["threads"].delete_one({"thread_id": thread_id, "user_id": user_id})
        # Delete all messages in thread
        mongo.db["chat_history"].delete_many({"thread_id": thread_id, "user_id": user_id})
        print(f"DEBUG: Deleted thread {thread_id}")
        return True
    except Exception as e:
        print(f"Error deleting thread: {e}")
        return False
    finally:
        mongo.close()

