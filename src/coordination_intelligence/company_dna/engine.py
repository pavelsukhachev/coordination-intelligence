"""Decision engine that evaluates actions against Company DNA.

The DecisionEngine calculates an alignment score for any proposed
resolution action. Actions that score below the configured threshold
are flagged for escalation rather than automatic execution.
"""

from __future__ import annotations

from coordination_intelligence.company_dna.schema import CompanyDNA
from coordination_intelligence.models import (
    AuthorityLevel,
    Blocker,
    ResolutionAction,
    ResolutionPlan,
    Severity,
)


class AlignmentResult:
    """Result of an alignment check."""

    def __init__(
        self,
        score: float,
        aligned: bool,
        reasons: list[str] | None = None,
    ) -> None:
        self.score = score
        self.aligned = aligned
        self.reasons = reasons or []

    def __repr__(self) -> str:
        status = "ALIGNED" if self.aligned else "MISALIGNED"
        return f"AlignmentResult({status}, score={self.score:.2f})"


class DecisionEngine:
    """Evaluates resolution plans against Company DNA.

    The engine checks:
    1. Authority compliance - is the action within allowed authority?
    2. Value alignment - does the action match core values?
    3. Communication fit - does the channel match preferences?
    4. Principle alignment - does the action align with decision principles?

    Each check contributes to a composite alignment score (0.0-1.0).
    """

    def __init__(self, dna: CompanyDNA, min_score: float = 0.6) -> None:
        self.dna = dna
        self.min_score = min_score
        self._evaluation_log: list[dict[str, object]] = []

    @property
    def evaluation_log(self) -> list[dict[str, object]]:
        """Return the log of all evaluations."""
        return list(self._evaluation_log)

    def evaluate(self, plan: ResolutionPlan, blocker: Blocker) -> AlignmentResult:
        """Evaluate a resolution plan against Company DNA.

        Returns an AlignmentResult with the composite score and
        whether the plan is aligned (score >= min_score).
        """
        reasons: list[str] = []

        # 1. Authority check (0.0 or 0.3).
        authority_score = self._check_authority(plan, blocker, reasons)

        # 2. Value alignment (0.0-0.3).
        value_score = self._check_values(plan, blocker, reasons)

        # 3. Communication fit (0.0-0.2).
        comm_score = self._check_communication(plan, reasons)

        # 4. Principle alignment (0.0-0.2).
        principle_score = self._check_principles(plan, blocker, reasons)

        composite = authority_score + value_score + comm_score + principle_score
        composite = min(max(composite, 0.0), 1.0)

        aligned = composite >= self.min_score

        result = AlignmentResult(score=composite, aligned=aligned, reasons=reasons)

        plan.alignment_score = composite

        self._evaluation_log.append({
            "blocker_id": blocker.id,
            "action": plan.action.value,
            "score": composite,
            "aligned": aligned,
            "components": {
                "authority": authority_score,
                "values": value_score,
                "communication": comm_score,
                "principles": principle_score,
            },
        })

        return result

    def should_execute(self, plan: ResolutionPlan, blocker: Blocker) -> bool:
        """Quick check: should this plan be auto-executed or escalated?"""
        result = self.evaluate(plan, blocker)
        return result.aligned

    # ------------------------------------------------------------------
    # Component checks
    # ------------------------------------------------------------------

    def _check_authority(
        self,
        plan: ResolutionPlan,
        blocker: Blocker,
        reasons: list[str],
    ) -> float:
        """Check if the plan's authority level is appropriate."""
        severity_map = {
            "low": Severity.LOW,
            "medium": Severity.MEDIUM,
            "high": Severity.HIGH,
            "critical": Severity.CRITICAL,
        }

        # Check if action requires approval.
        if plan.action.value in self.dna.authority.require_approval_for:
            if plan.authority_level == AuthorityLevel.IMMEDIATE:
                reasons.append(
                    f"Action '{plan.action.value}' requires approval but has IMMEDIATE authority."
                )
                return 0.0

        # Check severity vs authority level.
        immediate_max = severity_map.get(
            self.dna.authority.immediate_max_severity, Severity.MEDIUM
        )
        severity_rank = {
            Severity.LOW: 0,
            Severity.MEDIUM: 1,
            Severity.HIGH: 2,
            Severity.CRITICAL: 3,
        }

        if plan.authority_level == AuthorityLevel.IMMEDIATE:
            if severity_rank[blocker.severity] > severity_rank[immediate_max]:
                reasons.append(
                    f"Severity {blocker.severity.value} exceeds IMMEDIATE authority max "
                    f"({self.dna.authority.immediate_max_severity})."
                )
                return 0.1

        reasons.append("Authority level is appropriate.")
        return 0.3

    def _check_values(
        self,
        plan: ResolutionPlan,
        blocker: Blocker,
        reasons: list[str],
    ) -> float:
        """Check alignment with core values and anti-patterns."""
        score = 0.15  # Base score.

        text = f"{blocker.title} {blocker.description} {plan.message}".lower()

        # Positive: keywords from priorities.
        for priority in self.dna.core_values.priorities:
            for word in priority.lower().split():
                if len(word) > 3 and word in text:
                    score += 0.05
                    break

        # Negative: anti-patterns.
        for anti in self.dna.core_values.anti_patterns:
            if anti.lower() in text:
                score -= 0.1
                reasons.append(f"Anti-pattern detected: '{anti}'")

        score = min(max(score, 0.0), 0.3)
        if score >= 0.15:
            reasons.append("Action aligns with core values.")
        return score

    def _check_communication(
        self,
        plan: ResolutionPlan,
        reasons: list[str],
    ) -> float:
        """Check if the communication channel fits preferences."""
        score = 0.1  # Base.

        # Prefer async channels.
        if self.dna.communication.prefer_async:
            if plan.action == ResolutionAction.SCHEDULE_MEETING:
                if self.dna.communication.meeting_as_last_resort:
                    reasons.append("Meetings are a last resort per DNA.")
                    return 0.05

        # SMS only for critical urgency.
        from coordination_intelligence.models import ChannelType

        if plan.channel == ChannelType.SMS:
            threshold = self.dna.communication.urgency_threshold_for_sms
            if threshold == "critical":
                score = 0.2
                reasons.append("SMS channel matches critical urgency threshold.")

        score = min(max(score, 0.0), 0.2)
        if score >= 0.1:
            reasons.append("Communication channel is appropriate.")
        return score

    def _check_principles(
        self,
        plan: ResolutionPlan,
        blocker: Blocker,
        reasons: list[str],
    ) -> float:
        """Check alignment with decision principles."""
        if not self.dna.decision_principles:
            reasons.append("No decision principles defined.")
            return 0.1

        text = f"{blocker.title} {blocker.description} {plan.message}".lower()
        total_weight = sum(p.weight for p in self.dna.decision_principles)
        if total_weight == 0:
            return 0.1

        weighted_score = 0.0
        for principle in self.dna.decision_principles:
            for kw in principle.keywords:
                if kw.lower() in text:
                    weighted_score += principle.weight
                    break

        normalized = (weighted_score / total_weight) * 0.2
        normalized = min(max(normalized, 0.0), 0.2)

        if normalized > 0.05:
            reasons.append("Action aligns with decision principles.")
        return normalized
