"""Workflow-related API schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class WorkflowStartRequest(BaseModel):
    """Request to start a new content generation workflow."""
    topic_query: str = Field(default="", description="Optional topic query. If empty, auto-discovers hot topics.")


class WorkflowStateResponse(BaseModel):
    """Full workflow state response for UI display."""
    workflow_id: str
    user_id: str
    status: str
    current_node: str | None = None

    # Hot topics
    hot_topics: list[dict] = []
    selected_topic: dict | None = None

    # Retrieval
    retrieval_count: int = 0

    # Perspectives
    perspectives: list[dict] = []
    selected_perspective: dict | None = None

    # Angles
    angles: list[dict] = []
    selected_angle: dict | None = None

    # Drafts
    drafts: list[dict] = []
    selected_draft: dict | None = None
    adapted_draft: dict | None = None

    # Verification
    citations: list[dict] = []
    verification_score: float = 0.0
    hallucination_flags: list[dict] = []

    # Review
    human_approved: bool = False
    human_feedback: str = ""
    revision_count: int = 0

    # Export
    exported_content: str = ""

    # Evaluation
    evaluation: dict | None = None

    # Error
    error: str | None = None

    created_at: str = ""
    updated_at: str = ""


class WorkflowApprovalRequest(BaseModel):
    """Human approval of a draft."""
    approved: bool = True
    edited_content: str | None = Field(default=None, description="Optional edited version of the draft.")
    feedback: str = ""


class WorkflowRejectionRequest(BaseModel):
    """Human rejection of a draft with feedback."""
    feedback: str = Field(..., description="Why the draft was rejected and what to improve.")
