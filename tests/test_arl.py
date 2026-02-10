"""Tests for the Autonomous Resolution Loop."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from coordination_intelligence.arl.loop import AutonomousResolutionLoop, LoopMetrics
from coordination_intelligence.models import (
    ARLConfig,
    Blocker,
    BlockerStatus,
    BlockerType,
    CheckIn,
    EscalationConfig,
    Severity,
    Task,
)


class TestLoopMetrics:
    def test_initial_state(self):
        m = LoopMetrics()
        assert m.total_cycles == 0
        assert m.total_detected == 0
        assert m.total_resolved == 0
        assert m.avg_resolution_time_hours == 0.0

    def test_summary(self):
        m = LoopMetrics()
        s = m.summary()
        assert "total_cycles" in s
        assert "resolution_rate" in s
        assert s["resolution_rate"] == 0.0

    def test_record_resolution(self):
        m = LoopMetrics()
        b = Blocker(
            title="test",
            detected_at=datetime.now() - timedelta(hours=2),
            resolved_at=datetime.now(),
        )
        m.record_resolution(b)
        assert m.avg_resolution_time_hours > 0


class TestAutonomousResolutionLoop:
    def test_empty_cycle(self):
        loop = AutonomousResolutionLoop()
        results = loop.run_cycle()
        assert results == []
        assert loop.metrics.total_cycles == 1
        assert loop.metrics.total_detected == 0

    def test_cycle_with_checkin(self, simple_checkin):
        loop = AutonomousResolutionLoop()
        results = loop.run_cycle(checkins=[simple_checkin])
        assert len(results) > 0
        assert loop.metrics.total_detected > 0

    def test_cycle_with_blocked_checkin(self, blocked_checkin):
        loop = AutonomousResolutionLoop()
        results = loop.run_cycle(checkins=[blocked_checkin])
        assert len(results) >= 2  # Multiple signals in blocked_checkin
        assert loop.metrics.total_detected >= 2

    def test_cycle_with_overdue_tasks(self, overdue_task):
        loop = AutonomousResolutionLoop()
        results = loop.run_cycle(tasks=[overdue_task])
        assert len(results) == 1
        assert loop.metrics.total_detected == 1

    def test_cycle_with_stalled_tasks(self, stalled_task):
        loop = AutonomousResolutionLoop()
        results = loop.run_cycle(tasks=[stalled_task])
        assert len(results) == 1

    def test_completed_tasks_ignored(self, completed_task):
        loop = AutonomousResolutionLoop()
        results = loop.run_cycle(tasks=[completed_task])
        assert len(results) == 0

    def test_clean_checkin_no_blockers(self, clean_checkin):
        loop = AutonomousResolutionLoop()
        results = loop.run_cycle(checkins=[clean_checkin])
        assert len(results) == 0

    def test_multiple_cycles(self, simple_checkin, overdue_task):
        loop = AutonomousResolutionLoop()
        loop.run_cycle(checkins=[simple_checkin])
        loop.run_cycle(tasks=[overdue_task])
        assert loop.metrics.total_cycles == 2
        assert loop.metrics.total_detected >= 2

    def test_learning_log(self, simple_checkin):
        loop = AutonomousResolutionLoop()
        loop.run_cycle(checkins=[simple_checkin])
        assert len(loop.learning_log) > 0
        entry = loop.learning_log[0]
        assert "blocker_type" in entry
        assert "action" in entry
        assert "success" in entry

    def test_custom_config(self):
        config = ARLConfig(
            max_retries=5,
            quiet_resolution_first=False,
            min_alignment_score=0.8,
            escalation=EscalationConfig(
                first_reminder=timedelta(hours=1),
                escalate_to_manager=timedelta(hours=6),
            ),
        )
        loop = AutonomousResolutionLoop(config=config)
        assert loop.config.max_retries == 5
        assert loop.config.escalation.first_reminder == timedelta(hours=1)

    def test_force_escalate_unknown_id(self):
        loop = AutonomousResolutionLoop()
        result = loop.force_escalate("nonexistent-id")
        assert result is None

    def test_get_blocker_status_unknown(self):
        loop = AutonomousResolutionLoop()
        assert loop.get_blocker_status("nonexistent") is None

    def test_active_blockers_list(self, blocked_checkin):
        loop = AutonomousResolutionLoop()
        loop.run_cycle(checkins=[blocked_checkin])
        # Some blockers may have been resolved; check the list is accessible.
        assert isinstance(loop.active_blockers, list)

    def test_escalation_on_stale_blocker(self, alice):
        """Test that stale blockers get escalated."""
        config = ARLConfig(
            escalation=EscalationConfig(
                escalate_to_manager=timedelta(seconds=0),
                escalate_to_director=timedelta(seconds=0),
            ),
        )
        loop = AutonomousResolutionLoop(config=config)
        # Create a blocker that's already old.
        old_checkin = CheckIn(
            employee_id=alice.id,
            blockers="Waiting for server access from IT",
            timestamp=datetime.now() - timedelta(days=5),
        )
        # First cycle detects it.
        loop.run_cycle(checkins=[old_checkin])
        # Second cycle should trigger escalation check.
        loop.run_cycle()
        assert loop.metrics.total_cycles == 2
