"""Layer 2: Perspective extraction from retrieved chunks.

Extracts user judgments, reflections, lessons, controversies, and summaries
from document chunks using LLM analysis.
"""

import json
from dataclasses import dataclass

from app.llm.base import BaseLLMProvider, LLMMessage, MessageRole
from app.services.prompt_loader import PromptLoader
from app.observability.logger import AgentLogAdapter


@dataclass
class ExtractedPerspective:
    """A perspective extracted from a knowledge chunk."""

    perspective_text: str
    perspective_type: str  # judgment, reflection, lesson, controversy, summary
    source_chunk_ids: list[str]
    source_quotes: list[str]
    confidence: float
    novelty: float
    engagement_potential: float
    reasoning: str


class PerspectiveExtractor:
    """Extracts user perspectives from document chunks using LLM.

    This is Layer 2 of the dual-layer RAG pipeline.
    Takes semantic recall results and extracts genuine user viewpoints.
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        prompt_loader: PromptLoader | None = None,
    ):
        self.llm = llm_provider
        self.prompt_loader = prompt_loader or PromptLoader()
        self.logger = AgentLogAdapter("perspective_extractor")

    async def extract(
        self,
        query: str,
        chunks: list[tuple[str, str, dict]],
    ) -> list[ExtractedPerspective]:
        """Extract perspectives from chunks relevant to a query.

        Args:
            query: The topic/query to find perspectives for.
            chunks: List of (chunk_id, content, metadata) tuples.

        Returns:
            List of extracted perspectives.
        """
        import time
        start = time.monotonic()

        if not chunks:
            return []

        # Build the chunk context
        chunk_context = self._build_chunk_context(chunks)

        # Load prompt
        prompt_content = self.prompt_loader.get_agent_prompt_content(
            "perspective_discovery_agent"
        )

        # Build messages
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=prompt_content),
            LLMMessage(
                role=MessageRole.USER,
                content=f"""## Hot Topic / Query
{query}

## Retrieved Knowledge Chunks
{chunk_context}

Extract genuine user perspectives from these chunks. Output as JSON.""",
            ),
        ]

        # Call LLM
        try:
            response = await self.llm.chat(
                messages=messages,
                temperature=0.3,  # Lower temperature for more grounded extraction
                response_format={"type": "json_object"},
            )

            perspectives = self._parse_response(response.content)

            self.logger.log_execution(
                input_summary=f"Query: {query[:80]}, Chunks: {len(chunks)}",
                output_summary=f"Extracted {len(perspectives)} perspectives",
                latency_ms=response.latency_ms,
                tokens_used=response.usage.total_tokens,
                prompt_version=self.prompt_loader.load_agent_prompt(
                    "perspective_discovery_agent"
                ).version,
            )

            return perspectives

        except Exception as e:
            self.logger.log_execution(
                input_summary=f"Query: {query[:80]}, Chunks: {len(chunks)}",
                output_summary="Failed",
                latency_ms=(time.monotonic() - start) * 1000,
                error=str(e),
            )
            return []

    def _build_chunk_context(self, chunks: list[tuple[str, str, dict]]) -> str:
        """Format chunks into a readable context string."""
        parts = []
        for i, (chunk_id, content, metadata) in enumerate(chunks):
            source = metadata.get("source_file", "unknown")
            section = metadata.get("section_title", "")
            parts.append(
                f"### Chunk {i + 1} (ID: {chunk_id})\n"
                f"Source: {source}" + (f" / Section: {section}" if section else "") + f"\n"
                f"Content:\n{content}\n"
            )
        return "\n---\n".join(parts)

    def _parse_response(self, response_text: str) -> list[ExtractedPerspective]:
        """Parse LLM response into ExtractedPerspective objects."""
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            self.logger.log_execution(
                input_summary="Parse response",
                output_summary="Failed to parse JSON",
                latency_ms=0,
                error="JSON decode error",
            )
            return []

        perspectives_data = data.get("perspectives", [])
        if not isinstance(perspectives_data, list):
            return []

        results = []
        for p in perspectives_data:
            if not isinstance(p, dict):
                continue

            # Validate required fields
            text = p.get("perspective_text", "").strip()
            if not text:
                continue

            ptype = p.get("perspective_type", "summary")
            if ptype not in ("judgment", "reflection", "lesson", "controversy", "summary"):
                ptype = "summary"

            confidence = float(p.get("confidence", 0.5))
            if confidence < 0.5:
                continue  # Skip low-confidence extractions

            results.append(ExtractedPerspective(
                perspective_text=text,
                perspective_type=ptype,
                source_chunk_ids=p.get("source_chunk_ids", []),
                source_quotes=p.get("source_quotes", []),
                confidence=confidence,
                novelty=float(p.get("novelty", 0.5)),
                engagement_potential=float(p.get("engagement_potential", 0.5)),
                reasoning=p.get("reasoning", ""),
            ))

        return results
