"""Draft model for generated LinkedIn content."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, JSON, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Draft(Base):
    """A generated LinkedIn post draft."""

    __tablename__ = "drafts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    perspective_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("perspectives.id"), nullable=True, index=True
    )

    # Content
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    draft_type: Mapped[str] = mapped_column(
        String(50)
    )  # professional, story, controversial
    language: Mapped[str] = mapped_column(String(10), default="en")

    # Structure metadata
    hook: Mapped[str | None] = mapped_column(Text, nullable=True)
    cta: Mapped[str | None] = mapped_column(Text, nullable=True)
    structure_notes: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Style
    style_match_score: Mapped[float] = mapped_column(Float, default=0.0)
    style_profile_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="draft"
    )  # draft, review, approved, exported, rejected
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Human review
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    exported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="drafts")
    perspective: Mapped["Perspective | None"] = relationship(back_populates="drafts")
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="draft", cascade="all, delete-orphan"
    )
    versions: Mapped[list["DraftVersion"]] = relationship(
        back_populates="draft", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Draft [{self.draft_type}] {self.title[:50]}>"


class DraftVersion(Base):
    """Version history for a draft."""

    __tablename__ = "draft_versions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    draft_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drafts.id"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[str] = mapped_column(String(50), default="ai")  # ai, human

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    draft: Mapped["Draft"] = relationship(back_populates="versions")

    def __repr__(self) -> str:
        return f"<DraftVersion v{self.version_number} for draft={self.draft_id[:8]}>"
