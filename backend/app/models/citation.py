"""Citation model for source traceability."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Citation(Base):
    """A citation linking draft content to source knowledge chunks."""

    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    draft_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drafts.id"), index=True
    )
    chunk_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_chunks.id"), index=True
    )

    # Citation details
    cited_text: Mapped[str] = mapped_column(Text)
    source_quote: Mapped[str] = mapped_column(Text)
    source_file: Mapped[str] = mapped_column(String(500))
    source_section: Mapped[str | None] = mapped_column(String(500), nullable=True)
    page_number: Mapped[int | None] = None

    # Verification
    verification_status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, verified, failed
    verification_score: Mapped[float] = mapped_column(Float, default=0.0)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    draft: Mapped["Draft"] = relationship(back_populates="citations")
    chunk: Mapped["DocumentChunk"] = relationship(back_populates="citations")

    def __repr__(self) -> str:
        return f"<Citation {self.id[:8]} -> chunk={self.chunk_id[:8]}>"
