"""Embedding service using bge-m3."""

import os
from functools import lru_cache

import numpy as np

from app.core.config import get_settings


class EmbeddingService:
    """Generates embeddings using BAAI/bge-m3 model.

    Uses sentence-transformers for local inference.
    """

    def __init__(self, model_name: str | None = None, device: str | None = None):
        settings = get_settings()
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self.device = device or settings.EMBEDDING_DEVICE
        self._model = None

    def _load_model(self):
        """Lazy-load the embedding model."""
        if self._model is None:
            try:
                # Set HF mirror endpoint for faster download in China
                settings = get_settings()
                if settings.HF_ENDPOINT:
                    os.environ["HF_ENDPOINT"] = settings.HF_ENDPOINT
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, device=self.device)
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for embeddings. "
                    "Install with: pip install sentence-transformers"
                )

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        self._load_model()
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Generate embeddings for multiple texts in batches."""
        self._load_model()
        embeddings = self._model.encode(
            texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False
        )
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        self._load_model()
        return self._model.get_sentence_embedding_dimension()


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """Get a cached embedding service instance."""
    return EmbeddingService()
