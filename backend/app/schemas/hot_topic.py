"""Hot topic API schemas."""

from pydantic import BaseModel


class HotTopicResponse(BaseModel):
    """Hot topic response."""
    id: str
    title: str
    summary: str | None = None
    source: str
    source_url: str | None = None
    relevance_score: float = 0.0
    engagement_score: float = 0.0
    freshness_score: float = 0.0
    composite_score: float = 0.0
    tags: dict | None = None
    category: str | None = None
    status: str = "new"

    model_config = {"from_attributes": True}


class HotTopicListResponse(BaseModel):
    """List of hot topics."""
    topics: list[HotTopicResponse]
    total: int
