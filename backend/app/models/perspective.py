"""Perspective model for discovered user viewpoints."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Perspective(Base):
    """A discovered user perspective/viewpoint derived from knowledge base."""

    __tablename__ = "perspectives"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    hot_topic_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("hot_topics.id"), nullable=True, index=True
    )

    # Perspective content
    perspective_text: Mapped[str] = mapped_column(Text)
    perspective_type: Mapped[str] = mapped_column(
        String(50)
    )  # judgment, reflection, lesson, controversy, summary
    angle: Mapped[str | None] = mapped_column(Text, nullable=True)
    hook_idea: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Quality scoring
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    novelty: Mapped[float] = mapped_column(Float, default=0.0)
    engagement_potential: Mapped[float] = mapped_column(Float, default=0.0)

    # Source traceability
    source_chunks: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # list of chunk IDs used

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="discovered"
    )  # discovered, selected, used, discarded
    user_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    hot_topic: Mapped["HotTopic | None"] = relationship(back_populates="perspectives")
    drafts: Mapped[list["Draft"]] = relationship(back_populates="perspective")

    def __repr__(self) -> str:
        return f"<Perspective [{self.perspective_type}] {self.perspective_text[:50]}>"
