"""PerspectiveDiscoveryAgent node - core perspective extraction."""

import json
import time

from app.agents.state.workflow_state import WorkflowState, PerspectiveData, AgentNode
from app.llm.base import BaseLLMProvider, LLMMessage, MessageRole
from app.services.prompt_loader import PromptLoader
from app.observability.logger import AgentLogAdapter


class PerspectiveDiscoveryNode:
    """Core agent: discovers user perspectives from retrieved knowledge.

    Input: WorkflowState.selected_topic, WorkflowState.retrieval_results
    Output: WorkflowState.perspectives, WorkflowState.selected_perspective
    Next: ANGLE_PLANNER
    """

    def __init__(self, llm: BaseLLMProvider, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.logger = AgentLogAdapter("perspective_discovery")

    async def execute(self, state: WorkflowState) -> WorkflowState:
        start = time.monotonic()

        if not state.selected_topic or not state.retrieval_results:
            state.mark_failed("Missing topic or retrieval results")
            return state

        prompt = self.prompt_loader.get_agent_prompt_content("perspective_discovery_agent")

        chunk_context = "\n---\n".join(
            f"### Chunk {i+1} (ID: {r.chunk_id})\nSource: {r.source_file}\n{r.content}"
            for i, r in enumerate(state.retrieval_results[:8])
        )

        topic_info = f"Title: {state.selected_topic.title}\nSummary: {state.selected_topic.summary}"

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=prompt),
            LLMMessage(
                role=MessageRole.USER,
                content=f"## Hot Topic\n{topic_info}\n\n## Retrieved Knowledge Chunks\n{chunk_context}\n\nExtract genuine user perspectives.",
            ),
        ]

        response = await self.llm.chat(
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        perspectives = self._parse_perspectives(response.content)
        state.perspectives = perspectives

        if perspectives:
            state.selected_perspective = max(perspectives, key=lambda p: p.confidence * p.engagement_potential)

        state.transition_to(AgentNode.PERSPECTIVE_DISCOVERY)

        self.logger.log_execution(
            input_summary=f"Topic: {state.selected_topic.title}, Chunks: {len(state.retrieval_results)}",
            output_summary=f"Discovered {len(perspectives)} perspectives",
            latency_ms=(time.monotonic() - start) * 1000,
            tokens_used=response.usage.total_tokens,
        )

        return state

    def _parse_perspectives(self, response_text: str) -> list[PerspectiveData]:
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            return []

        raw = data.get("perspectives", []) if isinstance(data, dict) else data
        results = []
        for p in raw:
            if not isinstance(p, dict):
                continue
            text = p.get("perspective_text", "").strip()
            if not text:
                continue
            confidence = float(p.get("confidence", 0))
            if confidence < 0.5:
                continue
            results.append(PerspectiveData(
                perspective_text=text,
                perspective_type=p.get("perspective_type", "summary"),
                source_chunk_ids=p.get("source_chunk_ids", []),
                source_quotes=p.get("source_quotes", []),
                confidence=confidence,
                novelty=float(p.get("novelty", 0.5)),
                engagement_potential=float(p.get("engagement_potential", 0.5)),
                reasoning=p.get("reasoning", ""),
            ))
        return results
