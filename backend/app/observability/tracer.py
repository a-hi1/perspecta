"""Workflow tracer for debugging and replaying agent runs.

Stores a complete trace of an agent workflow execution including
all node inputs, outputs, state transitions, and timing.
"""

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class NodeTrace:
    """Trace record for a single node execution."""

    node_name: str
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    start_time: float
    end_time: float
    latency_ms: float
    tokens_used: int = 0
    prompt_version: str = ""
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_display(self) -> str:
        if self.latency_ms < 1000:
            return f"{self.latency_ms:.0f}ms"
        return f"{self.latency_ms / 1000:.1f}s"


@dataclass
class WorkflowTrace:
    """Complete trace of a workflow execution."""

    trace_id: str
    workflow_name: str
    started_at: str
    completed_at: str | None = None
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    status: str = "running"
    nodes: list[NodeTrace] = field(default_factory=list)
    final_state: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, default=str)

    def save(self, directory: str = "traces") -> Path:
        """Save trace to a JSON file for later replay."""
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        filepath = path / f"{self.trace_id}.json"
        filepath.write_text(self.to_json(), encoding="utf-8")
        return filepath

    @property
    def summary(self) -> str:
        lines = [
            f"Workflow: {self.workflow_name}",
            f"Trace ID: {self.trace_id}",
            f"Status: {self.status}",
            f"Duration: {self.total_latency_ms:.0f}ms",
            f"Tokens: {self.total_tokens}",
            f"Nodes executed: {len(self.nodes)}",
        ]
        for node in self.nodes:
            status_mark = "✓" if not node.error else "✗"
            lines.append(
                f"  {status_mark} {node.node_name}: {node.duration_display} "
                f"({node.tokens_used} tokens)"
            )
        return "\n".join(lines)


class AgentTracer:
    """Context manager for tracing agent workflow execution.

    Usage:
        tracer = AgentTracer("content_generation")
        with tracer.trace_node("perspective_discovery") as node:
            result = await run_perspective_discovery(state)
            node.set_output(result)
            node.set_tokens(500)
    """

    def __init__(self, workflow_name: str):
        self.workflow_name = workflow_name
        self.trace = WorkflowTrace(
            trace_id=str(uuid.uuid4()),
            workflow_name=workflow_name,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._workflow_start: float = 0.0

    def start(self) -> None:
        self._workflow_start = time.monotonic()

    def trace_node(self, node_name: str) -> "NodeTracerContext":
        return NodeTracerContext(tracer=self, node_name=node_name)

    def finish(self, status: str = "completed", final_state: dict | None = None) -> None:
        self.trace.completed_at = datetime.now(timezone.utc).isoformat()
        self.trace.total_latency_ms = (time.monotonic() - self._workflow_start) * 1000
        self.trace.total_tokens = sum(n.tokens_used for n in self.trace.nodes)
        self.trace.status = status
        if final_state:
            self.trace.final_state = final_state
        self._save_trace()

    def finish_with_error(self, error: str) -> None:
        self.finish(status="failed")
        self.trace.error = error

    def _save_trace(self) -> None:
        """Persist trace to disk."""
        try:
            self.trace.save("traces")
        except Exception:
            pass  # Trace saving is non-critical


class NodeTracerContext:
    """Context manager for tracing a single node execution."""

    def __init__(self, tracer: AgentTracer, node_name: str):
        self.tracer = tracer
        self.node_name = node_name
        self._start: float = 0.0
        self._input: dict = {}
        self._output: dict = {}
        self._tokens: int = 0
        self._prompt_version: str = ""
        self._error: str | None = None

    def __enter__(self) -> "NodeTracerContext":
        self._start = time.monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        end_time = time.monotonic()
        if exc_type is not None:
            self._error = str(exc_val)

        node_trace = NodeTrace(
            node_name=self.node_name,
            input_data=self._input,
            output_data=self._output,
            start_time=self._start,
            end_time=end_time,
            latency_ms=(end_time - self._start) * 1000,
            tokens_used=self._tokens,
            prompt_version=self._prompt_version,
            error=self._error,
        )
        self.tracer.trace.nodes.append(node_trace)

    def set_input(self, data: dict) -> None:
        self._input = data

    def set_output(self, data: dict) -> None:
        self._output = data

    def set_tokens(self, count: int) -> None:
        self._tokens = count

    def set_prompt_version(self, version: str) -> None:
        self._prompt_version = version
