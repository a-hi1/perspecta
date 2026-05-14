"""Structured logging for agent observability.

Provides JSON-lines logging with fields for:
- agent node name
- input/output summaries
- latency
- token usage
- prompt version
- retrieved chunks (optional)
"""

import json
import logging
import sys
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings

# Context variable for current agent node name
_current_node: ContextVar[str] = ContextVar("current_node", default="unknown")
_current_trace_id: ContextVar[str] = ContextVar("current_trace_id", default="")


class JSONFormatter(logging.Formatter):
    """JSON-lines log formatter for structured agent logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "node": _current_node.get(),
            "trace_id": _current_trace_id.get(),
        }

        # Merge extra fields from record
        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)

        return json.dumps(log_entry, ensure_ascii=False)


class AgentLogAdapter:
    """Structured log adapter for agent nodes.

    Usage:
        logger = AgentLogAdapter("perspective_discovery")
        logger.log_execution(
            input_summary="Found 3 hot topics",
            output_summary="Extracted 5 perspectives",
            latency_ms=1234,
            tokens_used=500,
            prompt_version="v1.2.0",
        )
    """

    def __init__(self, node_name: str):
        self.node_name = node_name
        self._logger = logging.getLogger(f"agent.{node_name}")

    def log_execution(
        self,
        input_summary: str,
        output_summary: str,
        latency_ms: float,
        tokens_used: int = 0,
        prompt_version: str = "",
        retrieved_chunks: list[dict] | None = None,
        error: str | None = None,
    ) -> None:
        """Log a complete agent node execution."""
        extra_data = {
            "event": "agent_execution",
            "node": self.node_name,
            "input_summary": input_summary,
            "output_summary": output_summary,
            "latency_ms": round(latency_ms, 2),
            "tokens_used": tokens_used,
            "prompt_version": prompt_version,
        }

        if retrieved_chunks:
            extra_data["retrieved_chunks_count"] = len(retrieved_chunks)
            extra_data["retrieved_chunks_preview"] = [
                c.get("content", "")[:100] for c in retrieved_chunks[:3]
            ]

        if error:
            extra_data["error"] = error

        record = self._logger.makeRecord(
            name=self._logger.name,
            level=logging.INFO if not error else logging.ERROR,
            fn="",
            lno=0,
            msg=f"Agent node '{self.node_name}' executed",
            args=(),
            exc_info=None,
        )
        record.extra_data = extra_data
        self._logger.handle(record)

    def log_state_transition(self, from_state: str, to_state: str) -> None:
        """Log a workflow state transition."""
        extra_data = {
            "event": "state_transition",
            "from_state": from_state,
            "to_state": to_state,
            "node": self.node_name,
        }
        record = self._logger.makeRecord(
            name=self._logger.name,
            level=logging.INFO,
            fn="",
            lno=0,
            msg=f"State transition: {from_state} -> {to_state}",
            args=(),
            exc_info=None,
        )
        record.extra_data = extra_data
        self._logger.handle(record)


def setup_logging() -> None:
    """Configure application-wide logging."""
    settings = get_settings()
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if settings.LOG_FORMAT == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger."""
    return logging.getLogger(name)
