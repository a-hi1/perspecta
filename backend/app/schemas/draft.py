"""Draft-related API schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class DraftResponse(BaseModel):
    """Draft response."""
    id: str
    title: str
    content: str
    draft_type: str
    hook: str | None = None
    cta: str | None = None
    style_match_score: float = 0.0
    status: str
    version: int = 1
    review_notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DraftUpdateRequest(BaseModel):
    """Request to update a draft's content."""
    content: str = Field(..., min_length=1)
    change_summary: str = ""


class DraftListResponse(BaseModel):
    """List of drafts."""
    drafts: list[DraftResponse]
    total: int
