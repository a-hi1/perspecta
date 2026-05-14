"""Hot topic model for trending content discovery."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class HotTopic(Base):
    """A discovered hot topic from external sources."""

    __tablename__ = "hot_topics"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Source information
    source: Mapped[str] = mapped_column(
        String(50), index=True
    )  # reddit, hackernews, arxiv, twitter
    source_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Content
    title: Mapped[str] = mapped_column(String(1000))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_preview: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Scoring
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    engagement_score: Mapped[float] = mapped_column(Float, default=0.0)
    freshness_score: Mapped[float] = mapped_column(Float, default=0.0)
    composite_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Categorization
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="new"
    )  # new, filtered, matched, used

    # Metadata
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    perspectives: Mapped[list["Perspective"]] = relationship(back_populates="hot_topic")

    def __repr__(self) -> str:
        return f"<HotTopic [{self.source}] {self.title[:50]}>"
