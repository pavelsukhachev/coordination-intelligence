"""Tests for the ResolutionRouter and ResolutionExecutor."""

from __future__ import annotations

import pytest

from coordination_intelligence.arl.resolver import ResolutionExecutor
from coordination_intelligence.arl.router import ResolutionRouter
from coordination_intelligence.models import (
    AuthorityLevel,
    Blocker,
    BlockerStatus,
    BlockerType,
    ChannelType,
    ResolutionAction,
    Severity,
)


@pytest.fixture
def router() -> ResolutionRouter:
    return ResolutionRouter()


@pytest.fixture
def executor() -> ResolutionExecutor:
    return ResolutionExecutor()


class TestResolutionRouter:
    def test_route_dependency_high(self, router, dependency_blocker):
        plan = router.route(dependency_blocker)
        assert plan.action == ResolutionAction.SCHEDULE_MEETING
        assert plan.authority_level == AuthorityLevel.STANDARD
        assert dependency_blocker.status == BlockerStatus.ROUTED

    def test_route_technical_critical(self, router, technical_blocker):
        plan = router.route(technical_blocker)
        assert plan.action == ResolutionAction.ESCALATE
        assert plan.authority_level == AuthorityLevel.ELEVATED

    def test_route_knowledge_medium(self, router, knowledge_blocker):
        plan = router.route(knowledge_blocker)
        assert plan.action == ResolutionAction.PROVIDE_INFO

    def test_route_unclassified_blocker(self, router):
        b = Blocker(title="Mystery blocker", severity=Severity.LOW)
        plan = router.route(b)
        assert plan.action is not None

    def test_max_authority_clamping(self):
        router = ResolutionRouter(max_authority=AuthorityLevel.STANDARD)
        b = Blocker(
            title="Critical org issue",
            blocker_type=BlockerType.ORGANIZATIONAL,
            severity=Severity.CRITICAL,
        )
        plan = router.route(b)
        # CRITICAL ORG would normally escalate to ELEVATED,
        # but max is STANDARD, so it should be clamped.
        assert plan.authority_level == AuthorityLevel.STANDARD

    def test_critical_uses_sms(self, router, technical_blocker):
        plan = router.route(technical_blocker)
        assert plan.channel == ChannelType.SMS

    def test_low_severity_uses_default(self, router):
        b = Blocker(
            title="Minor issue",
            blocker_type=BlockerType.KNOWLEDGE,
            severity=Severity.LOW,
        )
        plan = router.route(b)
        assert plan.channel == ChannelType.SLACK

    def test_route_batch(self, router, dependency_blocker, technical_blocker):
        plans = router.route_batch([dependency_blocker, technical_blocker])
        assert len(plans) == 2
        assert len(router.routed_plans) == 2

    def test_message_composed(self, router, dependency_blocker):
        plan = router.route(dependency_blocker)
        assert plan.message != ""
        assert dependency_blocker.title in plan.message

    def test_fallback_action_set(self, router, dependency_blocker):
        plan = router.route(dependency_blocker)
        assert plan.fallback_action is not None


class TestResolutionExecutor:
    def test_notify(self, executor, dependency_blocker, router):
        plan = router.route(dependency_blocker)
        plan.action = ResolutionAction.NOTIFY
        result = executor.execute(plan, dependency_blocker)
        assert result.success is True

    def test_schedule_meeting(self, executor, alice):
        b = Blocker(title="Discussion needed", affected_employee_ids=[alice.id])
        from coordination_intelligence.models import ResolutionPlan
        plan = ResolutionPlan(
            blocker_id=b.id,
            action=ResolutionAction.SCHEDULE_MEETING,
            authority_level=AuthorityLevel.STANDARD,
            target_employee_ids=[alice.id],
        )
        result = executor.execute(plan, b)
        assert result.success is True

    def test_schedule_meeting_no_participants(self, executor):
        b = Blocker(title="Empty meeting")
        from coordination_intelligence.models import ResolutionPlan
        plan = ResolutionPlan(
            blocker_id=b.id,
            action=ResolutionAction.SCHEDULE_MEETING,
            authority_level=AuthorityLevel.STANDARD,
            target_employee_ids=[],
        )
        result = executor.execute(plan, b)
        assert result.success is False

    def test_escalate(self, executor, technical_blocker, router):
        plan = router.route(technical_blocker)
        plan.action = ResolutionAction.ESCALATE
        result = executor.execute(plan, technical_blocker)
        assert result.success is True
        assert technical_blocker.escalation_count >= 1

    def test_reassign_needs_two_employees(self, executor, alice, bob):
        b = Blocker(title="Reassign task")
        from coordination_intelligence.models import ResolutionPlan
        plan = ResolutionPlan(
            blocker_id=b.id,
            action=ResolutionAction.REASSIGN,
            authority_level=AuthorityLevel.STANDARD,
            target_employee_ids=[alice.id, bob.id],
        )
        result = executor.execute(plan, b)
        assert result.success is True

    def test_reassign_one_employee_fails(self, executor, alice):
        b = Blocker(title="Reassign task")
        from coordination_intelligence.models import ResolutionPlan
        plan = ResolutionPlan(
            blocker_id=b.id,
            action=ResolutionAction.REASSIGN,
            authority_level=AuthorityLevel.STANDARD,
            target_employee_ids=[alice.id],
        )
        result = executor.execute(plan, b)
        assert result.success is False

    def test_connect_peers_needs_two(self, executor, alice, bob):
        b = Blocker(title="Peer help")
        from coordination_intelligence.models import ResolutionPlan
        plan = ResolutionPlan(
            blocker_id=b.id,
            action=ResolutionAction.CONNECT_PEERS,
            authority_level=AuthorityLevel.IMMEDIATE,
            target_employee_ids=[alice.id, bob.id],
        )
        result = executor.execute(plan, b)
        assert result.success is True

    def test_execute_with_fallback(self, executor, alice):
        b = Blocker(title="Peer help")
        from coordination_intelligence.models import ResolutionPlan
        plan = ResolutionPlan(
            blocker_id=b.id,
            action=ResolutionAction.CONNECT_PEERS,
            authority_level=AuthorityLevel.IMMEDIATE,
            target_employee_ids=[alice.id],  # Only 1 = fails.
            fallback_action=ResolutionAction.NOTIFY,
        )
        result = executor.execute_with_fallback(plan, b)
        # Fallback to NOTIFY should succeed.
        assert result.success is True

    def test_success_rate(self, executor, alice, bob):
        from coordination_intelligence.models import ResolutionPlan
        b = Blocker(title="Test")
        # One success.
        plan1 = ResolutionPlan(
            blocker_id=b.id,
            action=ResolutionAction.NOTIFY,
            authority_level=AuthorityLevel.IMMEDIATE,
            target_employee_ids=[alice.id],
        )
        executor.execute(plan1, b)
        assert executor.success_rate == 1.0

    def test_action_log(self, executor, dependency_blocker, router):
        plan = router.route(dependency_blocker)
        executor.execute(plan, dependency_blocker)
        assert len(executor.action_log) == 1
        assert "action" in executor.action_log[0]
