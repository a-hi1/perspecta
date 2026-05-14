"""Agent run log model for observability and replay."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, DateTime, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentRunLog(Base):
    """Persistent log of agent node executions for observability and debugging."""

    __tablename__ = "agent_run_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    trace_id: Mapped[str] = mapped_column(String(36), index=True)
    workflow_name: Mapped[str] = mapped_column(String(100))
    node_name: Mapped[str] = mapped_column(String(100), index=True)

    # Execution details
    input_summary: Mapped[str] = mapped_column(Text)
    output_summary: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[float] = mapped_column(Float)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    prompt_version: Mapped[str] = mapped_column(String(50), default="")

    # State
    state_before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    state_after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="success"
    )  # success, failed, skipped
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Retrieved chunks (for RAG nodes)
    retrieved_chunks: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<AgentRunLog [{self.node_name}] trace={self.trace_id[:8]}>"
