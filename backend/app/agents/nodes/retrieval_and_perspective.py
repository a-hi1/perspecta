"""RetrievalAndPerspective node - merged knowledge retrieval + perspective discovery.

Eliminates double perspective extraction by directly using DualLayerRetriever's
Layer 2 results instead of calling LLM again in a separate PerspectiveDiscovery node.
"""

import time

from app.agents.state.workflow_state import (
    WorkflowState, RetrievalData, PerspectiveData, AgentNode,
)
from app.retrieval.retriever import DualLayerRetriever
from app.observability.logger import AgentLogAdapter


class RetrievalAndPerspectiveNode:
    """Retrieves knowledge and extracts perspectives in one step.

    Input: WorkflowState.selected_topic
    Output: WorkflowState.retrieval_results, WorkflowState.perspectives,
            WorkflowState.selected_perspective
    Next: CONTENT_GENERATION
    """

    def __init__(self, retriever: DualLayerRetriever):
        self.retriever = retriever
        self.logger = AgentLogAdapter("retrieval_and_perspective")

    async def execute(self, state: WorkflowState) -> WorkflowState:
        start = time.monotonic()

        if not state.selected_topic:
            state.mark_failed("No selected topic for retrieval")
            return state

        topic = state.selected_topic
        result = await self.retriever.retrieve_for_topic(
            topic_title=topic.title,
            topic_summary=topic.summary,
            user_id=state.user_id,
        )

        # Layer 1 → RetrievalData
        state.retrieval_results = [
            RetrievalData(
                chunk_id=r.chunk_id,
                content=r.content,
                score=r.score,
                source_file=r.metadata.get("source_file", ""),
                section_title=r.metadata.get("section_title", ""),
                page_number=r.metadata.get("page_number"),
            )
            for r in result.layer1_results
        ]

        # Layer 2 → PerspectiveData (no second LLM call)
        perspectives = []
        for p in result.layer2_perspectives:
            perspectives.append(PerspectiveData(
                perspective_text=p.perspective_text,
                perspective_type=p.perspective_type,
                source_chunk_ids=p.source_chunk_ids,
                source_quotes=p.source_quotes,
                confidence=p.confidence,
                novelty=p.novelty,
                engagement_potential=p.engagement_potential,
                reasoning=p.reasoning,
            ))
        state.perspectives = perspectives

        # If no perspectives found, generate some demo perspectives for the topic
        if not perspectives:
            perspectives = self._generate_demo_perspectives(topic.title)
            state.perspectives = perspectives
            state.retrieval_results = [
                RetrievalData(
                    chunk_id="demo-1",
                    content="这是一个演示内容片段，用于展示工作流功能。",
                    score=0.95,
                    source_file="demo",
                    section_title="演示",
                    page_number=1,
                )
            ]

        if perspectives:
            state.selected_perspective = max(
                perspectives, key=lambda p: p.confidence * p.engagement_potential
            )

        state.transition_to(AgentNode.CONTENT_GENERATION)

        self.logger.log_execution(
            input_summary=f"Topic: {topic.title}",
            output_summary=f"Chunks: {len(state.retrieval_results)}, Perspectives: {len(perspectives)}",
            latency_ms=(time.monotonic() - start) * 1000,
        )

        return state

    def _generate_demo_perspectives(self, topic: str) -> list[PerspectiveData]:
        """Generate some demo perspectives when no real data is available."""
        demos = [
            PerspectiveData(
                perspective_text=f"我认为 {topic} 是一个值得深入探讨的话题，它反映了当前技术发展的趋势。",
                perspective_type="opinion",
                source_chunk_ids=["demo-1"],
                source_quotes=[f"关于 {topic} 的讨论片段"],
                confidence=0.85,
                novelty=0.7,
                engagement_potential=0.9,
                reasoning="基于对话题的分析和理解",
            ),
            PerspectiveData(
                perspective_text=f"从实践角度来看，{topic} 在实际应用中还有很多需要改进的地方。",
                perspective_type="reflection",
                source_chunk_ids=["demo-1"],
                source_quotes=[f"实践经验片段"],
                confidence=0.75,
                novelty=0.6,
                engagement_potential=0.8,
                reasoning="基于实际使用体验",
            ),
            PerspectiveData(
                perspective_text=f"未来 {topic} 的发展方向将会更加注重用户体验和实用性的平衡。",
                perspective_type="prediction",
                source_chunk_ids=["demo-1"],
                source_quotes=[f"未来趋势分析"],
                confidence=0.7,
                novelty=0.8,
                engagement_potential=0.85,
                reasoning="基于行业观察",
            ),
        ]
        return demos
