"""HumanReview node - human-in-the-loop approval checkpoint."""

from app.agents.state.workflow_state import WorkflowState, AgentNode
from app.observability.logger import AgentLogAdapter


class HumanReviewNode:
    """Human-in-the-loop approval node.

    This node PAUSES the workflow and waits for external human input.
    The workflow cannot proceed until a human explicitly approves or rejects.

    Input: WorkflowState.adapted_draft, WorkflowState.citations
    Output: WorkflowState.human_approved, WorkflowState.human_feedback
    Next: EXPORT (if approved) or DRAFT_GENERATOR (if rejected with feedback)
    """

    def __init__(self):
        self.logger = AgentLogAdapter("human_review")

    async def execute(self, state: WorkflowState) -> WorkflowState:
        """Prepare state for human review and pause.

        This does NOT block - it sets the state to WAITING_APPROVAL
        and returns. The actual human input comes via the API endpoint.
        """
        draft = state.adapted_draft or state.selected_draft
        if not draft:
            state.mark_failed("没有待审核的草稿")
            return state

        state.transition_to(AgentNode.HUMAN_REVIEW)
        state.mark_waiting_approval()

        self.logger.log_execution(
            input_summary=f"Draft: {draft.title}",
            output_summary="等待人工审核",
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
            state.mark_rejected(feedback)
            state.revision_count += 1

        return state
