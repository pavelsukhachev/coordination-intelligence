"""Tests for the CDI Proxy calculator."""

from __future__ import annotations

import pytest

from coordination_intelligence.cdi.proxy import CDIProxy
from coordination_intelligence.models import CDIBenchmark, CDIMetrics


@pytest.fixture
def proxy() -> CDIProxy:
    return CDIProxy()


class TestCDIProxy:
    def test_elite_score(self, proxy):
        """Minimal coordination overhead = elite score."""
        metrics = CDIMetrics(
            meeting_hours_per_week=2.0,
            recurring_meeting_ratio=0.1,
            blocker_resolution_days=0.5,
            message_volume_per_day=10.0,
            task_delay_rate=0.02,
            handoff_time_hours=0.5,
        )
        result = proxy.calculate(metrics)
        assert result.score <= 25.0
        assert result.benchmark == CDIBenchmark.ELITE

    def test_critical_score(self, proxy):
        """Maximum overhead = critical score."""
        metrics = CDIMetrics(
            meeting_hours_per_week=25.0,
            recurring_meeting_ratio=0.9,
            blocker_resolution_days=15.0,
            message_volume_per_day=300.0,
            task_delay_rate=0.6,
            handoff_time_hours=30.0,
        )
        result = proxy.calculate(metrics)
        assert result.score >= 71.0
        assert result.benchmark == CDIBenchmark.CRITICAL

    def test_average_score(self, proxy):
        """Mid-range values = average score."""
        metrics = CDIMetrics(
            meeting_hours_per_week=10.0,
            recurring_meeting_ratio=0.4,
            blocker_resolution_days=5.0,
            message_volume_per_day=100.0,
            task_delay_rate=0.2,
            handoff_time_hours=10.0,
        )
        result = proxy.calculate(metrics)
        assert 30.0 <= result.score <= 65.0

    def test_score_bounded_0_100(self, proxy):
        # Extreme low.
        low = CDIMetrics()  # All zeros.
        r1 = proxy.calculate(low)
        assert r1.score >= 0.0

        # Extreme high.
        high = CDIMetrics(
            meeting_hours_per_week=100,
            recurring_meeting_ratio=1.0,
            blocker_resolution_days=100,
            message_volume_per_day=1000,
            task_delay_rate=1.0,
            handoff_time_hours=100,
        )
        r2 = proxy.calculate(high)
        assert r2.score <= 100.0

    def test_component_scores(self, proxy):
        metrics = CDIMetrics(
            meeting_hours_per_week=8.0,
            recurring_meeting_ratio=0.3,
            blocker_resolution_days=3.0,
            message_volume_per_day=50.0,
            task_delay_rate=0.1,
            handoff_time_hours=4.0,
        )
        result = proxy.calculate(metrics)
        assert "meeting_hours" in result.component_scores
        assert "resolution_days" in result.component_scores
        assert len(result.component_scores) == 6

    def test_recommendations_generated(self, proxy):
        metrics = CDIMetrics(
            meeting_hours_per_week=18.0,  # High
            recurring_meeting_ratio=0.7,  # High
            blocker_resolution_days=2.0,
            message_volume_per_day=30.0,
            task_delay_rate=0.05,
            handoff_time_hours=2.0,
        )
        result = proxy.calculate(metrics)
        assert len(result.recommendations) > 0
        assert any("meeting" in r.lower() for r in result.recommendations)

    def test_elite_recommendation(self, proxy):
        metrics = CDIMetrics(
            meeting_hours_per_week=2.0,
            recurring_meeting_ratio=0.1,
            blocker_resolution_days=0.5,
            message_volume_per_day=10.0,
            task_delay_rate=0.02,
            handoff_time_hours=0.5,
        )
        result = proxy.calculate(metrics)
        assert any("elite" in r.lower() for r in result.recommendations)

    def test_critical_recommendation(self, proxy):
        metrics = CDIMetrics(
            meeting_hours_per_week=25.0,
            recurring_meeting_ratio=0.9,
            blocker_resolution_days=15.0,
            message_volume_per_day=300.0,
            task_delay_rate=0.6,
            handoff_time_hours=30.0,
        )
        result = proxy.calculate(metrics)
        assert any("critical" in r.lower() for r in result.recommendations)

    def test_history_tracking(self, proxy):
        m1 = CDIMetrics(meeting_hours_per_week=5.0, blocker_resolution_days=2.0)
        m2 = CDIMetrics(meeting_hours_per_week=10.0, blocker_resolution_days=5.0)
        proxy.calculate(m1)
        proxy.calculate(m2)
        assert len(proxy.history) == 2

    def test_trend(self, proxy):
        for hours in [5.0, 8.0, 12.0, 15.0]:
            proxy.calculate(CDIMetrics(meeting_hours_per_week=hours))
        trend = proxy.trend()
        assert len(trend) == 4
        # Scores should increase with more meeting hours.
        assert trend[-1] > trend[0]

    def test_improvement_since(self, proxy):
        proxy.calculate(CDIMetrics(meeting_hours_per_week=15.0, blocker_resolution_days=8.0))
        proxy.calculate(CDIMetrics(meeting_hours_per_week=5.0, blocker_resolution_days=2.0))
        improvement = proxy.improvement_since(1)
        assert improvement is not None
        assert improvement < 0  # Negative = improved.

    def test_improvement_insufficient_history(self, proxy):
        assert proxy.improvement_since(1) is None

    def test_good_benchmark(self, proxy):
        metrics = CDIMetrics(
            meeting_hours_per_week=6.0,
            recurring_meeting_ratio=0.25,
            blocker_resolution_days=2.0,
            message_volume_per_day=40.0,
            task_delay_rate=0.08,
            handoff_time_hours=3.0,
        )
        result = proxy.calculate(metrics)
        assert result.benchmark in (CDIBenchmark.ELITE, CDIBenchmark.GOOD)

    def test_all_zeros_score(self, proxy):
        result = proxy.calculate(CDIMetrics())
        # All at minimum = score should be very low.
        assert result.score < 10.0
