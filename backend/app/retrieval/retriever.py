"""Dual-layer RAG retriever.

Layer 1: Semantic recall - find relevant chunks via vector similarity.
Layer 2: Perspective extraction - extract user opinions from retrieved chunks.
"""

from dataclasses import dataclass, field

from app.llm.base import BaseLLMProvider, LLMMessage, MessageRole
from app.retrieval.embedder import EmbeddingService, get_embedding_service
from app.retrieval.vector_store import VectorStoreService, SearchResult
from app.retrieval.perspective_extractor import PerspectiveExtractor, ExtractedPerspective
from app.services.prompt_loader import PromptLoader
from app.observability.logger import AgentLogAdapter


@dataclass
class RetrievalResult:
    """Complete result from dual-layer retrieval."""

    query: str
    layer1_results: list[SearchResult]
    layer2_perspectives: list[ExtractedPerspective]
    total_latency_ms: float = 0.0


class DualLayerRetriever:
    """Two-stage retrieval: semantic recall + perspective extraction.

    Layer 1: Retrieves semantically relevant chunks from ChromaDB.
    Layer 2: Extracts user perspectives/opinions from those chunks.
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStoreService | None = None,
        prompt_loader: PromptLoader | None = None,
    ):
        self.llm = llm_provider
        self.embedder = embedding_service or get_embedding_service()
        self.vector_store = vector_store or VectorStoreService()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.perspective_extractor = PerspectiveExtractor(llm_provider, prompt_loader)
        self.logger = AgentLogAdapter("dual_layer_retriever")

    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int | None = None,
        extract_perspectives: bool = True,
    ) -> RetrievalResult:
        """Execute dual-layer retrieval.

        Args:
            query: The search query (topic or question).
            user_id: Filter results to this user's documents.
            top_k: Number of results for layer 1. Defaults to config.
            extract_perspectives: Whether to run layer 2.

        Returns:
            RetrievalResult with both layer results.
        """
        import time
        start = time.monotonic()

        # Layer 1: Semantic recall
        query_embedding = self.embedder.embed_text(query)
        layer1_results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k or 10,
            where={"user_id": user_id},
        )

        # Layer 2: Perspective extraction
        layer2_perspectives = []
        if extract_perspectives and layer1_results:
            layer2_perspectives = await self.perspective_extractor.extract(
                query=query,
                chunks=[(r.chunk_id, r.content, r.metadata) for r in layer1_results],
            )

        latency_ms = (time.monotonic() - start) * 1000

        self.logger.log_execution(
            input_summary=f"Query: {query[:100]}",
            output_summary=f"Layer 1: {len(layer1_results)} chunks, Layer 2: {len(layer2_perspectives)} perspectives",
            latency_ms=latency_ms,
        )

        return RetrievalResult(
            query=query,
            layer1_results=layer1_results,
            layer2_perspectives=layer2_perspectives,
            total_latency_ms=latency_ms,
        )

    async def retrieve_for_topic(
        self,
        topic_title: str,
        topic_summary: str,
        user_id: str,
    ) -> RetrievalResult:
        """Retrieve knowledge relevant to a hot topic.

        Constructs a focused query from the topic information.
        """
        query = f"{topic_title}: {topic_summary}"
        return await self.retrieve(query=query, user_id=user_id, extract_perspectives=True)
