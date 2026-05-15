"""HotTopicAgent node - discovers trending topics from external sources."""

import json
import time
from contextlib import contextmanager

from app.agents.state.workflow_state import (
    WorkflowState, HotTopicData, AgentNode,
)
from app.llm.base import BaseLLMProvider, LLMMessage, MessageRole
from app.services.prompt_loader import PromptLoader
from app.observability.logger import AgentLogAdapter
from app.observability.tracer import AgentTracer


class HotTopicNode:
    """Discovers hot topics from external sources.

    Input: WorkflowState with topic_query or auto-discovery
    Output: WorkflowState.hot_topics populated
    Next: TOPIC_FILTER
    """

    def __init__(self, llm: BaseLLMProvider, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.logger = AgentLogAdapter("hot_topic")

    async def execute(
        self, state: WorkflowState, tracer: AgentTracer | None = None
    ) -> WorkflowState:
        """Execute hot topic discovery."""
        start = time.monotonic()

        # Load prompt
        prompt = self.prompt_loader.get_agent_prompt_content("hot_topic_agent")

        # For MVP, use LLM to simulate topic discovery
        source_content = await self._fetch_source_content(state.topic_query)

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=prompt),
            LLMMessage(
                role=MessageRole.USER,
                content=f"Extract and score hot topics from this content:\n\n{source_content}",
            ),
        ]

        response = await self.llm.chat(
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        topics = self._parse_topics(response.content)
        state.hot_topics = topics
        state.transition_to(AgentNode.HOT_TOPIC)

        latency_ms = (time.monotonic() - start) * 1000
        self.logger.log_execution(
            input_summary=f"Query: {state.topic_query[:100]}",
            output_summary=f"Found {len(topics)} hot topics",
            latency_ms=latency_ms,
            tokens_used=response.usage.total_tokens,
            prompt_version=self.prompt_loader.load_agent_prompt("hot_topic_agent").version,
        )

        return state

    async def _fetch_source_content(self, query: str) -> str:
        """Fetch content from external sources.

        MVP: Returns simulated content.
        Production: Calls Reddit API, HN API, Arxiv API.
        """
        return f"""
        与以下话题相关的近期技术讨论: {query or "软件工程"}

        [Hacker News]
        - "为什么我们从微服务回到了单体架构"
        - "反对 AI 辅助编程的理由"
        - "我们用 SQLite 支撑 100 万用户的经历"

        [Reddit r/programming]
        - "不受欢迎的观点：TDD 对创业公司来说被高估了"
        - "用了 10 年 React 之后，我今天会选择什么"
        - "我们用这个方法把 AWS 账单降低了 80%"

        [Arxiv]
        - "重新思考 RAG：为什么仅靠检索是不够的"
        - "更大语言模型的边际收益递减"
        """

    def _parse_topics(self, response_text: str) -> list[HotTopicData]:
        """Parse LLM response into HotTopicData objects."""
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            return []

        topics_raw = data if isinstance(data, list) else data.get("topics", [])
        topics = []
        for t in topics_raw:
            if not isinstance(t, dict):
                continue
            topics.append(HotTopicData(
                title=t.get("title", ""),
                summary=t.get("summary", ""),
                source=t.get("source", "unknown"),
                source_url=t.get("source_url", ""),
                relevance_score=float(t.get("relevance_score", 0)),
                engagement_score=float(t.get("engagement_score", 0)),
                freshness_score=float(t.get("freshness_score", 0)),
                composite_score=float(t.get("composite_score", 0)),
                tags=t.get("tags", []),
                category=t.get("category", ""),
            ))
        return topics
