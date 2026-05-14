"""DraftGeneratorAgent node - generates LinkedIn post drafts."""

import json
import time

from app.agents.state.workflow_state import WorkflowState, DraftData, AgentNode
from app.llm.base import BaseLLMProvider, LLMMessage, MessageRole
from app.services.prompt_loader import PromptLoader
from app.observability.logger import AgentLogAdapter


class DraftGeneratorNode:
    """Generates LinkedIn post drafts based on angle and perspective.

    Input: WorkflowState.selected_angle, WorkflowState.selected_perspective
    Output: WorkflowState.drafts, WorkflowState.selected_draft
    Next: STYLE_ADAPTER
    """

    def __init__(self, llm: BaseLLMProvider, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.logger = AgentLogAdapter("draft_generator")

    async def execute(self, state: WorkflowState) -> WorkflowState:
        start = time.monotonic()

        if not state.selected_angle or not state.selected_perspective:
            state.mark_failed("Missing angle or perspective")
            return state

        prompt = self.prompt_loader.get_agent_prompt_content("draft_generator_agent")

        # Load template based on style
        template_name = f"post_template_{state.selected_angle.style}"
        try:
            template = self.prompt_loader.get_template_content(template_name)
        except FileNotFoundError:
            template = ""

        style_context = ""
        if state.adapted_draft and state.adapted_draft.style_match_score > 0:
            # This is a revision - include previous draft for reference
            style_context = f"\n\nPrevious draft for reference:\n{state.adapted_draft.content}"

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=prompt),
            LLMMessage(
                role=MessageRole.USER,
                content=f"""## Angle Plan
Style: {state.selected_angle.style}
Hook: {state.selected_angle.hook}
Structure: {json.dumps(state.selected_angle.structure, ensure_ascii=False)}
Tone: {state.selected_angle.tone_notes}
Length: {state.selected_angle.estimated_length}

## Source Perspective
{state.selected_perspective.perspective_text}

## Source Quotes
{json.dumps(state.selected_perspective.source_quotes, ensure_ascii=False)}

## Template
{template}
{style_context}

Generate the LinkedIn post draft. Output as JSON.""",
            ),
        ]

        response = await self.llm.chat(
            messages=messages,
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        draft = self._parse_draft(response.content)
        if draft:
            state.drafts.append(draft)
            state.selected_draft = draft

        state.transition_to(AgentNode.DRAFT_GENERATOR)

        self.logger.log_execution(
            input_summary=f"Angle: {state.selected_angle.style}, Perspective: {state.selected_perspective.perspective_text[:60]}",
            output_summary=f"Generated draft: {draft.title if draft else 'none'}",
            latency_ms=(time.monotonic() - start) * 1000,
            tokens_used=response.usage.total_tokens,
        )

        return state

    def _parse_draft(self, response_text: str) -> DraftData | None:
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            return None

        content = data.get("content", "").strip()
        if not content:
            return None

        return DraftData(
            title=data.get("title", "Untitled"),
            content=content,
            draft_type=data.get("draft_type", "professional"),
            hook=data.get("hook", ""),
            cta=data.get("cta", ""),
            structure_notes=data.get("structure_notes", {}),
            citation_markers=data.get("citation_markers", []),
        )
