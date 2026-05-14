"""StyleAdapterAgent node - adapts draft to user's writing style."""

import json
import time

from app.agents.state.workflow_state import WorkflowState, DraftData, AgentNode
from app.llm.base import BaseLLMProvider, LLMMessage, MessageRole
from app.services.prompt_loader import PromptLoader
from app.observability.logger import AgentLogAdapter


class StyleAdapterNode:
    """Adapts draft content to match user's writing style.

    Input: WorkflowState.selected_draft, user's StyleProfile
    Output: WorkflowState.adapted_draft, WorkflowState.style_changes
    Next: CITATION_VERIFIER
    """

    def __init__(self, llm: BaseLLMProvider, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.logger = AgentLogAdapter("style_adapter")

    async def execute(self, state: WorkflowState, style_profile: dict | None = None) -> WorkflowState:
        start = time.monotonic()

        if not state.selected_draft:
            state.mark_failed("No draft to adapt")
            return state

        prompt = self.prompt_loader.get_agent_prompt_content("style_adapter_agent")

        style_context = "No style profile available. Use a professional, clear writing style."
        if style_profile:
            style_context = json.dumps(style_profile, ensure_ascii=False, indent=2)

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=prompt),
            LLMMessage(
                role=MessageRole.USER,
                content=f"""## Draft to Adapt
{state.selected_draft.content}

## User Style Profile
{style_context}

Adapt the draft to match the user's style. Output as JSON.""",
            ),
        ]

        response = await self.llm.chat(
            messages=messages,
            temperature=0.4,
            response_format={"type": "json_object"},
        )

        adapted = self._parse_adapted(response.content, state.selected_draft)
        if adapted:
            state.adapted_draft = adapted
            state.style_changes = adapted.structure_notes.get("changes", [])

        state.transition_to(AgentNode.STYLE_ADAPTER)

        self.logger.log_execution(
            input_summary=f"Draft: {state.selected_draft.title}",
            output_summary=f"Style match: {adapted.style_match_score:.2f}" if adapted else "Failed",
            latency_ms=(time.monotonic() - start) * 1000,
            tokens_used=response.usage.total_tokens,
        )

        return state

    def _parse_adapted(self, response_text: str, original: DraftData) -> DraftData | None:
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            return None

        content = data.get("adapted_content", "").strip()
        if not content:
            return None

        return DraftData(
            id=original.id,
            title=original.title,
            content=content,
            draft_type=original.draft_type,
            hook=original.hook,
            cta=original.cta,
            structure_notes={"changes": data.get("changes_made", [])},
            citation_markers=original.citation_markers,
            style_match_score=float(data.get("style_match_score", 0.5)),
        )
