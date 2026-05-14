"""Agent workflow endpoints."""

from fastapi import APIRouter, HTTPException
from app.schemas.workflow import (
    WorkflowStartRequest,
    WorkflowStateResponse,
    WorkflowApprovalRequest,
    WorkflowRejectionRequest,
)
from app.agents.workflow import ContentGenerationWorkflow
from app.agents.state.workflow_state import WorkflowState, WorkflowStatus
from app.llm.factory import get_llm_provider
from app.retrieval.retriever import DualLayerRetriever
from app.services.prompt_loader import PromptLoader

router = APIRouter()

# In-memory state store for MVP
# Production would use Redis or database
_workflow_states: dict[str, WorkflowState] = {}


def _get_workflow() -> ContentGenerationWorkflow:
    """Create a workflow instance."""
    llm = get_llm_provider()
    retriever = DualLayerRetriever(llm)
    return ContentGenerationWorkflow(llm, retriever)


def _state_to_response(state: WorkflowState) -> WorkflowStateResponse:
    """Convert internal state to API response."""
    from dataclasses import asdict

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

    Runs the full pipeline until human review checkpoint.
    """
    workflow = _get_workflow()
    state = await workflow.run(
        user_id="default_user",
        topic_query=request.topic_query,
    )
    _workflow_states[state.workflow_id] = state
    return _state_to_response(state)


@router.get("/{workflow_id}", response_model=WorkflowStateResponse)
async def get_workflow_state(workflow_id: str):
    """Get the current state of a workflow."""
    state = _workflow_states.get(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return _state_to_response(state)


@router.post("/{workflow_id}/approve", response_model=WorkflowStateResponse)
async def approve_workflow(workflow_id: str, request: WorkflowApprovalRequest):
    """Approve a draft and proceed to export.

    Human-in-the-loop: user must explicitly approve.
    Can optionally provide edited content.
    """
    state = _workflow_states.get(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if state.status != WorkflowStatus.WAITING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Workflow is not waiting for approval. Current status: {state.status.value}",
        )

    workflow = _get_workflow()
    state = await workflow.approve(state, edited_content=request.edited_content)
    _workflow_states[workflow_id] = state
    return _state_to_response(state)


@router.post("/{workflow_id}/reject", response_model=WorkflowStateResponse)
async def reject_workflow(workflow_id: str, request: WorkflowRejectionRequest):
    """Reject a draft and provide feedback for revision.

    The workflow will loop back to draft generation with the feedback.
    """
    state = _workflow_states.get(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if state.status != WorkflowStatus.WAITING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Workflow is not waiting for approval. Current status: {state.status.value}",
        )

    workflow = _get_workflow()
    state = await workflow.reject(state, feedback=request.feedback)
    _workflow_states[workflow_id] = state
    return _state_to_response(state)


@router.get("/{workflow_id}/diagram")
async def get_workflow_diagram(workflow_id: str):
    """Get a Mermaid diagram of the workflow structure."""
    workflow = _get_workflow()
    return {"diagram": workflow.get_state_diagram()}
