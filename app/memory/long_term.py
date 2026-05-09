import os
import json
import requests
from typing import List, Dict
import chromadb


class OllamaEmbeddingFunction:
    """Ollama嵌入函数"""
    
    def __init__(self, model_name: str = "qwen3-embedding:0.6b", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
    
    def name(self) -> str:
        return f"ollama-{self.model_name}"
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        embeddings = []
        for text in input:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text}
            )
            if response.status_code == 200:
                embeddings.append(response.json()["embedding"])
            else:
                raise Exception(f"Ollama embedding failed: {response.text}")
        return embeddings


class LongTermMemory:
    """长期记忆，基于ChromaDB + Ollama本地嵌入模型"""

    def __init__(self, persist_dir: str = "./chroma_data"):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        
        # 使用Ollama本地嵌入模型
        self.embedding_fn = OllamaEmbeddingFunction(
            model_name="qwen3-embedding:0.6b"
        )
        
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="agent_memory",
            metadata={"hnsw:space": "cosine"},
            embedding_function=self.embedding_fn
        )

    def store(self, user_id: int, query: str, result: str, metadata: Dict = None):
        doc_id = f"user_{user_id}_{len(self.collection.get()['ids'])}"
        self.collection.add(
            documents=[f"问题: {query}\n回答: {result}"],
            metadatas=[{"user_id": user_id, **(metadata or {})}],
            ids=[doc_id]
        )

    def retrieve(self, user_id: int, query: str, k: int = 3) -> str:
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=k,
                where={"user_id": user_id}
            )
            if results["documents"] and results["documents"][0]:
                return "\n---\n".join(results["documents"][0])
        except Exception:
            pass
        return ""

    def clear_user_memory(self, user_id: int):
        try:
            self.collection.delete(where={"user_id": user_id})
        except Exception:
            pass
