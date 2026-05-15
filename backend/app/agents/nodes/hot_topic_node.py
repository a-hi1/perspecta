"""HotTopic node - discovers trending topics from real sources."""

import json
import time
import httpx

from app.agents.state.workflow_state import (
    WorkflowState, HotTopicData, AgentNode,
)
from app.llm.base import BaseLLMProvider, LLMMessage, MessageRole
from app.services.prompt_loader import PromptLoader
from app.observability.logger import AgentLogAdapter
from app.observability.tracer import AgentTracer

# Fallback topics when API is unavailable
_FALLBACK_TOPICS = [
    "AI agent frameworks and autonomous coding",
    "RAG vs fine-tuning for domain-specific LLMs",
    "SQLite at scale: lessons from production",
    "The return of monoliths after microservices fatigue",
    "LLM cost optimization strategies",
]


class HotTopicNode:
    """Discovers hot topics from real external sources.

    Input: WorkflowState with topic_query or auto-discovery
    Output: WorkflowState.hot_topics populated
    Next: TOPIC_SELECTION
    """

    def __init__(self, llm: BaseLLMProvider, prompt_loader: PromptLoader):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.logger = AgentLogAdapter("hot_topic")

    async def execute(
        self, state: WorkflowState, tracer: AgentTracer | None = None
    ) -> WorkflowState:
        start = time.monotonic()

        prompt = self.prompt_loader.get_full_prompt("hot_topic_agent")

        # Fetch real trending stories from Hacker News
        source_content = await self._fetch_source_content(state.topic_query)

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=prompt),
            LLMMessage(
                role=MessageRole.USER,
                content=f"从以下内容中提取并评分热点话题，用简体中文输出：\n\n{source_content}",
            ),
        ]

        response = await self.llm.chat(
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        topics = self._parse_topics(response.content)
        state.hot_topics = topics
        state.transition_to(AgentNode.TOPIC_SELECTION)

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
        """Fetch real trending stories from Hacker News API."""
        stories = []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get top story IDs
                resp = await client.get(
                    "https://hacker-news.firebaseio.com/v0/topstories.json"
                )
                resp.raise_for_status()
                story_ids = resp.json()[:15]  # Top 15 stories

                # Fetch story details concurrently
                tasks = [
                    client.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
                    for sid in story_ids
                ]
                import asyncio
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, Exception):
                        continue
                    if result.status_code == 200:
                        item = result.json()
                        if item and item.get("title"):
                            stories.append({
                                "title": item["title"],
                                "url": item.get("url", ""),
                                "score": item.get("score", 0),
                                "comments": item.get("descendants", 0),
                                "source": "Hacker News",
                            })

        except Exception as e:
            self.logger.log_execution(
                input_summary="Fetch HN stories",
                output_summary=f"API failed: {e}",
                latency_ms=0,
                error=str(e),
            )

        if not stories:
            # Fallback to curated topics
            topics_text = "\n".join(
                f"- {topic}" for topic in _FALLBACK_TOPICS
            )
            if query:
                return f"用户关注的话题: {query}\n\n近期技术热点:\n{topics_text}"
            return f"近期技术热点:\n{topics_text}"

        # Format real stories for LLM
        stories_text = "\n".join(
            f"- [{s['source']}] {s['title']} (热度: {s['score']}, 评论: {s['comments']})"
            for s in stories
        )

        context = f"[Hacker News 热门]\n{stories_text}"
        if query:
            context = f"用户关注的话题: {query}\n\n{context}"

        return context

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
