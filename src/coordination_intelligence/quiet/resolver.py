"""Quiet resolution: invisible blocker handling.

The quiet resolution flow:
1. Search knowledge base for existing solutions.
2. Discreetly contact the right person (one-on-one, no public channels).
3. Deliver the solution silently to the blocked person.
4. Escalate only if quiet resolution fails.

The goal: solve problems before anyone notices they existed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from coordination_intelligence.models import Blocker, BlockerStatus


@dataclass
class KnowledgeEntry:
    """An entry in the knowledge base."""

    id: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    relevance_score: float = 0.0


@dataclass
class QuietResolutionAttempt:
    """Record of one quiet resolution attempt."""

    blocker_id: UUID
    step: str  # "search", "contact", "deliver", "escalate"
    success: bool
    details: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class QuietResolver:
    """Resolves blockers invisibly using a 4-step process.

    The resolver maintains a simple in-memory knowledge base and
    tracks quiet resolution attempts for metrics.

    Usage::

        resolver = QuietResolver()
        resolver.add_knowledge("deploy-guide", "How to Deploy", "Step 1: ...")
        result = resolver.resolve_quietly(blocker)
    """

    def __init__(self) -> None:
        self._knowledge_base: dict[str, KnowledgeEntry] = {}
        self._attempts: list[QuietResolutionAttempt] = []
        self._resolved_count: int = 0
        self._escalated_count: int = 0

    @property
    def quiet_resolution_rate(self) -> float:
        """Fraction of blockers resolved quietly (vs escalated)."""
        total = self._resolved_count + self._escalated_count
        if total == 0:
            return 0.0
        return self._resolved_count / total

    @property
    def attempts(self) -> list[QuietResolutionAttempt]:
        """Return all resolution attempts."""
        return list(self._attempts)

    @property
    def total_resolved(self) -> int:
        return self._resolved_count

    @property
    def total_escalated(self) -> int:
        return self._escalated_count

    # ------------------------------------------------------------------
    # Knowledge base management
    # ------------------------------------------------------------------

    def add_knowledge(
        self, entry_id: str, title: str, content: str, tags: list[str] | None = None
    ) -> None:
        """Add an entry to the knowledge base."""
        self._knowledge_base[entry_id] = KnowledgeEntry(
            id=entry_id,
            title=title,
            content=content,
            tags=tags or [],
        )

    def remove_knowledge(self, entry_id: str) -> bool:
        """Remove a knowledge base entry. Returns True if found."""
        return self._knowledge_base.pop(entry_id, None) is not None

    @property
    def knowledge_count(self) -> int:
        """Number of entries in the knowledge base."""
        return len(self._knowledge_base)

    # ------------------------------------------------------------------
    # Core resolution flow
    # ------------------------------------------------------------------

    def resolve_quietly(self, blocker: Blocker) -> bool:
        """Attempt to resolve a blocker quietly.

        Steps:
        1. Search knowledge base for relevant info.
        2. If found, attempt discreet contact.
        3. Deliver solution silently.
        4. If any step fails, escalate.

        Returns True if resolved quietly, False if escalated.
        """
        # Step 1: Search knowledge base.
        matches = self.search_knowledge_base(blocker)
        if matches:
            self._record("search", blocker.id, True, f"Found {len(matches)} match(es).")

            # Step 2: Discreet contact.
            contact_ok = self.discreet_contact(blocker)
            if contact_ok:
                self._record("contact", blocker.id, True, "Contacted discreetly.")

                # Step 3: Deliver silently.
                deliver_ok = self.deliver_silently(blocker, matches[0])
                if deliver_ok:
                    self._record("deliver", blocker.id, True, "Delivered solution.")
                    blocker.status = BlockerStatus.RESOLVED
                    blocker.quiet_resolution = True
                    blocker.resolved_at = datetime.now()
                    blocker.resolution_notes = f"Quietly resolved via: {matches[0].title}"
                    self._resolved_count += 1
                    return True

        # Step 4: Escalate if quiet resolution failed.
        self._record("search", blocker.id, False, "No match or delivery failed.")
        return self.escalate_if_failed(blocker)

    def search_knowledge_base(self, blocker: Blocker) -> list[KnowledgeEntry]:
        """Search the knowledge base for entries relevant to a blocker.

        Uses simple keyword matching against blocker title and
        description. Returns matches sorted by relevance.
        """
        query_words = set(
            f"{blocker.title} {blocker.description}".lower().split()
        )
        # Remove very common words.
        stop_words = {"the", "a", "an", "is", "are", "was", "to", "for", "on", "in", "of", "and"}
        query_words -= stop_words

        matches: list[KnowledgeEntry] = []
        for entry in self._knowledge_base.values():
            entry_words = set(
                f"{entry.title} {entry.content} {' '.join(entry.tags)}".lower().split()
            )
            overlap = query_words & entry_words
            if overlap:
                entry.relevance_score = len(overlap) / max(len(query_words), 1)
                matches.append(entry)

        matches.sort(key=lambda e: e.relevance_score, reverse=True)
        return matches

    def discreet_contact(self, blocker: Blocker) -> bool:
        """Simulate discreet one-on-one contact.

        In production, this would send a private DM or email.
        Returns True if contact was successful (simulated).
        """
        # Simulated: always succeeds if there are affected employees.
        return len(blocker.affected_employee_ids) > 0

    def deliver_silently(
        self, blocker: Blocker, entry: KnowledgeEntry
    ) -> bool:
        """Deliver a knowledge base solution to the blocked person.

        In production, this would compose a helpful message with
        links and context, delivered privately.
        """
        # Simulated: succeeds if the entry has content.
        return bool(entry.content.strip())

    def escalate_if_failed(self, blocker: Blocker) -> bool:
        """Escalate when quiet resolution fails.

        Returns False to indicate quiet resolution failed.
        """
        self._record("escalate", blocker.id, True, "Escalated after quiet resolution failed.")
        blocker.status = BlockerStatus.ESCALATED
        blocker.escalation_count += 1
        self._escalated_count += 1
        return False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _record(self, step: str, blocker_id: UUID, success: bool, details: str) -> None:
        """Record a resolution attempt step."""
        self._attempts.append(
            QuietResolutionAttempt(
                blocker_id=blocker_id,
                step=step,
                success=success,
                details=details,
            )
        )
