"""Content generation workflow engine.

Uses a simple async state machine instead of LangGraph for MVP simplicity.
Each node is an async function that takes WorkflowState and returns WorkflowState.
The engine handles node sequencing, error recovery, and human-in-the-loop pauses.

Why not LangGraph for MVP:
- LangGraph's TypedDict-based state doesn't play well with dataclass defaults
- Custom engine is simpler to debug and has zero external dependencies
- LangGraph can be added later when checkpointing/branching is needed
"""

import uuid
import time
from datetime import datetime, timezone

from app.agents.state.workflow_state import (
    WorkflowState,
    WorkflowStatus,
    AgentNode,
    VALID_TRANSITIONS,
    EvaluationData,
)
from app.agents.nodes.hot_topic_node import HotTopicNode
from app.agents.nodes.topic_filter_node import TopicFilterNode
from app.agents.nodes.knowledge_retriever_node import KnowledgeRetrieverNode
from app.agents.nodes.perspective_discovery_node import PerspectiveDiscoveryNode
from app.agents.nodes.angle_planner_node import AnglePlannerNode
from app.agents.nodes.draft_generator_node import DraftGeneratorNode
from app.agents.nodes.style_adapter_node import StyleAdapterNode
from app.agents.nodes.citation_verifier_node import CitationVerifierNode
from app.agents.nodes.human_review_node import HumanReviewNode
from app.agents.nodes.export_node import ExportNode

from app.llm.base import BaseLLMProvider
from app.retrieval.retriever import DualLayerRetriever
from app.services.prompt_loader import PromptLoader
from app.evaluation.rag_evaluator import RAGEvaluator
from app.observability.tracer import AgentTracer
from app.observability.logger import AgentLogAdapter, setup_logging


# The pipeline order for automatic execution
PIPELINE: list[AgentNode] = [
    AgentNode.HOT_TOPIC,
    AgentNode.TOPIC_FILTER,
    AgentNode.KNOWLEDGE_RETRIEVER,
    AgentNode.PERSPECTIVE_DISCOVERY,
    AgentNode.ANGLE_PLANNER,
    AgentNode.DRAFT_GENERATOR,
    AgentNode.STYLE_ADAPTER,
    AgentNode.CITATION_VERIFIER,
    AgentNode.HUMAN_REVIEW,
]

# Nodes that follow HUMAN_REVIEW based on approval
POST_REVIEW_PIPELINE: list[AgentNode] = [
    AgentNode.EXPORT,
]


