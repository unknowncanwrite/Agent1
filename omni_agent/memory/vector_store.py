"""
Vector Store - Optional, falls back to file memory if chroma not available
"""
from pathlib import Path
from typing import List, Dict, Optional

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMER = True
except ImportError:
    HAS_SENTENCE_TRANSFORMER = False

class VectorStore:
    def __init__(self, persist_dir: Path):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = HAS_CHROMA
        self.client = None
        self.collection = None
        self.embed_model = None
        
        if self.enabled:
            try:
                self.client = chromadb.PersistentClient(path=str(self.persist_dir / "chroma"))
                self.collection = self.client.get_or_create_collection("omni_memory")
                # Lazy load embedding model only when needed, don't download at init
                self.embed_model = None
            except Exception as e:
                print(f"Vector store init failed: {e}, falling back to file memory")
                self.enabled = False
    
    def add(self, text: str, metadata: Dict = None, id: str = None):
        if not self.enabled:
            return False
        try:
            import uuid
            doc_id = id or str(uuid.uuid4())
            self.collection.add(
                documents=[text],
                metadatas=[metadata or {}],
                ids=[doc_id]
            )
            return True
        except Exception as e:
            print(f"Vector add failed: {e}")
            return False
    
    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        if not self.enabled:
            return []
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            formatted = []
            if results.get("documents"):
                for i, doc in enumerate(results["documents"][0]):
                    formatted.append({
                        "text": doc,
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                        "distance": results["distances"][0][i] if results.get("distances") else 0
                    })
            return formatted
        except Exception as e:
            print(f"Vector search failed: {e}")
            return []

class HybridMemory:
    """Combines file + vector for best retrieval"""
    def __init__(self, memory_dir: Path):
        from .file_memory import FileMemory
        self.file_memory = FileMemory(memory_dir)
        self.vector_store = VectorStore(memory_dir)
    
    def write(self, category: str, key: str, content: str):
        # Write to both
        path = self.file_memory.write(category, key, content)
        self.vector_store.add(content, metadata={"category": category, "key": key, "file": str(path)}, id=f"{category}_{key}")
        return path
    
    def search(self, query: str) -> List[Dict]:
        # Combine results
        file_results = self.file_memory.search(query)
        vector_results = self.vector_store.search(query)
        
        # Merge - prioritize file memory for exact matches, vector for semantic
        combined = []
        seen = set()
        
        for r in file_results:
            combined.append({"type": "file", "content": r["snippet"], "meta": r, "score": r["score"] * 2})
            seen.add(r["file"])
        
        for r in vector_results:
            combined.append({"type": "vector", "content": r["text"], "meta": r["metadata"], "score": 1.0 - r.get("distance", 0)})
        
        combined.sort(key=lambda x: x["score"], reverse=True)
        return combined[:10]
    
    def get_context_prompt(self, query: str) -> str:
        file_context = self.file_memory.get_context_prompt(query)
        vector_results = self.vector_store.search(query, n_results=3)
        
        vector_context = ""
        if vector_results:
            vector_context = "\n## Semantic Memory:\n"
            for r in vector_results:
                vector_context += f"- {r['text'][:300]}...\n"
        
        return file_context + vector_context
