"""Resolution routing based on blocker classification and authority levels.

The router maps each classified blocker to a resolution strategy,
choosing the appropriate action and authority level. It respects
Company DNA alignment when available.
"""

from __future__ import annotations

from coordination_intelligence.models import (
    AuthorityLevel,
    Blocker,
    BlockerStatus,
    BlockerType,
    ChannelType,
    ResolutionAction,
    ResolutionPlan,
    Severity,
)

# Default routing rules: (blocker_type, severity) -> (action, authority).
_ROUTING_TABLE: dict[
    tuple[BlockerType, Severity],
    tuple[ResolutionAction, AuthorityLevel],
] = {
    # Dependency blockers
    (BlockerType.DEPENDENCY, Severity.LOW): (ResolutionAction.NOTIFY, AuthorityLevel.IMMEDIATE),
    (BlockerType.DEPENDENCY, Severity.MEDIUM): (ResolutionAction.NOTIFY, AuthorityLevel.IMMEDIATE),
    (BlockerType.DEPENDENCY, Severity.HIGH): (
        ResolutionAction.SCHEDULE_MEETING,
        AuthorityLevel.STANDARD,
    ),
    (BlockerType.DEPENDENCY, Severity.CRITICAL): (
        ResolutionAction.ESCALATE,
        AuthorityLevel.ELEVATED,
    ),
    # Resource blockers
    (BlockerType.RESOURCE, Severity.LOW): (ResolutionAction.NOTIFY, AuthorityLevel.IMMEDIATE),
    (BlockerType.RESOURCE, Severity.MEDIUM): (
        ResolutionAction.REASSIGN,
        AuthorityLevel.STANDARD,
    ),
    (BlockerType.RESOURCE, Severity.HIGH): (ResolutionAction.REASSIGN, AuthorityLevel.STANDARD),
    (BlockerType.RESOURCE, Severity.CRITICAL): (
        ResolutionAction.ESCALATE,
        AuthorityLevel.ELEVATED,
    ),
    # Technical blockers
    (BlockerType.TECHNICAL, Severity.LOW): (
        ResolutionAction.PROVIDE_INFO,
        AuthorityLevel.IMMEDIATE,
    ),
    (BlockerType.TECHNICAL, Severity.MEDIUM): (
        ResolutionAction.CONNECT_PEERS,
        AuthorityLevel.IMMEDIATE,
    ),
    (BlockerType.TECHNICAL, Severity.HIGH): (
        ResolutionAction.SCHEDULE_MEETING,
        AuthorityLevel.STANDARD,
    ),
    (BlockerType.TECHNICAL, Severity.CRITICAL): (
        ResolutionAction.ESCALATE,
        AuthorityLevel.ELEVATED,
    ),
    # Knowledge blockers
    (BlockerType.KNOWLEDGE, Severity.LOW): (
        ResolutionAction.PROVIDE_INFO,
        AuthorityLevel.IMMEDIATE,
    ),
    (BlockerType.KNOWLEDGE, Severity.MEDIUM): (
        ResolutionAction.PROVIDE_INFO,
        AuthorityLevel.IMMEDIATE,
    ),
    (BlockerType.KNOWLEDGE, Severity.HIGH): (
        ResolutionAction.CONNECT_PEERS,
        AuthorityLevel.STANDARD,
    ),
    (BlockerType.KNOWLEDGE, Severity.CRITICAL): (
        ResolutionAction.SCHEDULE_MEETING,
        AuthorityLevel.STANDARD,
    ),
    # Organizational blockers
    (BlockerType.ORGANIZATIONAL, Severity.LOW): (
        ResolutionAction.NOTIFY,
        AuthorityLevel.IMMEDIATE,
    ),
    (BlockerType.ORGANIZATIONAL, Severity.MEDIUM): (
        ResolutionAction.SCHEDULE_MEETING,
        AuthorityLevel.STANDARD,
    ),
    (BlockerType.ORGANIZATIONAL, Severity.HIGH): (
        ResolutionAction.ESCALATE,
        AuthorityLevel.ELEVATED,
    ),
    (BlockerType.ORGANIZATIONAL, Severity.CRITICAL): (
        ResolutionAction.ESCALATE,
        AuthorityLevel.ELEVATED,
    ),
}

