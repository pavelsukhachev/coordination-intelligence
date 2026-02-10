"""CDI Proxy calculator.

Computes the Coordination Debt Index from six observable metrics:

1. Meeting hours per week
2. Recurring meeting ratio
3. Blocker resolution time (days)
4. Message volume per day
5. Task delay rate
6. Handoff time (hours)

Each metric is normalized to a 0-100 contribution and combined
into a composite score.

Benchmarks:
- Elite:    15-25
- Good:     26-40
- Average:  41-55
- High:     56-70
- Critical: 71+
"""

from __future__ import annotations

from coordination_intelligence.models import CDIBenchmark, CDIMetrics, CDIResult

# Normalization ranges for each metric.
# (min_good, max_bad) - values at min_good score 0, at max_bad score 100.
_RANGES: dict[str, tuple[float, float]] = {
    "meeting_hours": (2.0, 20.0),        # 2h/week = great, 20h/week = terrible
    "recurring_ratio": (0.1, 0.8),       # 10% recurring = great, 80% = terrible
    "resolution_days": (0.5, 10.0),      # 0.5 days = great, 10 days = terrible
    "message_volume": (10.0, 200.0),     # 10 msgs/day = great, 200 = terrible
    "delay_rate": (0.02, 0.5),           # 2% delayed = great, 50% = terrible
    "handoff_hours": (0.5, 24.0),        # 30 min = great, 24h = terrible
}

# Weights for each component (must sum to 1.0).
_WEIGHTS: dict[str, float] = {
    "meeting_hours": 0.20,
    "recurring_ratio": 0.15,
    "resolution_days": 0.25,
    "message_volume": 0.10,
    "delay_rate": 0.20,
    "handoff_hours": 0.10,
}

# Benchmark thresholds.
_BENCHMARKS: list[tuple[float, CDIBenchmark]] = [
    (25.0, CDIBenchmark.ELITE),
    (40.0, CDIBenchmark.GOOD),
    (55.0, CDIBenchmark.AVERAGE),
    (70.0, CDIBenchmark.HIGH),
    (float("inf"), CDIBenchmark.CRITICAL),
]


class CDIProxy:
    """Coordination Debt Index calculator.

    Usage::

        proxy = CDIProxy()
        result = proxy.calculate(CDIMetrics(
            meeting_hours_per_week=8,
            recurring_meeting_ratio=0.4,
            blocker_resolution_days=3.0,
            message_volume_per_day=80,
            task_delay_rate=0.15,
            handoff_time_hours=4.0,
        ))
        print(result.score)      # e.g. 42.5
        print(result.benchmark)  # CDIBenchmark.AVERAGE
    """

    def __init__(self) -> None:
        self._history: list[CDIResult] = []

    @property
    def history(self) -> list[CDIResult]:
        """Return all past calculations."""
        return list(self._history)

    def calculate(self, metrics: CDIMetrics) -> CDIResult:
        """Calculate the CDI score from input metrics.

        Returns a CDIResult with the composite score, benchmark tier,
        component scores, and recommendations.
        """
        components = self._normalize(metrics)
        score = sum(
            components[key] * _WEIGHTS[key]
            for key in _WEIGHTS
        )
        score = round(min(max(score, 0.0), 100.0), 1)

        benchmark = self._classify(score)
        recommendations = self._recommend(components, benchmark)

        result = CDIResult(
            score=score,
            benchmark=benchmark,
            component_scores={k: round(v, 1) for k, v in components.items()},
            recommendations=recommendations,
        )
        self._history.append(result)
        return result

    def trend(self) -> list[float]:
        """Return historical CDI scores for trend analysis."""
        return [r.score for r in self._history]

    def improvement_since(self, n: int = 1) -> float | None:
        """Calculate improvement (negative = better) over last n calculations.

        Returns None if insufficient history.
        """
        if len(self._history) < n + 1:
            return None
        return self._history[-1].score - self._history[-(n + 1)].score

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(metrics: CDIMetrics) -> dict[str, float]:
        """Normalize each metric to a 0-100 scale."""
        raw = {
            "meeting_hours": metrics.meeting_hours_per_week,
            "recurring_ratio": metrics.recurring_meeting_ratio,
            "resolution_days": metrics.blocker_resolution_days,
            "message_volume": metrics.message_volume_per_day,
            "delay_rate": metrics.task_delay_rate,
            "handoff_hours": metrics.handoff_time_hours,
        }

        normalized: dict[str, float] = {}
        for key, value in raw.items():
            lo, hi = _RANGES[key]
            if hi <= lo:
                normalized[key] = 0.0
                continue
            scaled = (value - lo) / (hi - lo) * 100.0
            normalized[key] = min(max(scaled, 0.0), 100.0)

        return normalized

    @staticmethod
    def _classify(score: float) -> CDIBenchmark:
        """Map a score to a benchmark tier."""
        for threshold, benchmark in _BENCHMARKS:
            if score <= threshold:
                return benchmark
        return CDIBenchmark.CRITICAL

    @staticmethod
    def _recommend(
        components: dict[str, float],
        benchmark: CDIBenchmark,
    ) -> list[str]:
        """Generate recommendations based on component scores."""
        recs: list[str] = []

        # Flag any component scoring above 60 as needing attention.
        component_labels = {
            "meeting_hours": "Meeting hours are high. Audit recurring meetings.",
            "recurring_ratio": "Too many recurring meetings. Cancel low-value ones.",
            "resolution_days": "Blocker resolution is slow. Reduce time-to-resolution.",
            "message_volume": "Message volume is high. Consolidate communication.",
            "delay_rate": "Many tasks are delayed. Investigate root causes.",
            "handoff_hours": "Handoff times are long. Streamline handoff process.",
        }

        for key, label in component_labels.items():
            if components.get(key, 0) > 60:
                recs.append(label)

        if benchmark == CDIBenchmark.ELITE:
            recs.append("Score is elite. Maintain current practices.")
        elif benchmark == CDIBenchmark.CRITICAL:
            recs.append("Score is critical. Immediate coordination intervention needed.")

        return recs
