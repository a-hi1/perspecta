"""RAG evaluation pipeline.

Evaluates:
1. Retrieval relevance - how well retrieved chunks match the query
2. Perspective quality - whether extracted perspectives are genuine opinions
3. Hallucination detection - whether generated content has source backing
"""

import json
from dataclasses import dataclass, field

from app.llm.base import BaseLLMProvider, LLMMessage, MessageRole
from app.observability.logger import AgentLogAdapter


@dataclass
class EvaluationReport:
    """Evaluation report for a RAG pipeline run."""

    retrieval_relevance: float = 0.0
    perspective_quality: float = 0.0
    hallucination_score: float = 0.0  # 0 = no hallucination detected, 1 = likely hallucinated
    overall_score: float = 0.0
    details: dict = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    @property
    def is_acceptable(self) -> bool:
        """Whether the quality is acceptable for human review."""
        return (
            self.retrieval_relevance >= 0.6
            and self.perspective_quality >= 0.6
            and self.hallucination_score <= 0.3
        )

    def summary(self) -> str:
        status = "PASS" if self.is_acceptable else "NEEDS REVIEW"
        return (
            f"[{status}] "
            f"Relevance: {self.retrieval_relevance:.2f} | "
            f"Perspective: {self.perspective_quality:.2f} | "
            f"Hallucination: {self.hallucination_score:.2f} | "
            f"Overall: {self.overall_score:.2f}"
        )


class RAGEvaluator:
    """Evaluates RAG pipeline quality using LLM-as-judge approach."""

    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider
        self.logger = AgentLogAdapter("rag_evaluator")

    async def evaluate_retrieval(
        self, query: str, retrieved_chunks: list[dict]
    ) -> float:
        """Evaluate how relevant retrieved chunks are to the query.

        Returns a score from 0 to 1.
        """
        if not retrieved_chunks:
            return 0.0

        chunk_summaries = "\n".join(
            f"- [{c.get('chunk_id', '?')[:8]}] {c.get('content', '')[:200]}"
            for c in retrieved_chunks[:5]
        )

        messages = [
            LLMMessage(
                role=MessageRole.SYSTEM,
                content="You are a retrieval quality evaluator. Rate how relevant the retrieved chunks are to the query. Output JSON with a single 'score' field (0.0-1.0).",
            ),
            LLMMessage(
                role=MessageRole.USER,
                content=f"Query: {query}\n\nRetrieved chunks:\n{chunk_summaries}\n\nRate relevance (0.0-1.0):",
            ),
        ]

        try:
            response = await self.llm.chat(
                messages=messages,
                temperature=0.1,
                max_tokens=100,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.content)
            return float(data.get("score", 0.5))
        except Exception:
            return 0.5  # Default to neutral on error

    async def evaluate_perspective_quality(
        self, perspectives: list[dict]
    ) -> float:
        """Evaluate whether extracted perspectives are genuine opinions.

        Returns a score from 0 to 1.
        """
        if not perspectives:
            return 0.0

        perspective_texts = "\n".join(
            f"- [{p.get('perspective_type', '?')}] {p.get('perspective_text', '')[:200]}"
            for p in perspectives[:5]
        )

        messages = [
            LLMMessage(
                role=MessageRole.SYSTEM,
                content="You are a perspective quality evaluator. Assess whether these are genuine personal opinions/experiences (high score) vs generic facts or AI-generated platitudes (low score). Output JSON with 'score' field (0.0-1.0).",
            ),
            LLMMessage(
                role=MessageRole.USER,
                content=f"Perspectives to evaluate:\n{perspective_texts}\n\nRate quality (0.0-1.0):",
            ),
        ]

        try:
            response = await self.llm.chat(
                messages=messages,
                temperature=0.1,
                max_tokens=100,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.content)
            return float(data.get("score", 0.5))
        except Exception:
            return 0.5

    async def check_hallucination(
        self,
        generated_text: str,
        source_chunks: list[dict],
    ) -> float:
        """Check if generated text has source backing.

        Returns a hallucination score from 0 (no hallucination) to 1 (likely hallucinated).
        """
        if not source_chunks or not generated_text:
            return 0.0

        source_texts = "\n---\n".join(
            c.get("content", "")[:300] for c in source_chunks[:5]
        )

        messages = [
            LLMMessage(
                role=MessageRole.SYSTEM,
                content="You are a hallucination detector. Compare the generated text against the source material. Identify any claims not supported by sources. Output JSON with 'hallucination_score' (0.0-1.0, where 0 = fully supported, 1 = mostly hallucinated) and 'unsupported_claims' list.",
            ),
            LLMMessage(
                role=MessageRole.USER,
                content=f"Generated text:\n{generated_text[:1000]}\n\nSource material:\n{source_texts}\n\nEvaluate:",
            ),
        ]

        try:
            response = await self.llm.chat(
                messages=messages,
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.content)
            return float(data.get("hallucination_score", 0.0))
        except Exception:
            return 0.0

    async def full_evaluation(
        self,
        query: str,
        retrieved_chunks: list[dict],
        perspectives: list[dict],
        generated_text: str,
    ) -> EvaluationReport:
        """Run a full evaluation of the RAG pipeline output."""
        import time
        start = time.monotonic()

        relevance = await self.evaluate_retrieval(query, retrieved_chunks)
        quality = await self.evaluate_perspective_quality(perspectives)
        hallucination = await self.check_hallucination(generated_text, retrieved_chunks)

        overall = (relevance * 0.3 + quality * 0.4 + (1.0 - hallucination) * 0.3)

        recommendations = []
        if relevance < 0.6:
            recommendations.append("Improve retrieval: consider rephrasing query or expanding knowledge base")
        if quality < 0.6:
            recommendations.append("Perspectives may be too generic: refine extraction prompt")
        if hallucination > 0.3:
            recommendations.append("Possible hallucination detected: verify generated claims against sources")

        report = EvaluationReport(
            retrieval_relevance=relevance,
            perspective_quality=quality,
            hallucination_score=hallucination,
            overall_score=overall,
            recommendations=recommendations,
        )

        self.logger.log_execution(
            input_summary=f"Query: {query[:80]}",
            output_summary=report.summary(),
            latency_ms=(time.monotonic() - start) * 1000,
        )

        return report
