"""Export node - final content export."""

import time

from app.agents.state.workflow_state import WorkflowState, AgentNode, WorkflowStatus
from app.observability.logger import AgentLogAdapter


class ExportNode:
    """Exports the approved draft for the user.

    Input: WorkflowState.adapted_draft (approved)
    Output: WorkflowState.exported_content, WorkflowState.status = COMPLETED
    Next: None (terminal)
    """

    def __init__(self):
        self.logger = AgentLogAdapter("export")

    async def execute(self, state: WorkflowState) -> WorkflowState:
        start = time.monotonic()

        draft = state.adapted_draft or state.selected_draft
        if not draft:
            state.mark_failed("No draft to export")
            return state

        if not state.human_approved:
            state.mark_failed("Cannot export without human approval")
            return state

        # Format for export
        state.exported_content = self._format_for_linkedin(draft.content)
        state.status = WorkflowStatus.COMPLETED
        state.transition_to(AgentNode.EXPORT)

        self.logger.log_execution(
            input_summary=f"Draft: {draft.title}",
            output_summary=f"Exported {len(state.exported_content)} chars",
            latency_ms=(time.monotonic() - start) * 1000,
        )

        return state

    @staticmethod
    def _format_for_linkedin(content: str) -> str:
        """Format content for LinkedIn posting."""
        # LinkedIn-specific formatting
        lines = content.strip().split("\n")
        formatted_lines = []
        for line in lines:
            line = line.strip()
            if line:
                formatted_lines.append(line)
            else:
                formatted_lines.append("")

        return "\n\n".join(formatted_lines)
