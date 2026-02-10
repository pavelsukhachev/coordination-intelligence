"""Channel selection using weighted multi-factor scoring.

The scoring formula:
  score = response_rate * 0.30
        + response_speed * 0.25
        + preference * 0.20
        + urgency_match * 0.15
        + complexity_match * 0.10

The selector learns from feedback by adjusting response_rate and
response_speed for each (employee, channel) pair.
"""

from __future__ import annotations

from uuid import UUID

from coordination_intelligence.models import (
    ChannelScore,
    ChannelType,
    Employee,
    Severity,
)

# Weights for the scoring formula.
W_RESPONSE_RATE = 0.30
W_RESPONSE_SPEED = 0.25
W_PREFERENCE = 0.20
W_URGENCY_MATCH = 0.15
W_COMPLEXITY_MATCH = 0.10

# Default response rates per channel (prior).
_DEFAULT_RESPONSE_RATES: dict[ChannelType, float] = {
    ChannelType.SLACK: 0.85,
    ChannelType.EMAIL: 0.70,
    ChannelType.SMS: 0.95,
}

# Default response speed scores (1.0 = fastest).
_DEFAULT_RESPONSE_SPEEDS: dict[ChannelType, float] = {
    ChannelType.SLACK: 0.80,
    ChannelType.EMAIL: 0.40,
    ChannelType.SMS: 0.95,
}

# Urgency match: how well each channel fits each severity level.
_URGENCY_MATCH: dict[ChannelType, dict[Severity, float]] = {
    ChannelType.SLACK: {
        Severity.LOW: 0.9,
        Severity.MEDIUM: 0.85,
        Severity.HIGH: 0.7,
        Severity.CRITICAL: 0.5,
    },
    ChannelType.EMAIL: {
        Severity.LOW: 0.8,
        Severity.MEDIUM: 0.7,
        Severity.HIGH: 0.4,
        Severity.CRITICAL: 0.2,
    },
    ChannelType.SMS: {
        Severity.LOW: 0.3,
        Severity.MEDIUM: 0.5,
        Severity.HIGH: 0.8,
        Severity.CRITICAL: 1.0,
    },
}

# Complexity match: simple messages vs complex (multi-step, detailed).
_COMPLEXITY_MATCH: dict[ChannelType, dict[str, float]] = {
    ChannelType.SLACK: {"simple": 0.9, "medium": 0.7, "complex": 0.5},
    ChannelType.EMAIL: {"simple": 0.5, "medium": 0.8, "complex": 0.9},
    ChannelType.SMS: {"simple": 0.9, "medium": 0.4, "complex": 0.2},
}


class ChannelSelector:
    """Selects the optimal communication channel using weighted scoring.

    The selector maintains per-employee, per-channel stats and learns
    from feedback to improve future selections.
    """

    def __init__(self) -> None:
        # (employee_id, channel) -> {response_rate, response_speed, attempts, successes}
        self._stats: dict[tuple[UUID, ChannelType], dict[str, float]] = {}

    def select(
        self,
        employee: Employee,
        severity: Severity = Severity.MEDIUM,
        complexity: str = "simple",
    ) -> ChannelScore:
        """Select the best channel for reaching an employee.

        Args:
            employee: The target employee.
            severity: Urgency level of the message.
            complexity: Message complexity (simple, medium, complex).

        Returns:
            A ChannelScore for the best channel.
        """
        scores = self.score_all(employee, severity, complexity)
        return max(scores, key=lambda s: s.score)

    def score_all(
        self,
        employee: Employee,
        severity: Severity = Severity.MEDIUM,
        complexity: str = "simple",
    ) -> list[ChannelScore]:
        """Score all channels for an employee. Returns sorted list (best first)."""
        results: list[ChannelScore] = []

        for channel in ChannelType:
            score_obj = self._score_channel(employee, channel, severity, complexity)
            results.append(score_obj)

        results.sort(key=lambda s: s.score, reverse=True)
        return results

    def record_feedback(
        self,
        employee_id: UUID,
        channel: ChannelType,
        responded: bool,
        response_time_minutes: float | None = None,
    ) -> None:
        """Record feedback from a communication attempt.

        This updates the per-employee stats for the channel, allowing
        the selector to learn from real-world outcomes.
        """
        key = (employee_id, channel)
        stats = self._stats.get(key, {
            "response_rate": _DEFAULT_RESPONSE_RATES[channel],
            "response_speed": _DEFAULT_RESPONSE_SPEEDS[channel],
            "attempts": 0.0,
            "successes": 0.0,
        })

        stats["attempts"] += 1
        if responded:
            stats["successes"] += 1

        # Update response rate with exponential moving average.
        alpha = 0.3  # Learning rate.
        actual_rate = stats["successes"] / stats["attempts"]
        stats["response_rate"] = (
            alpha * actual_rate + (1 - alpha) * stats["response_rate"]
        )

        # Update response speed if we have timing data.
        if response_time_minutes is not None and responded:
            # Normalize: 5 min = 1.0, 60 min = 0.5, 480 min = 0.1
            speed = max(0.1, 1.0 - (response_time_minutes / 600))
            stats["response_speed"] = (
                alpha * speed + (1 - alpha) * stats["response_speed"]
            )

        self._stats[key] = stats

    def get_stats(
        self, employee_id: UUID, channel: ChannelType
    ) -> dict[str, float]:
        """Return current stats for an employee-channel pair."""
        key = (employee_id, channel)
        return dict(self._stats.get(key, {
            "response_rate": _DEFAULT_RESPONSE_RATES[channel],
            "response_speed": _DEFAULT_RESPONSE_SPEEDS[channel],
            "attempts": 0.0,
            "successes": 0.0,
        }))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _score_channel(
        self,
        employee: Employee,
        channel: ChannelType,
        severity: Severity,
        complexity: str,
    ) -> ChannelScore:
        """Compute the composite score for one channel."""
        key = (employee.id, channel)
        stats = self._stats.get(key)

        response_rate = (
            stats["response_rate"] if stats else _DEFAULT_RESPONSE_RATES[channel]
        )
        response_speed = (
            stats["response_speed"] if stats else _DEFAULT_RESPONSE_SPEEDS[channel]
        )

        preference = 1.0 if employee.preferred_channel == channel else 0.3
        urgency = _URGENCY_MATCH[channel].get(severity, 0.5)
        complexity_score = _COMPLEXITY_MATCH[channel].get(complexity, 0.5)

        composite = (
            response_rate * W_RESPONSE_RATE
            + response_speed * W_RESPONSE_SPEED
            + preference * W_PREFERENCE
            + urgency * W_URGENCY_MATCH
            + complexity_score * W_COMPLEXITY_MATCH
        )

        return ChannelScore(
            channel=channel,
            score=round(composite, 4),
            response_rate=response_rate,
            response_speed=response_speed,
            preference=preference,
            urgency_match=urgency,
            complexity_match=complexity_score,
        )
