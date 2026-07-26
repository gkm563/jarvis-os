"""
Semantic Vector Memory Store for JARVIS OS.
Integrates ChromaDB for RAG over past task history, user preferences, and document context.
"""

from typing import Any, Dict, List, Optional
from jarvis.config.settings import settings
from jarvis.utils.logger import get_logger

logger = get_logger("VectorStore")


class VectorMemoryStore:
    """
    ChromaDB-backed semantic vector memory manager.
    Supports storing text documents/events with metadata and performing similarity searches.
    """

    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_directory = persist_directory or settings.CHROMADB_PATH
        self._client = None
        self._collection = None
        self._in_memory_docs: List[Dict[str, Any]] = []
        self._init_chroma()

    def _init_chroma(self):
        """Initializes ChromaDB client or falls back gracefully."""
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=self.persist_directory)
            self._collection = self._client.get_or_create_collection(name="jarvis_semantic_memory")
            logger.info(f"ChromaDB Vector Store initialized at '{self.persist_directory}'")
        except Exception as e:
            logger.warning(f"ChromaDB failed to initialize ({str(e)}). Falling back to lightweight memory store.")

    def add_document(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Embeds and stores a document in the vector database.

        Args:
            doc_id (str): Unique document identifier.
            text (str): Document text content.
            metadata (Dict): Metadata attributes.

        Returns:
            bool: True if stored successfully.
        """
        metadata = metadata or {}
        if self._collection:
            try:
                self._collection.add(
                    ids=[doc_id],
                    documents=[text],
                    metadatas=[metadata],
                )
                logger.debug(f"Document '{doc_id}' added to ChromaDB vector store")
                return True
            except Exception as e:
                logger.error(f"Failed to add document to ChromaDB: {str(e)}")

        self._in_memory_docs.append({"id": doc_id, "text": text, "metadata": metadata})
        return True

    def search_similar(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Performs vector similarity search against the semantic memory.

        Args:
            query (str): Search query string.
            top_k (int): Number of top results to return.

        Returns:
            List[Dict]: List of matching document payloads.
        """
        if self._collection:
            try:
                results = self._collection.query(query_texts=[query], n_results=top_k)
                hits = []
                if results and "documents" in results and results["documents"]:
                    docs = results["documents"][0]
                    ids = results["ids"][0]
                    metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
                    for doc_id, doc_text, meta in zip(ids, docs, metas):
                        hits.append({"id": doc_id, "text": doc_text, "metadata": meta})
                return hits
            except Exception as e:
                logger.error(f"Vector search failed in ChromaDB: {str(e)}")

        # Fallback simple keyword search
        matches = [d for d in self._in_memory_docs if any(word.lower() in d["text"].lower() for word in query.split())]
        return matches[:top_k]
