import os
import shutil
from typing import List, Dict, Any
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Configuration
PERSIST_DIRECTORY = "./chroma_db"
DATA_DIRECTORY = "./data"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Ensure directories exist
os.makedirs(PERSIST_DIRECTORY, exist_ok=True)
os.makedirs(DATA_DIRECTORY, exist_ok=True)

class RAGManager:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self.vectorstore = Chroma(
            persist_directory=PERSIST_DIRECTORY,
            embedding_function=self.embeddings
        )

    def add_document(self, file_path: str, original_filename: str):
        """
        Loads a document, splits it, and adds it to the vector store.
        """
        file_ext = os.path.splitext(original_filename)[1].lower()
        
        if file_ext == ".pdf":
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path)
            
        docs = loader.load()
        
        # Add metadata
        for doc in docs:
            doc.metadata["source"] = original_filename
            
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        splits = text_splitter.split_documents(docs)
        
        self.vectorstore.add_documents(splits)
        # self.vectorstore.persist() # Chroma 0.4+ persists automatically usually, but good to check version. 
        # In newer langchain-chroma, persist() might be deprecated or auto. 
        # We will assume auto-persist or handled by the client.
        
        return len(splits)

    def delete_document(self, filename: str):
        """
        Deletes a document from the vector store and the filesystem.
        """
        try:
            # Delete from Vector Store
            # Note: This is specific to Chroma's underlying collection API
            self.vectorstore._collection.delete(where={"source": filename})
            
            # Delete from Filesystem
            file_path = os.path.join(DATA_DIRECTORY, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            else:
                print(f"File {file_path} not found on disk, but removed from DB.")
                return True
                
        except Exception as e:
            print(f"Error deleting document {filename}: {e}")
            raise e

    def query(self, question: str, k: int = 4):
        """
        Queries the vector store.
        """
        return self.vectorstore.similarity_search(question, k=k)

    def list_documents(self) -> List[str]:
        """
        Lists unique source documents in the vector store.
        Note: Chroma doesn't have a direct 'list all sources' optimized query, 
        so we might need to fetch all metadata. For large DBs this is slow, 
        but for this demo it's fine.
        """
        # This is a bit hacky for Chroma, but we can get collection data
        data = self.vectorstore.get()
        metadatas = data['metadatas']
        sources = set()
        for m in metadatas:
            if m and "source" in m:
                sources.add(m["source"])
        return list(sources)

    def get_vector_sample(self) -> List[Dict[str, Any]]:
        """
        Returns a sample of documents with their embeddings (truncated) for visualization.
        """
        data = self.vectorstore.get(include=['embeddings', 'metadatas', 'documents'], limit=5)
        
        samples = []
        for i in range(len(data['ids'])):
            samples.append({
                "id": data['ids'][i],
                "source": data['metadatas'][i].get("source", "Unknown"),
                "content_preview": data['documents'][i][:100] + "...",
                "embedding_preview": list(data['embeddings'][i][:5]) + ["..."] # Show first 5 dims
            })
        return samples

# Singleton instance
rag_manager = RAGManager()
