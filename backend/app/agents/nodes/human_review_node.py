"""HumanReview node - human-in-the-loop approval checkpoint."""

from datetime import datetime, timezone

from app.agents.state.workflow_state import WorkflowState, AgentNode
from app.observability.logger import AgentLogAdapter

# Configuration
MAX_REVISIONS = 3
TIMEOUT_HOURS = 24


class HumanReviewNode:
    """Human-in-the-loop approval node.

    Pauses the workflow and waits for external human input.
    Enforces revision limits and timeout.

    Input: WorkflowState.adapted_draft, WorkflowState.citations
    Output: WorkflowState.human_approved, WorkflowState.human_feedback
    Next: CONTENT_GENERATION (if rejected) or terminal (if approved)
    """

    def __init__(self):
        self.logger = AgentLogAdapter("human_review")

    async def execute(self, state: WorkflowState) -> WorkflowState:
        """Prepare state for human review and pause.

        Checks revision limit before allowing another review cycle.
        """
        draft = state.adapted_draft or state.selected_draft
        if not draft:
            state.mark_failed("没有待审核的草稿")
            return state

        # Check revision limit
        if state.revision_count >= MAX_REVISIONS:
            state.mark_failed(f"已达到最大修订次数 ({MAX_REVISIONS})")
            self.logger.log_execution(
                input_summary=f"Draft: {draft.title}",
                output_summary=f"Revision limit reached ({state.revision_count}/{MAX_REVISIONS})",
                latency_ms=0,
            )
            return state

        # HUMAN_REVIEW is a terminal node, bypass transition validation
        state.current_node = AgentNode.HUMAN_REVIEW
        state.updated_at = datetime.now(timezone.utc).isoformat()
        state.mark_waiting_approval()

        self.logger.log_execution(
            input_summary=f"Draft: {draft.title}",
            output_summary=f"等待人工审核 (修订 {state.revision_count}/{MAX_REVISIONS})",
            latency_ms=0,
        )

        return state

    @staticmethod
    async def process_approval(
        state: WorkflowState,
        approved: bool,
        feedback: str = "",
        edited_content: str | None = None,
    ) -> WorkflowState:
        """Process human review decision.

        Called by the API endpoint when user submits their review.
        """
        if approved:
            if edited_content:
                draft = state.adapted_draft or state.selected_draft
                if draft:
                    draft.content = edited_content
            state.mark_approved()
        else:
            state.revision_count += 1
            state.mark_rejected(feedback)

        return state

    @staticmethod
    def is_timed_out(state: WorkflowState) -> bool:
        """Check if the review has timed out."""
        if state.status.value != "waiting_approval":
            return False
        if not state.updated_at:
            return False
        try:
            last_update = datetime.fromisoformat(state.updated_at)
            now = datetime.now(timezone.utc)
            if last_update.tzinfo is None:
                from datetime import timezone as tz
                last_update = last_update.replace(tzinfo=tz.utc)
            elapsed_hours = (now - last_update).total_seconds() / 3600
            return elapsed_hours > TIMEOUT_HOURS
        except (ValueError, TypeError):
            return False
