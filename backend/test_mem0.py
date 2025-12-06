from mem0 import Memory
import os

config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "cnc_memory_test_v2",
            "host": "cnc_qdrant",
            "port": 6333,
            "embedding_model_dims": 384
        }
    },
    "embedder": {
        "provider": "huggingface",
        "config": {
            "model": "sentence-transformers/all-MiniLM-L6-v2"
        }
    }
}

print("Initializing Memory...")
try:
    m = Memory.from_config(config)
    print("Memory initialized.")
    print("Adding memory...")
    m.add("I am testing memory.", user_id="test_user")
    print("Memory added.")
    print("Searching memory...")
    res = m.search("Who am I?", user_id="test_user")
    print(f"Search result: {res}")
except Exception as e:
    print(f"Error: {e}")
