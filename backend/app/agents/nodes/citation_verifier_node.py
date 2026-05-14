"""CitationVerifier node - verifies all citations are accurate."""

import json
import time

from app.agents.state.workflow_state import WorkflowState, CitationData, AgentNode
from app.llm.base import BaseLLMProvider, LLMMessage, MessageRole
from app.services.prompt_loader import PromptLoader
from app.observability.logger import AgentLogAdapter


class CitationVerifierNode:
    """Verifies that all claims in the draft are traceable to sources.

    Input: WorkflowState.adapted_draft or selected_draft, WorkflowState.retrieval_results
    Output: WorkflowState.citations, WorkflowState.verification_score, WorkflowState.hallucination_flags
    Next: HUMAN_REVIEW
    """

    def __init__(self, llm: BaseLLMProvider, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.logger = AgentLogAdapter("citation_verifier")

    async def execute(self, state: WorkflowState) -> WorkflowState:
        start = time.monotonic()

        draft = state.adapted_draft or state.selected_draft
        if not draft:
            state.mark_failed("No draft to verify")
            return state

        prompt = self.prompt_loader.get_agent_prompt_content("citation_verifier")

        source_chunks = "\n---\n".join(
            f"### Chunk {i+1} (ID: {r.chunk_id})\nSource: {r.source_file}\n{r.content}"
            for i, r in enumerate(state.retrieval_results[:8])
        )

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=prompt),
            LLMMessage(
                role=MessageRole.USER,
                content=f"""## Draft to Verify
{draft.content}

## Source Material
{source_chunks}

Verify all claims and citations. Output as JSON.""",
            ),
        ]

        response = await self.llm.chat(
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        result = self._parse_verification(response.content)
        state.citations = result["citations"]
        state.verification_score = result["verification_score"]
        state.hallucination_flags = result["hallucination_flags"]

        state.transition_to(AgentNode.CITATION_VERIFIER)

        self.logger.log_execution(
            input_summary=f"Draft: {draft.title}",
            output_summary=f"Score: {state.verification_score:.2f}, Citations: {len(state.citations)}, Hallucinations: {len(state.hallucination_flags)}",
            latency_ms=(time.monotonic() - start) * 1000,
            tokens_used=response.usage.total_tokens,
        )

        return state

    def _parse_verification(self, response_text: str) -> dict:
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            return {"citations": [], "verification_score": 0.0, "hallucination_flags": []}

        citations = []
        for c in data.get("citations", []):
            citations.append(CitationData(
                cited_text=c.get("cited_text", ""),
                source_quote=c.get("source_quote", ""),
                source_file=c.get("source_file", ""),
                source_section=c.get("source_section", ""),
                status=c.get("status", "pending"),
                verification_score=float(c.get("verification_score", 0)),
            ))

        return {
            "citations": citations,
            "verification_score": float(data.get("verification_score", 0)),
            "hallucination_flags": data.get("hallucination_flags", []),
        }
