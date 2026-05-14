# ADR-003: Agent Workflow State Machine

**Date:** 2026-05-15
**Status:** Accepted

## Context

The content generation pipeline involves 10 distinct processing stages. Each stage has different inputs, outputs, and failure modes. We need explicit control over state transitions, observability at each stage, and the ability to pause for human input.

## Decision

### LangGraph StateGraph

Use LangGraph's StateGraph to model the entire pipeline as a directed graph:

```
HotTopic → TopicFilter → KnowledgeRetriever → PerspectiveDiscovery
→ AnglePlanner → DraftGenerator → StyleAdapter → CitationVerifier
→ HumanReview → Export
```

### WorkflowState (dataclass)

A single `WorkflowState` dataclass flows through all nodes. Each node reads specific fields and writes to designated output fields. The state includes:
- Workflow metadata (id, user_id, status, timestamps)
- Stage-specific data (hot_topics, perspectives, drafts, citations)
- Human review fields (approved, feedback, revision_count)
- Evaluation metrics
- Error handling

### Explicit State Transitions

`VALID_TRANSITIONS` dict defines allowed next-states for each node. Invalid transitions raise `WorkflowStateError`. This prevents accidental state corruption.

### Human-in-the-Loop

The `HumanReview` node sets status to `WAITING_APPROVAL` and returns. The workflow pauses until an API call provides approval/rejection. Rejection loops back to `DraftGenerator` with feedback.

### Conditional Routing

After `HumanReview`, a conditional edge routes to either `Export` (approved) or `DraftGenerator` (rejected), or `END` (still waiting).

## Alternatives Considered

1. **Celery task queue** — Overkill for synchronous agent pipeline. LangGraph handles async better.

2. **Custom state machine** — LangGraph provides graph compilation, conditional edges, and checkpointing out of the box.

3. **No state validation** — Rejected. Explicit transitions prevent bugs and make the system debuggable.

## Impact

- Every node must declare its input/output schema in the WorkflowState
- State transitions are validated at runtime
- Tracer captures input/output/latency for every node execution
- HumanReview is a mandatory checkpoint — no bypass allowed
