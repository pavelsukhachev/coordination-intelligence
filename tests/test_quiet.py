"""Tests for the QuietResolver."""

from __future__ import annotations

import pytest

from coordination_intelligence.models import (
    Blocker,
    BlockerStatus,
    BlockerType,
    Severity,
)
from coordination_intelligence.quiet.resolver import QuietResolver


@pytest.fixture
def resolver() -> QuietResolver:
    return QuietResolver()


@pytest.fixture
def resolver_with_kb() -> QuietResolver:
    """Resolver with a pre-populated knowledge base."""
    r = QuietResolver()
    r.add_knowledge(
        "deploy-guide",
        "How to Deploy",
        "Step 1: Run the build. Step 2: Push to staging. Step 3: Verify.",
        tags=["deploy", "build", "staging"],
    )
    r.add_knowledge(
        "api-auth",
        "API Authentication Guide",
        "Use OAuth2 with JWT tokens. See /docs/auth for details.",
        tags=["api", "auth", "jwt", "authentication"],
    )
    r.add_knowledge(
        "db-migration",
        "Database Migration Guide",
        "Run `alembic upgrade head` to migrate. Backup first.",
        tags=["database", "migration", "alembic"],
    )
    return r


class TestQuietResolver:
    def test_initial_state(self, resolver):
        assert resolver.quiet_resolution_rate == 0.0
        assert resolver.total_resolved == 0
        assert resolver.total_escalated == 0
        assert resolver.knowledge_count == 0

    def test_add_knowledge(self, resolver):
        resolver.add_knowledge("k1", "Title", "Content", tags=["tag1"])
        assert resolver.knowledge_count == 1

    def test_remove_knowledge(self, resolver):
        resolver.add_knowledge("k1", "Title", "Content")
        assert resolver.remove_knowledge("k1") is True
        assert resolver.knowledge_count == 0

    def test_remove_nonexistent_knowledge(self, resolver):
        assert resolver.remove_knowledge("nonexistent") is False

    def test_search_finds_match(self, resolver_with_kb):
        b = Blocker(
            title="Deploy broken",
            description="Build failing during deploy to staging",
        )
        matches = resolver_with_kb.search_knowledge_base(b)
        assert len(matches) > 0
        assert matches[0].title == "How to Deploy"

    def test_search_no_match(self, resolver_with_kb):
        b = Blocker(
            title="XYZ random problem",
            description="ZZZ completely unrelated issue",
        )
        matches = resolver_with_kb.search_knowledge_base(b)
        assert len(matches) == 0

    def test_search_relevance_ordering(self, resolver_with_kb):
        b = Blocker(
            title="API authentication failing",
            description="JWT tokens not working with OAuth2",
        )
        matches = resolver_with_kb.search_knowledge_base(b)
        assert len(matches) > 0
        # API auth guide should be most relevant.
        assert "Authentication" in matches[0].title or "auth" in matches[0].title.lower()

    def test_quiet_resolution_success(self, resolver_with_kb, alice):
        b = Blocker(
            title="Need help with deploy",
            description="How to deploy to staging?",
            affected_employee_ids=[alice.id],
        )
        result = resolver_with_kb.resolve_quietly(b)
        assert result is True
        assert b.status == BlockerStatus.RESOLVED
        assert b.quiet_resolution is True
        assert resolver_with_kb.total_resolved == 1

    def test_quiet_resolution_escalation(self, resolver, alice):
        """No knowledge base = quiet resolution fails and escalates."""
        b = Blocker(
            title="Unknown problem",
            description="Something we have never seen before",
            affected_employee_ids=[alice.id],
        )
        result = resolver.resolve_quietly(b)
        assert result is False
        assert b.status == BlockerStatus.ESCALATED
        assert b.escalation_count == 1
        assert resolver.total_escalated == 1

    def test_quiet_resolution_rate(self, resolver_with_kb, alice):
        # Resolve one quietly.
        b1 = Blocker(
            title="Deploy issue",
            description="Build problem in staging",
            affected_employee_ids=[alice.id],
        )
        resolver_with_kb.resolve_quietly(b1)

        # Escalate one.
        b2 = Blocker(
            title="XYZ unknown",
            description="ZZZ random failure",
            affected_employee_ids=[alice.id],
        )
        resolver_with_kb.resolve_quietly(b2)

        rate = resolver_with_kb.quiet_resolution_rate
        assert 0.0 < rate < 1.0

    def test_discreet_contact_needs_employees(self, resolver):
        b = Blocker(title="Test", affected_employee_ids=[])
        assert resolver.discreet_contact(b) is False

    def test_discreet_contact_with_employees(self, resolver, alice):
        b = Blocker(title="Test", affected_employee_ids=[alice.id])
        assert resolver.discreet_contact(b) is True

    def test_deliver_silently_needs_content(self, resolver):
        from coordination_intelligence.quiet.resolver import KnowledgeEntry
        b = Blocker(title="Test")
        empty_entry = KnowledgeEntry(id="e", title="Empty", content="")
        assert resolver.deliver_silently(b, empty_entry) is False

        full_entry = KnowledgeEntry(id="f", title="Full", content="Some content")
        assert resolver.deliver_silently(b, full_entry) is True

    def test_attempts_logged(self, resolver_with_kb, alice):
        b = Blocker(
            title="Deploy help needed",
            description="How to deploy staging build?",
            affected_employee_ids=[alice.id],
        )
        resolver_with_kb.resolve_quietly(b)
        assert len(resolver_with_kb.attempts) >= 3  # search + contact + deliver

    def test_escalation_attempts_logged(self, resolver, alice):
        b = Blocker(
            title="Unknown",
            description="ZZZ",
            affected_employee_ids=[alice.id],
        )
        resolver.resolve_quietly(b)
        assert len(resolver.attempts) >= 1
        assert any(a.step == "escalate" for a in resolver.attempts)

    def test_resolution_notes_set(self, resolver_with_kb, alice):
        b = Blocker(
            title="Database migration help",
            description="Need to run database migration",
            affected_employee_ids=[alice.id],
        )
        resolver_with_kb.resolve_quietly(b)
        assert b.resolution_notes != ""
        assert "Quietly resolved" in b.resolution_notes
