"""ChromaDB vector store service."""

from dataclasses import dataclass

from app.core.config import get_settings


@dataclass
class SearchResult:
    """A single search result from the vector store."""

    chunk_id: str
    content: str
    score: float
    metadata: dict


class VectorStoreService:
    """Manages document embeddings in ChromaDB."""

    def __init__(self, collection_name: str | None = None):
        settings = get_settings()
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self._client = None
        self._collection = None

    def _get_client(self):
        """Lazy-initialize ChromaDB client."""
        if self._client is None:
            try:
                import chromadb
                settings = get_settings()
                self._client = chromadb.HttpClient(
                    host=settings.CHROMA_HOST,
                    port=settings.CHROMA_PORT,
                )
            except Exception:
                # Fallback to persistent local client
                import chromadb
                self._client = chromadb.PersistentClient(path="./chroma_data")
        return self._client

    def _get_collection(self):
        """Get or create the collection."""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def add_chunks(
        self,
        chunk_ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> None:
        """Add document chunks to the vector store."""
        collection = self._get_collection()
        collection.upsert(
            ids=chunk_ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        where: dict | None = None,
    ) -> list[SearchResult]:
        """Search for similar chunks using cosine similarity."""
        collection = self._get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        search_results = []
        if results and results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                search_results.append(SearchResult(
                    chunk_id=chunk_id,
                    content=results["documents"][0][i],
                    score=1.0 - results["distances"][0][i],  # Convert distance to similarity
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                ))

        return search_results

    def delete_chunks(self, chunk_ids: list[str]) -> None:
        """Delete chunks by ID."""
        collection = self._get_collection()
        collection.delete(ids=chunk_ids)

    def delete_by_document(self, document_id: str) -> None:
        """Delete all chunks belonging to a document."""
        collection = self._get_collection()
        collection.delete(where={"document_id": document_id})

    def count(self) -> int:
        """Return total number of chunks in the collection."""
        return self._get_collection().count()
