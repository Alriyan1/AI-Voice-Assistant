from typing import List, Dict, Optional, Any
import json
from loguru import logger
from memory.database import MemoryDatabase
import faiss
import numpy as np
from pathlib import Path


class AgentMemory:

    embedding_dimension = 384
    embedding_model_name = "all-MiniLM-L6-v2"
    
    def __init__(self):
        self.db = MemoryDatabase()
        self.short_term_memory: List[Dict] = []
        self.max_short_term = 10
        self.faiss_index = None
        self.faiss_memory_ids: List[int] = []
        self._embedding_model = None
        self._init_faiss()
        self._load_semantic_memories()
    
    def _init_faiss(self) -> None:
        try:
            self.faiss_index = faiss.IndexFlatIP(self.embedding_dimension)
            logger.info("FAISS index initialized")
        except Exception as e:
            logger.warning(f"FAISS initialization failed: {e}")
            self.faiss_index = None

    def _get_embedding_model(self):
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:
                raise RuntimeError(
                    "Semantic memory requires the 'sentence-transformers' package"
                ) from e
            self._embedding_model = SentenceTransformer(self.embedding_model_name)
        return self._embedding_model

    def _embed(self, text: str) -> np.ndarray:
        embedding = self._get_embedding_model().encode(
            [text], convert_to_numpy=True, normalize_embeddings=True
        )
        return np.asarray(embedding, dtype="float32")

    def _load_semantic_memories(self) -> None:
        if self.faiss_index is None:
            return

        try:
            with self.db.get_connection() as conn:
                rows = conn.execute(
                    "SELECT id, embedding FROM semantic_memory ORDER BY id"
                ).fetchall()

            vectors = []
            for row in rows:
                if not row["embedding"]:
                    continue
                vector = np.frombuffer(row["embedding"], dtype="float32")
                if vector.size != self.embedding_dimension:
                    logger.warning(
                        f"Skipping semantic memory {row['id']}: invalid embedding size"
                    )
                    continue
                vectors.append(vector)
                self.faiss_memory_ids.append(row["id"])

            if vectors:
                self.faiss_index.add(np.vstack(vectors))
        except Exception as e:
            logger.warning(f"Loading semantic memories failed: {e}")
    
    def add_to_short_term(self, entry: Dict) -> None:
        
        self.short_term_memory.append(entry)
        
        # Trim if too long
        if len(self.short_term_memory) > self.max_short_term:
            self.short_term_memory = self.short_term_memory[-self.max_short_term:]
        
        logger.debug(f"Added to short-term memory: {entry.get('command', 'unknown')}")
    
    def get_short_term_memory(self) -> List[Dict]:
        return self.short_term_memory.copy()
    
    def clear_short_term(self) -> None:
        self.short_term_memory = []
        logger.info("Short-term memory cleared")
    
    def save_preference(self, key: str, value: Any) -> bool:
        return self.db.save_preference(key, value)
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.db.get_preference(key, default)
    
    def save_path(self, name: str, path: str, description: Optional[str] = None) -> bool:
        return self.db.save_file_path(name, path, description)
    
    def get_path(self, name: str) -> Optional[str]:
        return self.db.get_file_path(name)
    
    def get_all_paths(self) -> List[Dict]:
        return self.db.get_all_file_paths()
    
    def log_action(
        self,
        user_command: str,
        selected_tool: str,
        arguments: Dict,
        result: str,
        success: bool
    ) -> bool:
        return self.db.log_action(
            user_command,
            selected_tool,
            arguments,
            result,
            success
        )
    
    def get_action_history(self, limit: int = 50) -> List[Dict]:
        """Get recent action history."""
        return self.db.get_action_history(limit)
    
    def get_recent_conversations(self, limit: int = 10) -> List[Dict]:
        """Get recent conversations."""
        return self.db.get_recent_conversations(limit)
    
    def add_semantic_memory(self, content: str, metadata: Optional[Dict] = None) -> bool:
        
        try:
            if not content or not content.strip():
                raise ValueError("content must not be empty")
            if self.faiss_index is None:
                raise RuntimeError("FAISS index is not initialized")

            embedding = self._embed(content)
            serialized_metadata = json.dumps(metadata) if metadata is not None else None

            with self.db.get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO semantic_memory (content, embedding, metadata) VALUES (?, ?, ?)",
                    (content, embedding[0].tobytes(), serialized_metadata)
                )
                memory_id = cursor.lastrowid

            self.faiss_index.add(embedding)
            self.faiss_memory_ids.append(memory_id)
            
            logger.info(f"Added semantic memory: {content[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Add semantic memory failed: {e}")
            return False
    
    def search_semantic_memory(self, query: str, top_k: int = 5) -> List[Dict]:
        
        try:
            if not query or not query.strip() or top_k <= 0:
                return []
            if self.faiss_index is None or self.faiss_index.ntotal == 0:
                return []
            
            query_embedding = self._embed(query)
            
            distances, indices = self.faiss_index.search(
                query_embedding, min(top_k, self.faiss_index.ntotal)
            )
            
            memory_ids = [
                self.faiss_memory_ids[index]
                for index in indices[0]
                if 0 <= index < len(self.faiss_memory_ids)
            ]
            if not memory_ids:
                return []

            placeholders = ", ".join("?" for _ in memory_ids)
            with self.db.get_connection() as conn:
                rows = conn.execute(
                    f"SELECT id, content, metadata, created_at FROM semantic_memory "
                    f"WHERE id IN ({placeholders})",
                    memory_ids,
                ).fetchall()

            rows_by_id = {row["id"]: row for row in rows}
            results = []
            for distance, memory_id in zip(distances[0], memory_ids):
                row = rows_by_id.get(memory_id)
                if row is None:
                    continue
                results.append({
                    "id": row["id"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                    "created_at": row["created_at"],
                    "score": float(distance),
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def get_context_for_agent(self) -> Dict:
        
        return {
            'recent_actions': self.get_action_history(5),
            'preferences': {
                'saved_paths': self.get_all_paths()
            },
            'short_term_memory': self.get_short_term_memory()
        }
    
    def cleanup(self) -> None:
        self.db.clear_old_actions(days=30)
        logger.info("Memory cleanup completed")