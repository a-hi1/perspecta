"""Workflow service — business logic for workflow management.

Handles workflow lifecycle with DB persistence for state recovery.
"""

import json
import asyncio
from datetime import datetime, timezone
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.workflow import ContentGenerationWorkflow
from app.agents.state.workflow_state import WorkflowState, WorkflowStatus
from app.models.workflow_run import WorkflowRun
from app.llm.factory import get_llm_provider
from app.retrieval.retriever import DualLayerRetriever
from app.db.session import async_session_factory


def _serialize_state(state: WorkflowState) -> str:
    """Serialize WorkflowState to JSON string."""
    return json.dumps(asdict(state), ensure_ascii=False, default=str)


def _deserialize_state(data: str) -> dict:
    """Deserialize JSON string to dict."""
    return json.loads(data)


class WorkflowService:
    """Manages workflow lifecycle with DB persistence."""

    def __init__(self) -> None:
        self._states: dict[str, WorkflowState] = {}

    async def create_workflow(self, topic_query: str = "") -> WorkflowState:
        """Create a new workflow in PENDING state and persist to DB."""
        import uuid
        state = WorkflowState(
            workflow_id=str(uuid.uuid4()),
            user_id="default_user",
            status=WorkflowStatus.PENDING,
            topic_query=topic_query,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._states[state.workflow_id] = state

        # Persist to DB
        async with async_session_factory() as session:
            run = WorkflowRun(
                id=state.workflow_id,
                user_id=state.user_id,
                status=state.status.value,
                topic_query=topic_query,
                state_json=_serialize_state(state),
            )
            session.add(run)
            await session.commit()

        return state

    def start_workflow(self, state: WorkflowState) -> None:
        """Start workflow execution in background."""
        workflow = self._build_workflow()
        asyncio.create_task(self._run_background(workflow, state))

    async def get_state(self, workflow_id: str) -> WorkflowState | None:
        """Get workflow state by ID. Checks in-memory first, then DB."""
        state = self._states.get(workflow_id)
        if state:
            return state

        # Fallback: load from DB
        async with async_session_factory() as session:
            result = await session.execute(
                select(WorkflowRun).where(WorkflowRun.id == workflow_id)
            )
            run = result.scalar_one_or_none()
            if not run:
                return None

            state_dict = _deserialize_state(run.state_json)
            # Reconstruct WorkflowState from dict
            state = self._dict_to_state(state_dict)
            self._states[workflow_id] = state
            return state

    async def approve(
        self,
        workflow_id: str,
        edited_content: str | None = None,
    ) -> WorkflowState:
        """Approve a workflow draft."""
        state = self._states.get(workflow_id)
        if not state:
            raise ValueError("工作流未找到")
        if state.status != WorkflowStatus.WAITING_APPROVAL:
            raise ValueError(f"工作流不在等待审核状态。当前状态: {state.status.value}")

        workflow = self._build_workflow()
        state = await workflow.approve(state, edited_content=edited_content)
        self._states[workflow_id] = state

        await self._persist_state(state)
        return state

    async def reject(self, workflow_id: str, feedback: str) -> WorkflowState:
        """Reject a workflow draft with feedback."""
        state = self._states.get(workflow_id)
        if not state:
            raise ValueError("工作流未找到")
        if state.status != WorkflowStatus.WAITING_APPROVAL:
            raise ValueError(f"工作流不在等待审核状态。当前状态: {state.status.value}")

        workflow = self._build_workflow()
        state = await workflow.reject(state, feedback=feedback)
        self._states[workflow_id] = state

        await self._persist_state(state)
        return state

    @staticmethod
    def _build_workflow() -> ContentGenerationWorkflow:
        """Create a workflow instance with all dependencies."""
        llm = get_llm_provider()
        retriever = DualLayerRetriever(llm)
        return ContentGenerationWorkflow(llm, retriever)

    async def _run_background(
        self,
        workflow: ContentGenerationWorkflow,
        state: WorkflowState,
    ) -> None:
        """Run workflow in background. Persists state on completion."""
        try:
            await workflow.run(
                user_id=state.user_id,
                topic_query=state.topic_query,
                initial_state=state,
            )
        except Exception as e:
            state.mark_failed(str(e))

        await self._persist_state(state)

    @staticmethod
    async def _persist_state(state: WorkflowState) -> None:
        """Serialize and persist workflow state to DB."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(WorkflowRun).where(WorkflowRun.id == state.workflow_id)
            )
            run = result.scalar_one_or_none()
            if run:
                run.status = state.status.value
                run.current_node = state.current_node.value if state.current_node else None
                run.state_json = _serialize_state(state)
                run.updated_at = datetime.now(timezone.utc)
                await session.commit()

    @staticmethod
    def _dict_to_state(data: dict) -> WorkflowState:
        """Reconstruct WorkflowState from a serialized dict."""
        from app.agents.state.workflow_state import (
            HotTopicData, PerspectiveData, AngleData, DraftData,
            CitationData, RetrievalData, EvaluationData, AgentNode,
        )

        # Reconstruct nested dataclasses
        hot_topics = [HotTopicData(**t) for t in data.get("hot_topics", [])]
        perspectives = [PerspectiveData(**p) for p in data.get("perspectives", [])]
        angles = [AngleData(**a) for a in data.get("angles", [])]
        drafts = [DraftData(**d) for d in data.get("drafts", [])]
        citations = [CitationData(**c) for c in data.get("citations", [])]
        retrieval_results = [RetrievalData(**r) for r in data.get("retrieval_results", [])]

        selected_topic = HotTopicData(**data["selected_topic"]) if data.get("selected_topic") else None
        selected_perspective = PerspectiveData(**data["selected_perspective"]) if data.get("selected_perspective") else None
        selected_angle = AngleData(**data["selected_angle"]) if data.get("selected_angle") else None
        selected_draft = DraftData(**data["selected_draft"]) if data.get("selected_draft") else None
        adapted_draft = DraftData(**data["adapted_draft"]) if data.get("adapted_draft") else None
        evaluation = EvaluationData(**data["evaluation"]) if data.get("evaluation") else None

        current_node = AgentNode(data["current_node"]) if data.get("current_node") else None

        return WorkflowState(
            workflow_id=data.get("workflow_id", ""),
            user_id=data.get("user_id", ""),
            status=WorkflowStatus(data.get("status", "pending")),
            current_node=current_node,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            topic_query=data.get("topic_query", ""),
            hot_topics=hot_topics,
            selected_topic=selected_topic,
            retrieval_results=retrieval_results,
            perspectives=perspectives,
            selected_perspective=selected_perspective,
            angles=angles,
            selected_angle=selected_angle,
            drafts=drafts,
            selected_draft=selected_draft,
            adapted_draft=adapted_draft,
            style_changes=data.get("style_changes", []),
            citations=citations,
            verification_score=data.get("verification_score", 0.0),
            hallucination_flags=data.get("hallucination_flags", []),
            human_approved=data.get("human_approved", False),
            human_feedback=data.get("human_feedback", ""),
            revision_count=data.get("revision_count", 0),
            exported_content=data.get("exported_content", ""),
            export_format=data.get("export_format", "linkedin"),
            evaluation=evaluation,
            error=data.get("error"),
        )
