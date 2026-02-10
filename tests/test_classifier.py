"""Tests for the BlockerClassifier."""

from __future__ import annotations

import pytest

from coordination_intelligence.arl.classifier import BlockerClassifier
from coordination_intelligence.models import (
    Blocker,
    BlockerStatus,
    BlockerType,
    Severity,
)


@pytest.fixture
def classifier() -> BlockerClassifier:
    return BlockerClassifier()


class TestBlockerClassifier:
    def test_dependency_classification(self, classifier):
        b = Blocker(title="Waiting on API from partner team", description="Blocked by upstream dependency")
        classifier.classify(b)
        assert b.blocker_type == BlockerType.DEPENDENCY
        assert b.status == BlockerStatus.CLASSIFIED

    def test_resource_classification(self, classifier):
        b = Blocker(title="No server capacity", description="Team is overloaded with no bandwidth")
        classifier.classify(b)
        assert b.blocker_type == BlockerType.RESOURCE

    def test_technical_classification(self, classifier):
        b = Blocker(title="Build broken", description="CI/CD pipeline failing with error in deploy stage")
        classifier.classify(b)
        assert b.blocker_type == BlockerType.TECHNICAL

    def test_knowledge_classification(self, classifier):
        b = Blocker(title="Don't know how to proceed", description="Unclear documentation for API")
        classifier.classify(b)
        assert b.blocker_type == BlockerType.KNOWLEDGE

    def test_organizational_classification(self, classifier):
        b = Blocker(title="Priority conflict", description="Conflicting priorities from stakeholders")
        classifier.classify(b)
        assert b.blocker_type == BlockerType.ORGANIZATIONAL

    def test_default_to_organizational(self, classifier):
        b = Blocker(title="Something vague", description="Not sure what is going on here")
        # "Not sure" matches KNOWLEDGE, so let's use truly vague text.
        b2 = Blocker(title="XYZ", description="ABC 123")
        classifier.classify(b2)
        assert b2.blocker_type == BlockerType.ORGANIZATIONAL

    def test_batch_classification(self, classifier):
        blockers = [
            Blocker(title="Waiting on review", description="Pending approval from team lead"),
            Blocker(title="Server down", description="Infrastructure crash in staging"),
            Blocker(title="Need training", description="Unfamiliar with new technology"),
        ]
        classifier.classify_batch(blockers)
        assert all(b.status == BlockerStatus.CLASSIFIED for b in blockers)
        assert all(b.blocker_type is not None for b in blockers)

    def test_confidence_for_strong_match(self, classifier):
        b = Blocker(
            title="Waiting on dependency from upstream team",
            description="Blocked by prerequisite. Pending review from partner.",
        )
        classifier.classify(b)
        conf = classifier.get_confidence(b)
        assert conf > 0.0

    def test_confidence_for_unclassified(self, classifier):
        b = Blocker(title="test")
        assert classifier.get_confidence(b) == 0.0

    def test_classification_log(self, classifier):
        b = Blocker(title="Build error", description="Pipeline broken")
        classifier.classify(b)
        assert len(classifier.classification_log) == 1
        log_entry = classifier.classification_log[0]
        assert log_entry["blocker_id"] == b.id
        assert log_entry["classified_as"] == b.blocker_type

    def test_multiple_keyword_hits(self, classifier):
        """When multiple types match, highest count wins."""
        b = Blocker(
            title="Waiting on deploy fix",
            description="Build broken. Error in CI/CD pipeline. Deploy failing. Test regression.",
        )
        classifier.classify(b)
        # TECHNICAL should win with more hits.
        assert b.blocker_type == BlockerType.TECHNICAL

    def test_dependency_keywords(self, classifier):
        tests = [
            "Waiting for response from design team",
            "This depends on the API refactor",
            "Blocked by the auth service changes",
            "Handoff from marketing not complete",
        ]
        for text in tests:
            b = Blocker(title=text)
            classifier.classify(b)
            assert b.blocker_type == BlockerType.DEPENDENCY, f"Failed for: {text}"

    def test_resource_keywords(self, classifier):
        tests = [
            "Team has no bandwidth for this",
            "Need license for the tool",
            "Access denied to production environment",
            "Budget not approved yet",
        ]
        for text in tests:
            b = Blocker(title=text)
            classifier.classify(b)
            assert b.blocker_type == BlockerType.RESOURCE, f"Failed for: {text}"

    def test_technical_keywords(self, classifier):
        tests = [
            "Bug in the payment module",
            "Performance timeout on large queries",
            "Memory leak in the worker process",
        ]
        for text in tests:
            b = Blocker(title=text)
            classifier.classify(b)
            assert b.blocker_type == BlockerType.TECHNICAL, f"Failed for: {text}"

    def test_knowledge_keywords(self, classifier):
        tests = [
            "Need guidance on architecture",
            "Documentation is missing for this feature",
            "Onboarding not complete for new hire",
        ]
        for text in tests:
            b = Blocker(title=text)
            classifier.classify(b)
            assert b.blocker_type == BlockerType.KNOWLEDGE, f"Failed for: {text}"