# Fallback actions when authority is insufficient.
_FALLBACK_ACTIONS: dict[ResolutionAction, ResolutionAction] = {
    ResolutionAction.ESCALATE: ResolutionAction.SCHEDULE_MEETING,
    ResolutionAction.REASSIGN: ResolutionAction.NOTIFY,
    ResolutionAction.SCHEDULE_MEETING: ResolutionAction.NOTIFY,
    ResolutionAction.CONNECT_PEERS: ResolutionAction.PROVIDE_INFO,
}


class ResolutionRouter:
    """Routes classified blockers to resolution strategies.

    The router consults a routing table keyed by (blocker_type, severity)
    and produces a ResolutionPlan with the recommended action, authority
    level, and communication channel.
    """

    def __init__(
        self,
        max_authority: AuthorityLevel = AuthorityLevel.ELEVATED,
        default_channel: ChannelType = ChannelType.SLACK,
    ) -> None:
        self.max_authority = max_authority
        self.default_channel = default_channel
        self._routed: list[ResolutionPlan] = []

    @property
    def routed_plans(self) -> list[ResolutionPlan]:
        """Return all resolution plans created so far."""
        return list(self._routed)

    def route(self, blocker: Blocker) -> ResolutionPlan:
        """Create a resolution plan for a classified blocker.

        If the blocker is not yet classified, it defaults to
        ORGANIZATIONAL type with MEDIUM severity.
        """
        btype = blocker.blocker_type or BlockerType.ORGANIZATIONAL
        severity = blocker.severity

        action, authority = _ROUTING_TABLE.get(
            (btype, severity),
            (ResolutionAction.NOTIFY, AuthorityLevel.IMMEDIATE),
        )

        # Clamp authority to max allowed.
        if self._authority_rank(authority) > self._authority_rank(self.max_authority):
            authority = self.max_authority
            action = _FALLBACK_ACTIONS.get(action, ResolutionAction.NOTIFY)

        channel = self._select_channel(severity)

        plan = ResolutionPlan(
            blocker_id=blocker.id,
            action=action,
            authority_level=authority,
            target_employee_ids=list(blocker.affected_employee_ids),
            channel=channel,
            message=self._compose_message(blocker, action),
            fallback_action=_FALLBACK_ACTIONS.get(action),
        )

        blocker.status = BlockerStatus.ROUTED
        blocker.authority_level = authority
        blocker.resolution_action = action

        self._routed.append(plan)
        return plan

    def route_batch(self, blockers: list[Blocker]) -> list[ResolutionPlan]:
        """Route a batch of blockers. Returns list of resolution plans."""
        return [self.route(b) for b in blockers]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _authority_rank(level: AuthorityLevel) -> int:
        """Numeric rank for authority comparison."""
        return {
            AuthorityLevel.IMMEDIATE: 0,
            AuthorityLevel.STANDARD: 1,
            AuthorityLevel.ELEVATED: 2,
        }[level]

    def _select_channel(self, severity: Severity) -> ChannelType:
        """Pick channel based on severity."""
        if severity == Severity.CRITICAL:
            return ChannelType.SMS
        if severity == Severity.HIGH:
            return ChannelType.SLACK
        return self.default_channel

    @staticmethod
    def _compose_message(blocker: Blocker, action: ResolutionAction) -> str:
        """Compose a human-readable resolution message."""
        action_verbs = {
            ResolutionAction.NOTIFY: "Notification",
            ResolutionAction.SCHEDULE_MEETING: "Meeting scheduled",
            ResolutionAction.REASSIGN: "Task reassignment",
            ResolutionAction.ESCALATE: "Escalation",
            ResolutionAction.PROVIDE_INFO: "Information provided",
            ResolutionAction.CONNECT_PEERS: "Peer connection",
        }
        verb = action_verbs.get(action, "Action")
        return f"{verb}: {blocker.title}"
