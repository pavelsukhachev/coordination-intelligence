"""Resolution execution engine.

The ResolutionExecutor takes a ResolutionPlan and executes the
appropriate action: notify, schedule, reassign, escalate, provide
info, or connect peers.

In this reference implementation, actions are simulated and logged
rather than connected to real communication systems.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from coordination_intelligence.models import (
    Blocker,
    BlockerStatus,
    ResolutionAction,
    ResolutionPlan,
)


class ResolutionResult:
    """Outcome of a resolution attempt."""

    def __init__(
        self,
        plan: ResolutionPlan,
        success: bool,
        message: str = "",
        timestamp: datetime | None = None,
    ) -> None:
        self.plan = plan
        self.success = success
        self.message = message
        self.timestamp = timestamp or datetime.now()

    def __repr__(self) -> str:
        status = "OK" if self.success else "FAIL"
        return f"ResolutionResult({status}, action={self.plan.action.value})"


class ResolutionExecutor:
    """Executes resolution plans and tracks outcomes.

    Each action type has a handler method. In this reference
    implementation, all actions are simulated. Production systems
    would integrate with Slack, email, calendar, and task management
    APIs.
    """

    def __init__(self) -> None:
        self._results: list[ResolutionResult] = []
        self._action_log: list[dict[str, object]] = []

    @property
    def results(self) -> list[ResolutionResult]:
        """All resolution results."""
        return list(self._results)

    @property
    def action_log(self) -> list[dict[str, object]]:
        """Detailed log of all actions taken."""
        return list(self._action_log)

    @property
    def success_rate(self) -> float:
        """Fraction of successful resolutions."""
        if not self._results:
            return 0.0
        return sum(1 for r in self._results if r.success) / len(self._results)

    def execute(self, plan: ResolutionPlan, blocker: Blocker) -> ResolutionResult:
        """Execute a resolution plan against a blocker.

        Routes to the appropriate handler based on the plan's action.
        Updates the blocker's status on success.
        """
        handlers = {
            ResolutionAction.NOTIFY: self._handle_notify,
            ResolutionAction.SCHEDULE_MEETING: self._handle_schedule,
            ResolutionAction.REASSIGN: self._handle_reassign,
            ResolutionAction.ESCALATE: self._handle_escalate,
            ResolutionAction.PROVIDE_INFO: self._handle_provide_info,
            ResolutionAction.CONNECT_PEERS: self._handle_connect_peers,
        }

        handler = handlers.get(plan.action, self._handle_notify)
        result = handler(plan, blocker)

        if result.success:
            blocker.status = BlockerStatus.RESOLVED
            blocker.resolved_at = result.timestamp
            blocker.resolution_notes = result.message
        else:
            blocker.status = BlockerStatus.IN_PROGRESS

        self._results.append(result)
        self._action_log.append({
            "blocker_id": blocker.id,
            "action": plan.action.value,
            "success": result.success,
            "message": result.message,
            "timestamp": result.timestamp.isoformat(),
        })

        return result

    def execute_with_fallback(
        self, plan: ResolutionPlan, blocker: Blocker
    ) -> ResolutionResult:
        """Execute a plan. If it fails and a fallback exists, try that too."""
        result = self.execute(plan, blocker)

        if not result.success and plan.fallback_action:
            fallback_plan = plan.model_copy(update={"action": plan.fallback_action})
            result = self.execute(fallback_plan, blocker)

        return result

    # ------------------------------------------------------------------
    # Action handlers (simulated in reference implementation)
    # ------------------------------------------------------------------

    def _handle_notify(self, plan: ResolutionPlan, blocker: Blocker) -> ResolutionResult:
        """Send a notification about the blocker."""
        msg = f"Notified {len(plan.target_employee_ids)} person(s) about: {blocker.title}"
        return ResolutionResult(plan=plan, success=True, message=msg)

    def _handle_schedule(self, plan: ResolutionPlan, blocker: Blocker) -> ResolutionResult:
        """Schedule a meeting to discuss the blocker."""
        if not plan.target_employee_ids:
            return ResolutionResult(
                plan=plan,
                success=False,
                message="No participants for meeting.",
            )
        msg = (
            f"Meeting scheduled for {len(plan.target_employee_ids)} "
            f"participant(s) to resolve: {blocker.title}"
        )
        return ResolutionResult(plan=plan, success=True, message=msg)

    def _handle_reassign(self, plan: ResolutionPlan, blocker: Blocker) -> ResolutionResult:
        """Reassign the blocked task to another team member."""
        if len(plan.target_employee_ids) < 2:
            return ResolutionResult(
                plan=plan,
                success=False,
                message="Need at least 2 employees for reassignment.",
            )
        msg = f"Task reassigned to resolve: {blocker.title}"
        return ResolutionResult(plan=plan, success=True, message=msg)

    def _handle_escalate(self, plan: ResolutionPlan, blocker: Blocker) -> ResolutionResult:
        """Escalate the blocker to management."""
        blocker.escalation_count += 1
        blocker.status = BlockerStatus.ESCALATED
        msg = (
            f"Escalated to management (count: {blocker.escalation_count}): "
            f"{blocker.title}"
        )
        return ResolutionResult(plan=plan, success=True, message=msg)

    def _handle_provide_info(self, plan: ResolutionPlan, blocker: Blocker) -> ResolutionResult:
        """Provide information or documentation links."""
        msg = f"Information provided to resolve: {blocker.title}"
        return ResolutionResult(plan=plan, success=True, message=msg)

    def _handle_connect_peers(self, plan: ResolutionPlan, blocker: Blocker) -> ResolutionResult:
        """Connect the blocked employee with a peer who can help."""
        if len(plan.target_employee_ids) < 2:
            return ResolutionResult(
                plan=plan,
                success=False,
                message="Need at least 2 employees for peer connection.",
            )
        msg = f"Peers connected to resolve: {blocker.title}"
        return ResolutionResult(plan=plan, success=True, message=msg)
