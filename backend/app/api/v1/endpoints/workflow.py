"""Agent workflow endpoints."""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from app.schemas.workflow import (
    WorkflowStartRequest,
    WorkflowStateResponse,
    WorkflowApprovalRequest,
    WorkflowRejectionRequest,
)
from app.services.workflow_service import WorkflowService
from app.models.workflow_run import WorkflowRun
from app.db.session import async_session_factory

router = APIRouter()

# Shared service instance (in-memory state store for MVP)
_workflow_service = WorkflowService()


def _state_to_response(state) -> WorkflowStateResponse:
    """Convert internal state to API response."""
    draft = state.adapted_draft or state.selected_draft

    return WorkflowStateResponse(
        workflow_id=state.workflow_id,
        user_id=state.user_id,
        status=state.status.value,
        current_node=state.current_node.value if state.current_node else None,
        hot_topics=[asdict(t) for t in state.hot_topics],
        selected_topic=asdict(state.selected_topic) if state.selected_topic else None,
        retrieval_count=len(state.retrieval_results),
        perspectives=[asdict(p) for p in state.perspectives],
        selected_perspective=asdict(state.selected_perspective) if state.selected_perspective else None,
        angles=[asdict(a) for a in state.angles],
        selected_angle=asdict(state.selected_angle) if state.selected_angle else None,
        drafts=[asdict(d) for d in state.drafts],
        selected_draft=asdict(state.selected_draft) if state.selected_draft else None,
        adapted_draft=asdict(draft) if draft else None,
        citations=[asdict(c) for c in state.citations],
        verification_score=state.verification_score,
        hallucination_flags=state.hallucination_flags,
        human_approved=state.human_approved,
        human_feedback=state.human_feedback,
        revision_count=state.revision_count,
        exported_content=state.exported_content,
        evaluation=asdict(state.evaluation) if state.evaluation else None,
        error=state.error,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


@router.post("/start", response_model=WorkflowStateResponse)
async def start_workflow(request: WorkflowStartRequest):
    """Start a new content generation workflow.

    Returns immediately with PENDING status. The pipeline runs in the background.
    Poll GET /{workflow_id} to track progress.
    """
    state = await _workflow_service.create_workflow(request.topic_query)
    _workflow_service.start_workflow(state)
    return _state_to_response(state)


@router.get("/list", response_model=list[WorkflowStateResponse])
async def list_workflows():
    """Get all workflow runs (history)."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(WorkflowRun).order_by(WorkflowRun.created_at.desc()).limit(50)
        )
        runs = result.scalars().all()

        import json
        responses = []
        for run in runs:
            state_dict = json.loads(run.state_json)
            state = _workflow_service._dict_to_state(state_dict)
            responses.append(_state_to_response(state))

        return responses


@router.get("/{workflow_id}", response_model=WorkflowStateResponse)
async def get_workflow_state(workflow_id: str):
    """Get the current state of a workflow."""
    state = await _workflow_service.get_state(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail="工作流未找到")
    return _state_to_response(state)


@router.post("/{workflow_id}/approve", response_model=WorkflowStateResponse)
async def approve_workflow(workflow_id: str, request: WorkflowApprovalRequest):
    """Approve a draft and proceed to export."""
    try:
        state = await _workflow_service.approve(
            workflow_id, edited_content=request.edited_content
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _state_to_response(state)


@router.post("/{workflow_id}/reject", response_model=WorkflowStateResponse)
async def reject_workflow(workflow_id: str, request: WorkflowRejectionRequest):
    """Reject a draft and provide feedback for revision."""
    try:
        state = await _workflow_service.reject(workflow_id, feedback=request.feedback)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _state_to_response(state)


@router.get("/{workflow_id}/diagram")
async def get_workflow_diagram(workflow_id: str):
    """Get a Mermaid diagram of the workflow structure."""
    from app.agents.workflow import ContentGenerationWorkflow
    workflow = ContentGenerationWorkflow.__new__(ContentGenerationWorkflow)
    return {"diagram": workflow.get_state_diagram()}
