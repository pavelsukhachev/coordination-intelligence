"""Blocker classification into five organizational categories.

The classifier uses keyword matching and pattern analysis to assign
each blocker one of five types. This classification drives the
resolution strategy chosen by the router.
"""

from __future__ import annotations

import re

from coordination_intelligence.models import Blocker, BlockerStatus, BlockerType

# Keyword sets for each blocker type, ordered by specificity.
_TYPE_KEYWORDS: dict[BlockerType, list[str]] = {
    BlockerType.DEPENDENCY: [
        "waiting on",
        "waiting for",
        "depends on",
        "dependent on",
        "dependency",
        "blocked by",
        "need.*from",
        "upstream",
        "downstream",
        "handoff",
        "prerequisite",
        "pending.*review",
        "pending.*approval",
    ],
    BlockerType.RESOURCE: [
        "resource",
        "bandwidth",
        "capacity",
        "overloaded",
        "too many",
        "no one available",
        "understaffed",
        "budget",
        "license",
        "access.*denied",
        "permission",
        "environment",
        "server",
        "infrastructure",
    ],
    BlockerType.TECHNICAL: [
        "bug",
        "error",
        "crash",
        "failing",
        "broken",
        "technical",
        "api",
        "integration",
        "performance",
        "timeout",
        "memory",
        "deploy",
        "build",
        "pipeline",
        "ci/cd",
        "test.*fail",
        "regression",
    ],
    BlockerType.KNOWLEDGE: [
        "don't know",
        "not sure",
        "unclear",
        "need.*guidance",
        "documentation",
        "how to",
        "training",
        "learning",
        "unfamiliar",
        "new.*technology",
        "knowledge",
        "expertise",
        "mentor",
        "onboarding",
    ],
    BlockerType.ORGANIZATIONAL: [
        "process",
        "policy",
        "approval.*chain",
        "bureaucracy",
        "re-?org",
        "priority.*conflict",
        "conflicting.*priorities",
        "alignment",
        "decision.*needed",
        "stakeholder",
        "cross.*team",
        "communication",
        "meeting",
        "schedule.*conflict",
    ],
}

# Pre-compile patterns for performance.
_TYPE_PATTERNS: dict[BlockerType, list[re.Pattern[str]]] = {
    btype: [re.compile(kw, re.IGNORECASE) for kw in keywords]
    for btype, keywords in _TYPE_KEYWORDS.items()
}


class BlockerClassifier:
    """Classifies blockers into one of five organizational categories.

    Uses keyword matching with confidence scoring. When multiple types
    match, the type with the highest number of keyword hits wins.
    """

    def __init__(self) -> None:
        self._classification_log: list[dict[str, object]] = []

    @property
    def classification_log(self) -> list[dict[str, object]]:
        """Return the log of all classifications performed."""
        return list(self._classification_log)

    def classify(self, blocker: Blocker) -> Blocker:
        """Classify a single blocker and update its type and status.

        Returns the same blocker object with ``blocker_type`` and
        ``status`` updated.
        """
        text = f"{blocker.title} {blocker.description}".strip()
        scores = self._score_types(text)

        if scores:
            best_type = max(scores, key=scores.get)  # type: ignore[arg-type]
            blocker.blocker_type = best_type
        else:
            # Default when no patterns match.
            blocker.blocker_type = BlockerType.ORGANIZATIONAL

        blocker.status = BlockerStatus.CLASSIFIED

        self._classification_log.append({
            "blocker_id": blocker.id,
            "classified_as": blocker.blocker_type,
            "scores": scores,
            "text_preview": text[:120],
        })

        return blocker

    def classify_batch(self, blockers: list[Blocker]) -> list[Blocker]:
        """Classify a batch of blockers. Returns the same list, mutated."""
        for blocker in blockers:
            self.classify(blocker)
        return blockers

    def get_confidence(self, blocker: Blocker) -> float:
        """Return a confidence score (0.0-1.0) for the current classification.

        Confidence is based on how many keywords matched the assigned
        type relative to the total keyword count for that type.
        """
        if not blocker.blocker_type:
            return 0.0

        text = f"{blocker.title} {blocker.description}".strip()
        patterns = _TYPE_PATTERNS.get(blocker.blocker_type, [])
        if not patterns:
            return 0.0

        hits = sum(1 for p in patterns if p.search(text))
        return min(hits / max(len(patterns) * 0.3, 1.0), 1.0)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _score_types(text: str) -> dict[BlockerType, int]:
        """Score each blocker type by counting keyword hits in text."""
        scores: dict[BlockerType, int] = {}
        for btype, patterns in _TYPE_PATTERNS.items():
            hits = sum(1 for p in patterns if p.search(text))
            if hits > 0:
                scores[btype] = hits
        return scores
