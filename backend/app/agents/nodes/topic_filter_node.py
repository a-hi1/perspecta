"""TopicFilterAgent node - filters topics by user relevance."""

import json
import time

from app.agents.state.workflow_state import WorkflowState, AgentNode
from app.llm.base import BaseLLMProvider, LLMMessage, MessageRole
from app.services.prompt_loader import PromptLoader
from app.observability.logger import AgentLogAdapter


class TopicFilterNode:
    """Filters hot topics based on user's knowledge base relevance.

    Input: WorkflowState.hot_topics
    Output: WorkflowState.selected_topic
    Next: KNOWLEDGE_RETRIEVER
    """

    def __init__(self, llm: BaseLLMProvider, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.logger = AgentLogAdapter("topic_filter")

    async def execute(self, state: WorkflowState) -> WorkflowState:
        start = time.monotonic()

        if not state.hot_topics:
            state.error = "No hot topics to filter"
            state.mark_failed("No hot topics provided")
            return state

        prompt = self.prompt_loader.get_agent_prompt_content("topic_filter_agent")

        topics_text = json.dumps(
            [{"title": t.title, "summary": t.summary, "source": t.source} for t in state.hot_topics],
            ensure_ascii=False,
        )

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=prompt),
            LLMMessage(
                role=MessageRole.USER,
                content=f"Topics to filter:\n{topics_text}\n\nSelect the best topic for content creation.",
            ),
        ]

        response = await self.llm.chat(
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        selected = self._parse_selection(response.content, state.hot_topics)
        if selected:
            state.selected_topic = selected
        elif state.hot_topics:
            state.selected_topic = state.hot_topics[0]

        state.transition_to(AgentNode.TOPIC_FILTER)

        self.logger.log_execution(
            input_summary=f"Filtering {len(state.hot_topics)} topics",
            output_summary=f"Selected: {state.selected_topic.title if state.selected_topic else 'none'}",
            latency_ms=(time.monotonic() - start) * 1000,
            tokens_used=response.usage.total_tokens,
        )

        return state

    def _parse_selection(self, response_text: str, topics):
        try:
            data = json.loads(response_text)
            selected = data.get("selected_topics", [{}])[0] if isinstance(data, dict) else data[0]
            topic_title = selected.get("topic_id", "") or selected.get("title", "")

            for t in topics:
                if t.title == topic_title or t.title in topic_title:
                    return t
            return None
        except (json.JSONDecodeError, IndexError, KeyError):
            return None
