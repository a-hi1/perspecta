"""Perspective API schemas."""

from pydantic import BaseModel


class PerspectiveResponse(BaseModel):
    """Perspective response."""
    id: str
    perspective_text: str
    perspective_type: str
    angle: str | None = None
    hook_idea: str | None = None
    confidence: float = 0.0
    novelty: float = 0.0
    engagement_potential: float = 0.0
    source_chunks: dict | None = None
    status: str = "discovered"
    user_feedback: str | None = None

    model_config = {"from_attributes": True}


class PerspectiveListResponse(BaseModel):
    """List of perspectives."""
    perspectives: list[PerspectiveResponse]
    total: int
