"""KnowledgeRetriever node - dual-layer RAG retrieval."""

import time

from app.agents.state.workflow_state import WorkflowState, RetrievalData, AgentNode
from app.retrieval.retriever import DualLayerRetriever
from app.observability.logger import AgentLogAdapter


class KnowledgeRetrieverNode:
    """Retrieves relevant knowledge from user's knowledge base.

    Input: WorkflowState.selected_topic
    Output: WorkflowState.retrieval_results
    Next: PERSPECTIVE_DISCOVERY
    """

    def __init__(self, retriever: DualLayerRetriever):
        self.retriever = retriever
        self.logger = AgentLogAdapter("knowledge_retriever")

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

        state.transition_to(AgentNode.KNOWLEDGE_RETRIEVER)

        self.logger.log_execution(
            input_summary=f"Topic: {topic.title}",
            output_summary=f"Retrieved {len(state.retrieval_results)} chunks",
            latency_ms=(time.monotonic() - start) * 1000,
        )

        return state
