"""WorkflowRun model for persistent workflow state storage."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkflowRun(Base):
    """Persistent workflow state for recovery, replay, and debugging."""

    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), index=True, default="default_user")
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    current_node: Mapped[str | None] = mapped_column(String(50), nullable=True)
    topic_query: Mapped[str] = mapped_column(Text, default="")

    # Full serialized WorkflowState (JSON)
    state_json: Mapped[str] = mapped_column(Text, default="{}")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<WorkflowRun {self.id[:8]} status={self.status}>"
