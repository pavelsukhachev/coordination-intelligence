"""The main Autonomous Resolution Loop (ARL).

Orchestrates the 8-step cycle:
DETECT -> CLASSIFY -> ROUTE -> ENGAGE -> COORDINATE -> RESOLVE -> VERIFY -> LEARN

This is the core innovation of the Coordination Intelligence framework.
The loop runs continuously, detecting new blockers, classifying them,
routing to resolution strategies, and learning from outcomes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from coordination_intelligence.arl.classifier import BlockerClassifier
from coordination_intelligence.arl.detector import BlockerDetector
from coordination_intelligence.arl.resolver import ResolutionExecutor, ResolutionResult
from coordination_intelligence.arl.router import ResolutionRouter
from coordination_intelligence.models import (
    ARLConfig,
    Blocker,
    BlockerStatus,
    CheckIn,
    ResolutionPlan,
    Severity,
    Task,
)


class LoopMetrics:
    """Tracks ARL performance metrics across cycles."""

    def __init__(self) -> None:
        self.total_cycles: int = 0
        self.total_detected: int = 0
        self.total_resolved: int = 0
        self.total_escalated: int = 0
        self.total_stale: int = 0
        self.avg_resolution_time_hours: float = 0.0
        self._resolution_times: list[float] = []

    def record_resolution(self, blocker: Blocker) -> None:
        """Record a successful resolution for metrics."""
        if blocker.resolved_at and blocker.detected_at:
            delta = (blocker.resolved_at - blocker.detected_at).total_seconds() / 3600
            self._resolution_times.append(delta)
            self.avg_resolution_time_hours = (
                sum(self._resolution_times) / len(self._resolution_times)
            )

    def summary(self) -> dict[str, Any]:
        """Return a summary dict of all metrics."""
        return {
            "total_cycles": self.total_cycles,
            "total_detected": self.total_detected,
            "total_resolved": self.total_resolved,
            "total_escalated": self.total_escalated,
            "total_stale": self.total_stale,
            "avg_resolution_time_hours": round(self.avg_resolution_time_hours, 2),
            "resolution_rate": (
                self.total_resolved / self.total_detected
                if self.total_detected > 0
                else 0.0
            ),
        }


class AutonomousResolutionLoop:
    """The main ARL orchestrator.

    Usage::

        loop = AutonomousResolutionLoop()
        results = loop.run_cycle(checkins=checkins, tasks=tasks)

    The loop can run one cycle at a time (event-driven) or be called
    repeatedly in a polling pattern.
    """

    def __init__(self, config: ARLConfig | None = None) -> None:
        self.config = config or ARLConfig()
        self.detector = BlockerDetector()
        self.classifier = BlockerClassifier()
        self.router = ResolutionRouter()
        self.executor = ResolutionExecutor()
        self.metrics = LoopMetrics()

        # Active blockers being tracked.
        self._active_blockers: dict[str, Blocker] = {}
        # Resolution plans in flight.
        self._active_plans: dict[str, ResolutionPlan] = {}
        # Learning data: what worked, what did not.
        self._learning_log: list[dict[str, Any]] = []

    @property
    def active_blockers(self) -> list[Blocker]:
        """Return all currently active (unresolved) blockers."""
        return list(self._active_blockers.values())

    @property
    def learning_log(self) -> list[dict[str, Any]]:
        """Return the learning log for analysis."""
        return list(self._learning_log)

    def run_cycle(
        self,
        checkins: list[CheckIn] | None = None,
        tasks: list[Task] | None = None,
        now: datetime | None = None,
    ) -> list[ResolutionResult]:
        """Run one complete ARL cycle.

        Steps:
        1. DETECT - Find new blockers from check-ins and tasks.
        2. CLASSIFY - Assign blocker types.
        3. ROUTE - Create resolution plans.
        4. ENGAGE - (Simulated) Reach out to affected people.
        5. COORDINATE - (Simulated) Orchestrate resolution.
        6. RESOLVE - Execute the resolution plan.
        7. VERIFY - Check if resolution succeeded.
        8. LEARN - Record outcomes for future improvement.

        Returns a list of ResolutionResults from this cycle.
        """
        now = now or datetime.now()
        self.metrics.total_cycles += 1

        # Step 1: DETECT
        new_blockers = self._detect(checkins or [], tasks or [], now)
        self.metrics.total_detected += len(new_blockers)

        # Check for stale blockers that need escalation.
        self._check_escalations(now)

        # Step 2: CLASSIFY
        self.classifier.classify_batch(new_blockers)

        # Step 3: ROUTE
        plans = self.router.route_batch(new_blockers)

        # Steps 4-6: ENGAGE, COORDINATE, RESOLVE
        results: list[ResolutionResult] = []
        for blocker, plan in zip(new_blockers, plans):
            self._active_blockers[str(blocker.id)] = blocker
            self._active_plans[str(blocker.id)] = plan

            result = self.executor.execute_with_fallback(plan, blocker)
            results.append(result)

            # Step 7: VERIFY
            if result.success:
                if blocker.status == BlockerStatus.ESCALATED:
                    self.metrics.total_escalated += 1
                else:
                    self.metrics.total_resolved += 1
                    self.metrics.record_resolution(blocker)
                    del self._active_blockers[str(blocker.id)]

            # Step 8: LEARN
            self._learn(blocker, plan, result)

        return results

    def get_blocker_status(self, blocker_id: str) -> Blocker | None:
        """Look up a tracked blocker by ID."""
        return self._active_blockers.get(blocker_id)

    def force_escalate(self, blocker_id: str) -> ResolutionResult | None:
        """Manually escalate a blocker."""
        blocker = self._active_blockers.get(blocker_id)
        if not blocker:
            return None

        plan = self._active_plans.get(blocker_id)
        if not plan:
            return None

        from coordination_intelligence.models import AuthorityLevel, ResolutionAction

        escalation_plan = plan.model_copy(update={
            "action": ResolutionAction.ESCALATE,
            "authority_level": AuthorityLevel.ELEVATED,
        })

        result = self.executor.execute(escalation_plan, blocker)
        self.metrics.total_escalated += 1
        self._learn(blocker, escalation_plan, result)
        return result

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _detect(
        self,
        checkins: list[CheckIn],
        tasks: list[Task],
        now: datetime,
    ) -> list[Blocker]:
        """Run all detection strategies and return new blockers."""
        blockers: list[Blocker] = []

        for checkin in checkins:
            blockers.extend(self.detector.detect_from_checkin(checkin))

        blockers.extend(self.detector.detect_overdue_tasks(tasks, now))
        blockers.extend(self.detector.detect_stalled_tasks(tasks, now))

        return blockers

    def _check_escalations(self, now: datetime) -> None:
        """Check active blockers for escalation triggers."""
        stale_ids: list[str] = []
        for bid, blocker in self._active_blockers.items():
            if blocker.status in (BlockerStatus.RESOLVED, BlockerStatus.ESCALATED):
                continue

            age = now - blocker.detected_at
            if age > self.config.escalation.escalate_to_director:
                blocker.status = BlockerStatus.STALE
                blocker.severity = Severity.CRITICAL
                self.metrics.total_stale += 1
                stale_ids.append(bid)
            elif age > self.config.escalation.escalate_to_manager:
                if blocker.escalation_count == 0:
                    self.force_escalate(bid)

        # Remove stale blockers from active tracking.
        for bid in stale_ids:
            if bid in self._active_blockers:
                del self._active_blockers[bid]

    def _learn(
        self,
        blocker: Blocker,
        plan: ResolutionPlan,
        result: ResolutionResult,
    ) -> None:
        """Record outcome for future learning."""
        self._learning_log.append({
            "blocker_id": str(blocker.id),
            "blocker_type": blocker.blocker_type.value if blocker.blocker_type else None,
            "severity": blocker.severity.value,
            "action": plan.action.value,
            "channel": plan.channel.value,
            "success": result.success,
            "escalation_count": blocker.escalation_count,
            "timestamp": result.timestamp.isoformat(),
        })
