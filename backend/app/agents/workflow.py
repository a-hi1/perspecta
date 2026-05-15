"""Content generation workflow engine.

6-node pipeline: HotTopic → TopicSelection → RetrievalAndPerspective
→ ContentGeneration → CitationVerification → HumanReview

Uses a simple async state machine. Each node is an async class with
execute(state) -> state. The engine handles sequencing, error recovery,
and human-in-the-loop pauses.
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
from app.agents.nodes.retrieval_and_perspective import RetrievalAndPerspectiveNode
from app.agents.nodes.content_generation import ContentGenerationNode
from app.agents.nodes.citation_verifier_node import CitationVerifierNode
from app.agents.nodes.human_review_node import HumanReviewNode

from app.llm.base import BaseLLMProvider
from app.retrieval.retriever import DualLayerRetriever
from app.services.prompt_loader import PromptLoader
from app.evaluation.rag_evaluator import RAGEvaluator
from app.observability.tracer import AgentTracer
from app.observability.logger import AgentLogAdapter, setup_logging, _current_trace_id


# 6-node pipeline
PIPELINE: list[AgentNode] = [
    AgentNode.HOT_TOPIC,
    AgentNode.TOPIC_SELECTION,
    AgentNode.RETRIEVAL_AND_PERSPECTIVE,
    AgentNode.CONTENT_GENERATION,
    AgentNode.CITATION_VERIFICATION,
    AgentNode.HUMAN_REVIEW,
]

# Critical nodes that terminate the pipeline on failure
_CRITICAL_NODES = {AgentNode.HUMAN_REVIEW}


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

        # 6 node instances
        self._nodes = {
            AgentNode.HOT_TOPIC: HotTopicNode(llm, self.prompt_loader),
            AgentNode.TOPIC_SELECTION: TopicFilterNode(llm, self.prompt_loader),
            AgentNode.RETRIEVAL_AND_PERSPECTIVE: RetrievalAndPerspectiveNode(retriever),
            AgentNode.CONTENT_GENERATION: ContentGenerationNode(llm, self.prompt_loader),
            AgentNode.CITATION_VERIFICATION: CitationVerifierNode(llm, self.prompt_loader),
            AgentNode.HUMAN_REVIEW: HumanReviewNode(),
        }

    async def run(
        self,
        user_id: str,
        topic_query: str = "",
        initial_state: WorkflowState | None = None,
    ) -> WorkflowState:
        """Run the pipeline until human review checkpoint."""
        setup_logging()
        self.tracer.start()

        # Set trace_id for structured logging
        workflow_id = initial_state.workflow_id if initial_state else ""
        if not workflow_id:
            import uuid as _uuid
            workflow_id = str(_uuid.uuid4())
        _current_trace_id.set(workflow_id)

        if initial_state:
            state = initial_state
            state.mark_running()
        else:
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
                try:
                    state = await self._execute_node(node_name, state)
                except Exception as node_err:
                    self.logger.log_execution(
                        input_summary=f"Node {node_name.value}",
                        output_summary=f"Failed: {node_err}",
                        latency_ms=0,
                        error=str(node_err),
                    )
                    state.error = f"Node {node_name.value} failed: {node_err}"
                    state.current_node = node_name
                    state.updated_at = datetime.now(timezone.utc).isoformat()

                    if node_name in _CRITICAL_NODES:
                        state.mark_failed(str(node_err))
                        break
                    continue

                # Stop at human review
                if node_name == AgentNode.HUMAN_REVIEW:
                    if state.status in (WorkflowStatus.WAITING_APPROVAL, WorkflowStatus.FAILED):
                        break

            # Run evaluation (non-blocking, sets warnings)
            try:
                await self._run_evaluation(state)
            except Exception:
                pass

            self.tracer.finish(status="completed", final_state=state.to_dict())
            self.logger.log_execution(
                input_summary=f"User: {user_id}, Query: {topic_query}",
                output_summary=f"Status: {state.status.value}",
                latency_ms=self.tracer.trace.total_latency_ms,
                tokens_used=self.tracer.trace.total_tokens,
            )
            return state

        except Exception as e:
            self.tracer.finish_with_error(str(e))
            state.mark_failed(str(e))
            self.logger.log_execution(
                input_summary=f"User: {user_id}, Query: {topic_query}",
                output_summary=f"Failed: {e}",
                latency_ms=self.tracer.trace.total_latency_ms,
                error=str(e),
            )
            return state

    async def approve(
        self,
        state: WorkflowState,
        edited_content: str | None = None,
    ) -> WorkflowState:
        """Process human approval and export (inline, no ExportNode)."""
        state = await HumanReviewNode.process_approval(
            state, approved=True, edited_content=edited_content
        )

        # Inline export logic (was ExportNode)
        draft = state.adapted_draft or state.selected_draft
        if draft:
            state.exported_content = self._format_for_linkedin(draft.content)
        state.mark_completed()

        return state

    async def reject(self, state: WorkflowState, feedback: str) -> WorkflowState:
        """Process human rejection and regenerate from CONTENT_GENERATION."""
        state = await HumanReviewNode.process_approval(
            state, approved=False, feedback=feedback
        )
        state.mark_running()

        # Re-run from content generation
        restart_from = [
            AgentNode.CONTENT_GENERATION,
            AgentNode.CITATION_VERIFICATION,
            AgentNode.HUMAN_REVIEW,
        ]
        for node_name in restart_from:
            state = await self._execute_node(node_name, state)
            if node_name == AgentNode.HUMAN_REVIEW:
                break

        return state

    async def _execute_node(self, node_name: AgentNode, state: WorkflowState) -> WorkflowState:
        """Execute a single node with tracing."""
        node = self._nodes[node_name]
        with self.tracer.trace_node(node_name.value) as trace_ctx:
            if hasattr(trace_ctx, 'set_input'):
                trace_ctx.set_input({"workflow_id": state.workflow_id})
                prompt_name = f"{node_name.value}_agent"
                try:
                    trace_ctx.set_prompt_version(
                        self.prompt_loader.load_agent_prompt(prompt_name).version
                    )
                except FileNotFoundError:
                    trace_ctx.set_prompt_version("")

            state = await node.execute(state)
            state.updated_at = datetime.now(timezone.utc).isoformat()

            if hasattr(trace_ctx, 'set_output'):
                trace_ctx.set_output({
                    "status": state.status.value,
                    "error": state.error,
                })

        return state

    async def _run_evaluation(self, state: WorkflowState) -> None:
        """Run quality evaluation. Sets warnings that may affect review."""
        if not state.retrieval_results or not state.perspectives:
            return

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

        # Evaluation affects workflow: high hallucination blocks review
        if eval_report.hallucination_score > 0.7:
            state.error = f"高幻觉风险 ({eval_report.hallucination_score:.2f}): {', '.join(eval_report.recommendations)}"
            state.mark_failed(state.error)

    @staticmethod
    def _format_for_linkedin(content: str) -> str:
        """Format content for LinkedIn posting."""
        lines = content.strip().split("\n")
        formatted_lines = []
        for line in lines:
            line = line.strip()
            if line:
                formatted_lines.append(line)
            else:
                formatted_lines.append("")
        return "\n\n".join(formatted_lines)

    def get_state_diagram(self) -> str:
        """Return a Mermaid diagram of the 6-node workflow."""
        return """
graph TD
    A[HotTopic] --> B[TopicSelection]
    B --> C[RetrievalAndPerspective]
    C --> D[ContentGeneration]
    D --> E[CitationVerification]
    E --> F[HumanReview]
    F -->|approved| G([END])
    F -->|rejected| D

    style A fill:#e1f5fe
    style C fill:#fff3e0
    style F fill:#fce4ec
    style G fill:#e8f5e9
"""