class ContentGenerationWorkflow:
    """Async workflow engine for content generation.

    Usage:
        workflow = ContentGenerationWorkflow(llm, retriever)
        state = await workflow.run(user_id="u1", topic_query="AI agents")
        # state.status == WAITING_APPROVAL
        state = await workflow.approve(state, edited_content="...")
        # state.status == COMPLETED
    """

    def __init__(
        self,
        llm: BaseLLMProvider,
        retriever: DualLayerRetriever,
        prompt_loader: PromptLoader | None = None,
    ):
        self.llm = llm
        self.retriever = retriever
        self.prompt_loader = prompt_loader or PromptLoader()
        self.evaluator = RAGEvaluator(llm)
        self.logger = AgentLogAdapter("workflow")
        self.tracer = AgentTracer("content_generation")

        # Node instances
        self._nodes = {
            AgentNode.HOT_TOPIC: HotTopicNode(llm, self.prompt_loader),
            AgentNode.TOPIC_FILTER: TopicFilterNode(llm, self.prompt_loader),
            AgentNode.KNOWLEDGE_RETRIEVER: KnowledgeRetrieverNode(retriever),
            AgentNode.PERSPECTIVE_DISCOVERY: PerspectiveDiscoveryNode(llm, self.prompt_loader),
            AgentNode.ANGLE_PLANNER: AnglePlannerNode(llm, self.prompt_loader),
            AgentNode.DRAFT_GENERATOR: DraftGeneratorNode(llm, self.prompt_loader),
            AgentNode.STYLE_ADAPTER: StyleAdapterNode(llm, self.prompt_loader),
            AgentNode.CITATION_VERIFIER: CitationVerifierNode(llm, self.prompt_loader),
            AgentNode.HUMAN_REVIEW: HumanReviewNode(),
            AgentNode.EXPORT: ExportNode(),
        }

    async def run(self, user_id: str, topic_query: str = "") -> WorkflowState:
        """Run the pipeline until human review checkpoint."""
        setup_logging()
        self.tracer.start()

        state = WorkflowState(
            workflow_id=str(uuid.uuid4()),
            user_id=user_id,
            status=WorkflowStatus.RUNNING,
            topic_query=topic_query,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            for node_name in PIPELINE:
                state = await self._execute_node(node_name, state)

                # Stop at human review
                if node_name == AgentNode.HUMAN_REVIEW:
                    if state.status == WorkflowStatus.WAITING_APPROVAL:
                        break
                    if state.status == WorkflowStatus.FAILED:
                        break

            # Run evaluation
            await self._run_evaluation(state)

            self.tracer.finish(status="completed", final_state=state.to_dict())
            self.logger.log_execution(
                input_summary=f"用户: {user_id}, 查询: {topic_query}",
                output_summary=f"状态: {state.status.value}",
                latency_ms=self.tracer.trace.total_latency_ms,
                tokens_used=self.tracer.trace.total_tokens,
            )
            return state

        except Exception as e:
            self.tracer.finish_with_error(str(e))
            state.mark_failed(str(e))
            self.logger.log_execution(
                input_summary=f"用户: {user_id}, 查询: {topic_query}",
                output_summary=f"失败: {e}",
                latency_ms=self.tracer.trace.total_latency_ms,
                error=str(e),
            )
            return state

    async def approve(
        self,
        state: WorkflowState,
        edited_content: str | None = None,
    ) -> WorkflowState:
        """Process human approval and run export."""
        state = await HumanReviewNode.process_approval(
            state, approved=True, edited_content=edited_content
        )
        state.status = WorkflowStatus.RUNNING
        state = await self._execute_node(AgentNode.EXPORT, state)
        return state

    async def reject(self, state: WorkflowState, feedback: str) -> WorkflowState:
        """Process human rejection and regenerate draft."""
        state = await HumanReviewNode.process_approval(
            state, approved=False, feedback=feedback
        )
        state.status = WorkflowStatus.RUNNING

        # Re-run from draft generation
        restart_from = [
            AgentNode.DRAFT_GENERATOR,
            AgentNode.STYLE_ADAPTER,
            AgentNode.CITATION_VERIFIER,
            AgentNode.HUMAN_REVIEW,
        ]
        for node_name in restart_from:
            state = await self._execute_node(node_name, state)
            if node_name == AgentNode.HUMAN_REVIEW:
                break

        return state

    async def _execute_node(self, node_name: AgentNode, state: WorkflowState) -> WorkflowState:
        """Execute a single node with tracing and error handling."""
        node = self._nodes[node_name]
        with self.tracer.trace_node(node_name.value) as trace_ctx:
            if hasattr(trace_ctx, 'set_input'):
                trace_ctx.set_input({"workflow_id": state.workflow_id})
                trace_ctx.set_prompt_version(
                    self.prompt_loader.load_agent_prompt(
                        f"{node_name.value}_agent"
                    ).version if node_name in (
                        AgentNode.HOT_TOPIC, AgentNode.TOPIC_FILTER,
                        AgentNode.PERSPECTIVE_DISCOVERY, AgentNode.ANGLE_PLANNER,
                        AgentNode.DRAFT_GENERATOR, AgentNode.STYLE_ADAPTER,
                        AgentNode.CITATION_VERIFIER,
                    ) else ""
                )

            state = await node.execute(state)

            if hasattr(trace_ctx, 'set_output'):
                trace_ctx.set_output({
                    "status": state.status.value,
                    "error": state.error,
                })

        return state

    async def _run_evaluation(self, state: WorkflowState) -> None:
        """Run quality evaluation in development mode."""
        if not state.retrieval_results or not state.perspectives:
            return

        try:
            draft = state.adapted_draft or state.selected_draft
            eval_report = await self.evaluator.full_evaluation(
                query=state.selected_topic.title if state.selected_topic else "",
                retrieved_chunks=[
                    {"chunk_id": r.chunk_id, "content": r.content}
                    for r in state.retrieval_results
                ],
                perspectives=[
                    {"perspective_type": p.perspective_type, "perspective_text": p.perspective_text}
                    for p in state.perspectives
                ],
                generated_text=draft.content if draft else "",
            )
            state.evaluation = EvaluationData(
                retrieval_relevance=eval_report.retrieval_relevance,
                perspective_quality=eval_report.perspective_quality,
                hallucination_score=eval_report.hallucination_score,
                overall_score=eval_report.overall_score,
                recommendations=eval_report.recommendations,
            )
        except Exception as e:
            self.logger.log_execution(
                input_summary="Evaluation",
                output_summary=f"评估失败: {e}",
                latency_ms=0,
                error=str(e),
            )

    def get_state_diagram(self) -> str:
        """Return a Mermaid diagram of the workflow."""
        return """
graph TD
    A[HotTopic] --> B[TopicFilter]
    B --> C[KnowledgeRetriever]
    C --> D[PerspectiveDiscovery]
    D --> E[AnglePlanner]
    E --> F[DraftGenerator]
    F --> G[StyleAdapter]
    G --> H[CitationVerifier]
    H --> I[HumanReview]
    I -->|approved| J[Export]
    I -->|rejected| F
    J --> K([END])

    style A fill:#e1f5fe
    style D fill:#fff3e0
    style I fill:#fce4ec
    style J fill:#e8f5e9
"""
