"""Workflow state schema for the content generation pipeline.

This defines the complete state that flows through the LangGraph workflow.
Each node reads from and writes to this state.
"""

from enum import Enum
from typing import Any
from dataclasses import dataclass, field
from datetime import datetime


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentNode(str, Enum):
    """All agent nodes in the workflow."""

    HOT_TOPIC = "hot_topic"
    TOPIC_FILTER = "topic_filter"
    KNOWLEDGE_RETRIEVER = "knowledge_retriever"
    PERSPECTIVE_DISCOVERY = "perspective_discovery"
    ANGLE_PLANNER = "angle_planner"
    DRAFT_GENERATOR = "draft_generator"
    STYLE_ADAPTER = "style_adapter"
    CITATION_VERIFIER = "citation_verifier"
    HUMAN_REVIEW = "human_review"
    EXPORT = "export"


# Valid state transitions
VALID_TRANSITIONS: dict[AgentNode, list[AgentNode]] = {
    AgentNode.HOT_TOPIC: [AgentNode.TOPIC_FILTER],
    AgentNode.TOPIC_FILTER: [AgentNode.KNOWLEDGE_RETRIEVER],
    AgentNode.KNOWLEDGE_RETRIEVER: [AgentNode.PERSPECTIVE_DISCOVERY],
    AgentNode.PERSPECTIVE_DISCOVERY: [AgentNode.ANGLE_PLANNER],
    AgentNode.ANGLE_PLANNER: [AgentNode.DRAFT_GENERATOR],
    AgentNode.DRAFT_GENERATOR: [AgentNode.STYLE_ADAPTER],
    AgentNode.STYLE_ADAPTER: [AgentNode.CITATION_VERIFIER],
    AgentNode.CITATION_VERIFIER: [AgentNode.HUMAN_REVIEW],
    AgentNode.HUMAN_REVIEW: [AgentNode.EXPORT, AgentNode.DRAFT_GENERATOR],  # Can loop back
    AgentNode.EXPORT: [],  # Terminal state
}


@dataclass
class HotTopicData:
    """Data for a hot topic."""

    id: str = ""
    title: str = ""
    summary: str = ""
    source: str = ""
    source_url: str = ""
    relevance_score: float = 0.0
    engagement_score: float = 0.0
    freshness_score: float = 0.0
    composite_score: float = 0.0
    tags: list[str] = field(default_factory=list)
    category: str = ""


@dataclass
class PerspectiveData:
    """Data for a discovered perspective."""

    id: str = ""
    perspective_text: str = ""
    perspective_type: str = ""  # judgment, reflection, lesson, controversy, summary
    source_chunk_ids: list[str] = field(default_factory=list)
    source_quotes: list[str] = field(default_factory=list)
    confidence: float = 0.0
    novelty: float = 0.0
    engagement_potential: float = 0.0
    reasoning: str = ""


@dataclass
class AngleData:
    """Data for a content angle."""

    style: str = ""  # professional, story, controversial
    hook: str = ""
    angle_description: str = ""
    structure: list[dict] = field(default_factory=list)
    tone_notes: str = ""
    estimated_length: str = "medium"
    engagement_prediction: float = 0.0


@dataclass
class DraftData:
    """Data for a generated draft."""

    id: str = ""
    title: str = ""
    content: str = ""
    draft_type: str = ""
    hook: str = ""
    cta: str = ""
    structure_notes: dict = field(default_factory=dict)
    citation_markers: list[dict] = field(default_factory=list)
    style_match_score: float = 0.0


@dataclass
class CitationData:
    """Data for a citation."""

    id: str = ""
    cited_text: str = ""
    source_quote: str = ""
    source_file: str = ""
    source_section: str = ""
    status: str = "pending"  # pending, verified, failed
    verification_score: float = 0.0


@dataclass
class RetrievalData:
    """Data from knowledge retrieval."""

    chunk_id: str = ""
    content: str = ""
    score: float = 0.0
    source_file: str = ""
    section_title: str = ""
    page_number: int | None = None


@dataclass
class EvaluationData:
    """Evaluation metrics for the pipeline run."""

    retrieval_relevance: float = 0.0
    perspective_quality: float = 0.0
    hallucination_score: float = 0.0
    overall_score: float = 0.0
    recommendations: list[str] = field(default_factory=list)


@dataclass
class WorkflowState:
    """Complete state for the content generation workflow.

    This is the state that flows through all nodes in the LangGraph graph.
    Each node reads specific fields and writes its output to designated fields.

    State flow:
    HOT_TOPIC -> TOPIC_FILTER -> KNOWLEDGE_RETRIEVER -> PERSPECTIVE_DISCOVERY
    -> ANGLE_PLANNER -> DRAFT_GENERATOR -> STYLE_ADAPTER -> CITATION_VERIFIER
    -> HUMAN_REVIEW -> EXPORT
    """

    # --- Workflow metadata ---
    workflow_id: str = ""
    user_id: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_node: AgentNode | None = None
    created_at: str = ""
    updated_at: str = ""

    # --- Input ---
    topic_query: str = ""  # Optional manual topic query

    # --- Hot Topic stage ---
    hot_topics: list[HotTopicData] = field(default_factory=list)
    selected_topic: HotTopicData | None = None

    # --- Knowledge Retrieval stage ---
    retrieval_results: list[RetrievalData] = field(default_factory=list)

    # --- Perspective Discovery stage ---
    perspectives: list[PerspectiveData] = field(default_factory=list)
    selected_perspective: PerspectiveData | None = None

    # --- Angle Planning stage ---
    angles: list[AngleData] = field(default_factory=list)
    selected_angle: AngleData | None = None

    # --- Draft Generation stage ---
    drafts: list[DraftData] = field(default_factory=list)
    selected_draft: DraftData | None = None

    # --- Style Adaptation stage ---
    adapted_draft: DraftData | None = None
    style_changes: list[dict] = field(default_factory=list)

    # --- Citation Verification stage ---
    citations: list[CitationData] = field(default_factory=list)
    verification_score: float = 0.0
    hallucination_flags: list[dict] = field(default_factory=list)

    # --- Human Review stage ---
    human_approved: bool = False
    human_feedback: str = ""
    revision_count: int = 0

    # --- Export stage ---
    exported_content: str = ""
    export_format: str = "linkedin"

    # --- Evaluation ---
    evaluation: EvaluationData | None = None

    # --- Error handling ---
    error: str | None = None
    retry_count: int = 0

    def transition_to(self, node: AgentNode) -> None:
        """Validate and execute a state transition."""
        if self.current_node is not None:
            valid = VALID_TRANSITIONS.get(self.current_node, [])
            if node not in valid:
                from app.core.exceptions import WorkflowStateError
                raise WorkflowStateError(
                    current_state=self.current_node.value,
                    target_state=node.value,
                )
        self.current_node = node
        self.updated_at = datetime.utcnow().isoformat()

    def mark_waiting_approval(self) -> None:
        """Mark workflow as waiting for human approval."""
        self.status = WorkflowStatus.WAITING_APPROVAL

    def mark_approved(self) -> None:
        """Mark workflow as approved by human."""
        self.status = WorkflowStatus.APPROVED
        self.human_approved = True

    def mark_rejected(self, feedback: str = "") -> None:
        """Mark workflow as rejected by human."""
        self.status = WorkflowStatus.REJECTED
        self.human_feedback = feedback
        self.human_approved = False

    def mark_failed(self, error: str) -> None:
        """Mark workflow as failed."""
        self.status = WorkflowStatus.FAILED
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Serialize state to dict for storage/logging."""
        from dataclasses import asdict
        return asdict(self)
