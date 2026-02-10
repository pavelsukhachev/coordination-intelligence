"""Blocker detection from check-ins, tasks, and organizational signals.

The BlockerDetector uses pattern matching against structured check-in
responses, overdue task analysis, and stalled item detection to surface
blockers that might otherwise go unnoticed.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from coordination_intelligence.models import (
    Blocker,
    BlockerStatus,
    CheckIn,
    Severity,
    Task,
)

# Patterns that indicate a blocker in free-text check-in responses.
_BLOCKER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bblocked\b", re.IGNORECASE),
    re.compile(r"\bwaiting\s+(on|for)\b", re.IGNORECASE),
    re.compile(r"\bneed\s+(help|access|approval|input|review)\b", re.IGNORECASE),
    re.compile(r"\bstuck\b", re.IGNORECASE),
    re.compile(r"\bcan'?t\s+(proceed|continue|move\s+forward)\b", re.IGNORECASE),
    re.compile(r"\bdepend(s|ing|ent)\s+on\b", re.IGNORECASE),
    re.compile(r"\bno\s+(response|reply|answer)\b", re.IGNORECASE),
    re.compile(r"\bescalat", re.IGNORECASE),
    re.compile(r"\bbottleneck\b", re.IGNORECASE),
    re.compile(r"\bdelayed?\b", re.IGNORECASE),
]

# Severity keywords used to estimate impact.
_SEVERITY_KEYWORDS: dict[Severity, list[str]] = {
    Severity.CRITICAL: ["critical", "urgent", "emergency", "showstopper", "deadline today"],
    Severity.HIGH: ["high priority", "important", "asap", "deadline tomorrow", "release blocker"],
    Severity.MEDIUM: ["medium", "soon", "this week"],
    Severity.LOW: ["low", "minor", "nice to have", "when possible"],
}


class BlockerDetector:
    """Detects blockers from multiple organizational signals.

    Signals include:
    - Check-in text analysis (pattern matching)
    - Overdue tasks (past due date and incomplete)
    - Stalled tasks (no progress for a configurable window)
    - Explicit help requests in check-ins
    """

    def __init__(
        self,
        stale_threshold: timedelta = timedelta(days=3),
        overdue_severity: Severity = Severity.HIGH,
    ) -> None:
        self.stale_threshold = stale_threshold
        self.overdue_severity = overdue_severity
        self._detected: list[Blocker] = []

    @property
    def detected_blockers(self) -> list[Blocker]:
        """Return all blockers detected so far."""
        return list(self._detected)

    def detect_from_checkin(self, checkin: CheckIn) -> list[Blocker]:
        """Analyze a check-in response for blocker signals.

        Returns a list of blockers found. May return zero, one, or
        multiple blockers from a single check-in.
        """
        blockers: list[Blocker] = []

        # Check the explicit blockers field first.
        if checkin.blockers and checkin.blockers.strip():
            blocker = Blocker(
                title=self._extract_title(checkin.blockers),
                description=checkin.blockers.strip(),
                severity=self._estimate_severity(checkin.blockers),
                status=BlockerStatus.DETECTED,
                affected_employee_ids=[checkin.employee_id],
                source_check_in_id=checkin.employee_id,
                detected_at=checkin.timestamp,
            )
            blockers.append(blocker)

        # Check the free-text fields for hidden blocker signals.
        for text in [checkin.accomplished, checkin.working_on]:
            if not text:
                continue
            for pattern in _BLOCKER_PATTERNS:
                if pattern.search(text):
                    blocker = Blocker(
                        title=self._extract_title(text),
                        description=f"Detected via pattern in check-in: {text.strip()}",
                        severity=self._estimate_severity(text),
                        status=BlockerStatus.DETECTED,
                        affected_employee_ids=[checkin.employee_id],
                        source_check_in_id=checkin.employee_id,
                        detected_at=checkin.timestamp,
                    )
                    blockers.append(blocker)
                    break  # One blocker per text field.

        # Explicit help request with low sentiment is a strong signal.
        if checkin.needs_help and checkin.sentiment < 0.3:
            blocker = Blocker(
                title="Help requested with low sentiment",
                description=(
                    f"Employee requested help. Sentiment: {checkin.sentiment:.2f}. "
                    f"Working on: {checkin.working_on}"
                ),
                severity=Severity.HIGH,
                status=BlockerStatus.DETECTED,
                affected_employee_ids=[checkin.employee_id],
                source_check_in_id=checkin.employee_id,
                detected_at=checkin.timestamp,
            )
            blockers.append(blocker)

        self._detected.extend(blockers)
        return blockers

    def detect_overdue_tasks(
        self,
        tasks: list[Task],
        now: datetime | None = None,
    ) -> list[Blocker]:
        """Find tasks past their due date that are not completed.

        Each overdue task generates a blocker.
        """
        now = now or datetime.now()
        blockers: list[Blocker] = []

        for task in tasks:
            if task.completed:
                continue
            if task.due_date and task.due_date < now:
                days_overdue = (now - task.due_date).days
                severity = Severity.CRITICAL if days_overdue > 7 else self.overdue_severity
                blocker = Blocker(
                    title=f"Overdue: {task.title}",
                    description=f"Task overdue by {days_overdue} day(s).",
                    severity=severity,
                    status=BlockerStatus.DETECTED,
                    affected_employee_ids=[task.assignee_id] if task.assignee_id else [],
                    affected_task_ids=[task.id],
                    detected_at=now,
                )
                blockers.append(blocker)

        self._detected.extend(blockers)
        return blockers

    def detect_stalled_tasks(
        self,
        tasks: list[Task],
        now: datetime | None = None,
    ) -> list[Blocker]:
        """Find tasks that have been stalled beyond the threshold.

        A task is stalled when its ``stalled_since`` timestamp is set
        and the duration exceeds ``self.stale_threshold``.
        """
        now = now or datetime.now()
        blockers: list[Blocker] = []

        for task in tasks:
            if task.completed:
                continue
            if task.stalled_since and (now - task.stalled_since) > self.stale_threshold:
                stalled_days = (now - task.stalled_since).days
                blocker = Blocker(
                    title=f"Stalled: {task.title}",
                    description=f"No progress for {stalled_days} day(s).",
                    severity=Severity.MEDIUM,
                    status=BlockerStatus.DETECTED,
                    affected_employee_ids=[task.assignee_id] if task.assignee_id else [],
                    affected_task_ids=[task.id],
                    detected_at=now,
                )
                blockers.append(blocker)

        self._detected.extend(blockers)
        return blockers

    def clear(self) -> None:
        """Reset detected blockers."""
        self._detected.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_title(text: str, max_len: int = 80) -> str:
        """Create a short title from the first sentence of a text block."""
        first_line = text.strip().split("\n")[0]
        first_sentence = re.split(r"[.!?]", first_line)[0].strip()
        if len(first_sentence) > max_len:
            return first_sentence[: max_len - 3] + "..."
        return first_sentence

    @staticmethod
    def _estimate_severity(text: str) -> Severity:
        """Estimate severity from keyword presence in text."""
        lower = text.lower()
        for severity, keywords in _SEVERITY_KEYWORDS.items():
            for kw in keywords:
                if kw in lower:
                    return severity
        return Severity.MEDIUM
