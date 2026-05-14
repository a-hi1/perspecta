"""AnglePlannerAgent node - designs content angles and structures."""

import json
import time

from app.agents.state.workflow_state import WorkflowState, AngleData, AgentNode
from app.llm.base import BaseLLMProvider, LLMMessage, MessageRole
from app.services.prompt_loader import PromptLoader
from app.observability.logger import AgentLogAdapter


class AnglePlannerNode:
    """Plans content angles for the selected perspective.

    Input: WorkflowState.selected_perspective, WorkflowState.selected_topic
    Output: WorkflowState.angles, WorkflowState.selected_angle
    Next: DRAFT_GENERATOR
    """

    def __init__(self, llm: BaseLLMProvider, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.logger = AgentLogAdapter("angle_planner")

    async def execute(self, state: WorkflowState) -> WorkflowState:
        start = time.monotonic()

        if not state.selected_perspective or not state.selected_topic:
            state.mark_failed("Missing perspective or topic")
            return state

        prompt = self.prompt_loader.get_agent_prompt_content("angle_planner_agent")

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=prompt),
            LLMMessage(
                role=MessageRole.USER,
                content=f"""## Hot Topic
Title: {state.selected_topic.title}
Summary: {state.selected_topic.summary}

## Discovered Perspective
Type: {state.selected_perspective.perspective_type}
Text: {state.selected_perspective.perspective_text}
Source quotes: {json.dumps(state.selected_perspective.source_quotes, ensure_ascii=False)}

Design three content angles (professional, story, controversial).""",
            ),
        ]

        response = await self.llm.chat(
            messages=messages,
            temperature=0.5,
            response_format={"type": "json_object"},
        )

        angles = self._parse_angles(response.content)
        state.angles = angles

        if angles:
            state.selected_angle = angles[0]

        state.transition_to(AgentNode.ANGLE_PLANNER)

        self.logger.log_execution(
            input_summary=f"Perspective: {state.selected_perspective.perspective_text[:80]}",
            output_summary=f"Designed {len(angles)} angles",
            latency_ms=(time.monotonic() - start) * 1000,
            tokens_used=response.usage.total_tokens,
        )

        return state

    def _parse_angles(self, response_text: str) -> list[AngleData]:
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            return []

        raw = data.get("angles", []) if isinstance(data, dict) else data
        results = []
        for a in raw:
            if not isinstance(a, dict):
                continue
            results.append(AngleData(
                style=a.get("style", "professional"),
                hook=a.get("hook", ""),
                angle_description=a.get("angle_description", ""),
                structure=a.get("structure", []),
                tone_notes=a.get("tone_notes", ""),
                estimated_length=a.get("estimated_length", "medium"),
                engagement_prediction=float(a.get("engagement_prediction", 0.5)),
            ))
        return results
