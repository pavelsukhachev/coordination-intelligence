"""Tests for the BlockerDetector."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from coordination_intelligence.arl.detector import BlockerDetector
from coordination_intelligence.models import (
    BlockerStatus,
    CheckIn,
    Employee,
    Severity,
    Task,
)


@pytest.fixture
def detector() -> BlockerDetector:
    return BlockerDetector()


class TestBlockerDetector:
    def test_detect_explicit_blocker(self, detector, simple_checkin):
        blockers = detector.detect_from_checkin(simple_checkin)
        assert len(blockers) >= 1
        assert blockers[0].status == BlockerStatus.DETECTED

    def test_detect_hidden_blocker_in_working_on(self, detector, alice):
        checkin = CheckIn(
            employee_id=alice.id,
            working_on="Stuck on the integration test. Waiting on API fix.",
        )
        blockers = detector.detect_from_checkin(checkin)
        assert len(blockers) >= 1

    def test_detect_hidden_blocker_in_accomplished(self, detector, alice):
        checkin = CheckIn(
            employee_id=alice.id,
            accomplished="Delayed by missing dependencies.",
        )
        blockers = detector.detect_from_checkin(checkin)
        assert len(blockers) >= 1

    def test_no_blocker_clean_checkin(self, detector, clean_checkin):
        blockers = detector.detect_from_checkin(clean_checkin)
        assert len(blockers) == 0

    def test_help_with_low_sentiment(self, detector, alice):
        checkin = CheckIn(
            employee_id=alice.id,
            working_on="Trying to fix something",
            needs_help=True,
            sentiment=0.1,
        )
        blockers = detector.detect_from_checkin(checkin)
        # Should detect the help+low sentiment signal.
        assert any(b.severity == Severity.HIGH for b in blockers)

    def test_help_with_high_sentiment_no_extra_blocker(self, detector, alice):
        checkin = CheckIn(
            employee_id=alice.id,
            working_on="Minor question about styling",
            needs_help=True,
            sentiment=0.8,
        )
        blockers = detector.detect_from_checkin(checkin)
        # High sentiment + help is not a strong signal.
        assert not any(b.title == "Help requested with low sentiment" for b in blockers)

    def test_overdue_task_detection(self, detector, overdue_task):
        blockers = detector.detect_overdue_tasks([overdue_task])
        assert len(blockers) == 1
        assert "Overdue" in blockers[0].title

    def test_overdue_task_severity(self, detector, alice):
        # 10 days overdue = critical.
        task = Task(
            title="Critical Feature",
            assignee_id=alice.id,
            due_date=datetime.now() - timedelta(days=10),
        )
        blockers = detector.detect_overdue_tasks([task])
        assert blockers[0].severity == Severity.CRITICAL

    def test_completed_task_not_overdue(self, detector):
        task = Task(
            title="Done",
            due_date=datetime.now() - timedelta(days=10),
            completed=True,
        )
        blockers = detector.detect_overdue_tasks([task])
        assert len(blockers) == 0

    def test_stalled_task_detection(self, detector, stalled_task):
        blockers = detector.detect_stalled_tasks([stalled_task])
        assert len(blockers) == 1
        assert "Stalled" in blockers[0].title

    def test_stalled_below_threshold_ignored(self, detector, bob):
        task = Task(
            title="Recent",
            assignee_id=bob.id,
            stalled_since=datetime.now() - timedelta(hours=1),
        )
        blockers = detector.detect_stalled_tasks([task])
        assert len(blockers) == 0

    def test_detected_blockers_accumulated(self, detector, simple_checkin, overdue_task):
        detector.detect_from_checkin(simple_checkin)
        detector.detect_overdue_tasks([overdue_task])
        assert len(detector.detected_blockers) >= 2

    def test_clear(self, detector, simple_checkin):
        detector.detect_from_checkin(simple_checkin)
        assert len(detector.detected_blockers) > 0
        detector.clear()
        assert len(detector.detected_blockers) == 0

    def test_severity_estimation_critical(self, detector):
        sev = BlockerDetector._estimate_severity("This is a critical urgent emergency!")
        assert sev == Severity.CRITICAL

    def test_severity_estimation_high(self, detector):
        sev = BlockerDetector._estimate_severity("High priority: release blocker")
        assert sev == Severity.HIGH

    def test_severity_estimation_default(self, detector):
        sev = BlockerDetector._estimate_severity("Something happened")
        assert sev == Severity.MEDIUM

    def test_title_extraction(self, detector):
        title = BlockerDetector._extract_title("This is a blocker. More details here.")
        assert title == "This is a blocker"

    def test_title_truncation(self, detector):
        long_text = "A" * 200
        title = BlockerDetector._extract_title(long_text, max_len=50)
        assert len(title) <= 50
        assert title.endswith("...")

    def test_custom_stale_threshold(self, bob):
        detector = BlockerDetector(stale_threshold=timedelta(hours=12))
        task = Task(
            title="Short stall",
            assignee_id=bob.id,
            stalled_since=datetime.now() - timedelta(hours=13),
        )
        blockers = detector.detect_stalled_tasks([task])
        assert len(blockers) == 1

    def test_multiple_patterns_in_text(self, detector, alice):
        checkin = CheckIn(
            employee_id=alice.id,
            working_on="Blocked and stuck. Need help. No response from team. Escalate this.",
        )
        blockers = detector.detect_from_checkin(checkin)
        # Should detect from the working_on field (one blocker per field).
        assert len(blockers) >= 1
