"""ContentGeneration node - merged angle planning + draft generation + style adaptation.

Combines three previously separate nodes into one, reducing LLM call overhead
and simplifying the pipeline.
"""

import json
import time

from app.agents.state.workflow_state import (
    WorkflowState, AngleData, DraftData, AgentNode,
)
from app.llm.base import BaseLLMProvider, LLMMessage, MessageRole
from app.services.prompt_loader import PromptLoader
from app.observability.logger import AgentLogAdapter


class ContentGenerationNode:
    """Plans angle, generates draft, and adapts style in one node.

    Input: WorkflowState.selected_perspective, WorkflowState.selected_topic
    Output: WorkflowState.selected_angle, WorkflowState.selected_draft,
            WorkflowState.adapted_draft, WorkflowState.style_changes
    Next: CITATION_VERIFICATION
    """

    def __init__(self, llm: BaseLLMProvider, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.logger = AgentLogAdapter("content_generation")

    async def execute(self, state: WorkflowState, style_profile: dict | None = None) -> WorkflowState:
        start = time.monotonic()

        if not state.selected_perspective or not state.selected_topic:
            state.mark_failed("Missing perspective or topic for content generation")
            return state

        # Step 1: Plan angle (generate 1 instead of 3 — we only use the first)
        angle = await self._plan_angle(state)
        state.selected_angle = angle
        state.angles = [angle]

        # Step 2: Generate draft
        draft = await self._generate_draft(state)
        if draft:
            state.drafts.append(draft)
            state.selected_draft = draft

        # Step 3: Adapt style
        if draft:
            adapted = await self._adapt_style(draft, style_profile)
            if adapted:
                state.adapted_draft = adapted
                state.style_changes = adapted.structure_notes.get("changes", [])

        state.transition_to(AgentNode.CITATION_VERIFICATION)

        draft_for_log = state.adapted_draft or state.selected_draft
        self.logger.log_execution(
            input_summary=f"Perspective: {state.selected_perspective.perspective_text[:60]}",
            output_summary=f"Angle: {angle.style}, Draft: {draft_for_log.title if draft_for_log else 'none'}",
            latency_ms=(time.monotonic() - start) * 1000,
        )

        return state

    async def _plan_angle(self, state: WorkflowState) -> AngleData:
        """Plan a single content angle."""
        prompt = self.prompt_loader.get_full_prompt("angle_planner_agent")

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=prompt),
            LLMMessage(
                role=MessageRole.USER,
                content=f"""## 热点话题
标题: {state.selected_topic.title}
摘要: {state.selected_topic.summary}

## 发现的观点
类型: {state.selected_perspective.perspective_type}
内容: {state.selected_perspective.perspective_text}
来源引用: {json.dumps(state.selected_perspective.source_quotes, ensure_ascii=False)}

请设计一个最佳内容角度，用简体中文输出 JSON。""",
            ),
        ]

        response = await self.llm.chat(
            messages=messages,
            temperature=0.5,
            response_format={"type": "json_object"},
        )

        return self._parse_angle(response.content)

    async def _generate_draft(self, state: WorkflowState) -> DraftData | None:
        """Generate a LinkedIn post draft."""
        prompt = self.prompt_loader.get_full_prompt("draft_generator_agent")

        template_name = f"post_template_{state.selected_angle.style}"
        try:
            template = self.prompt_loader.get_template_content(template_name)
        except FileNotFoundError:
            template = ""

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=prompt),
            LLMMessage(
                role=MessageRole.USER,
                content=f"""## 角度计划
风格: {state.selected_angle.style}
开头: {state.selected_angle.hook}
结构: {json.dumps(state.selected_angle.structure, ensure_ascii=False)}
语气: {state.selected_angle.tone_notes}
长度: {state.selected_angle.estimated_length}

## 来源观点
{state.selected_perspective.perspective_text}

## 来源引用
{json.dumps(state.selected_perspective.source_quotes, ensure_ascii=False)}

## 模板
{template}

请用简体中文生成 LinkedIn 帖子草稿。以 JSON 格式输出。""",
            ),
        ]

        response = await self.llm.chat(
            messages=messages,
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        return self._parse_draft(response.content)

    async def _adapt_style(self, draft: DraftData, style_profile: dict | None = None) -> DraftData | None:
        """Adapt draft to user's writing style."""
        prompt = self.prompt_loader.get_full_prompt("style_adapter_agent")

        style_context = "暂无风格画像，请使用专业、清晰的写作风格。"
        if style_profile:
            style_context = json.dumps(style_profile, ensure_ascii=False, indent=2)

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=prompt),
            LLMMessage(
                role=MessageRole.USER,
                content=f"""## 待适配的草稿
{draft.content}

## 用户风格画像
{style_context}

请将草稿适配为用户的写作风格，用简体中文输出 JSON。""",
            ),
        ]

        response = await self.llm.chat(
            messages=messages,
            temperature=0.4,
            response_format={"type": "json_object"},
        )

        return self._parse_adapted(response.content, draft)

    def _parse_angle(self, response_text: str) -> AngleData:
        """Parse LLM response into AngleData."""
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            return AngleData(style="professional", hook="", angle_description="")

        # Handle both single angle and array of angles
        if isinstance(data, list):
            data = data[0] if data else {}
        elif "angles" in data:
            angles = data["angles"]
            data = angles[0] if angles else {}

        return AngleData(
            style=data.get("style", "professional"),
            hook=data.get("hook", ""),
            angle_description=data.get("angle_description", ""),
            structure=data.get("structure", []),
            tone_notes=data.get("tone_notes", ""),
            estimated_length=data.get("estimated_length", "medium"),
            engagement_prediction=float(data.get("engagement_prediction", 0.5)),
        )

    def _parse_draft(self, response_text: str) -> DraftData | None:
        """Parse LLM response into DraftData."""
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

    def _parse_adapted(self, response_text: str, original: DraftData) -> DraftData | None:
        """Parse style adaptation response into DraftData."""
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
