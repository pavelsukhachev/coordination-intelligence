"""Tests for Company DNA schema and decision engine."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from coordination_intelligence.company_dna.engine import AlignmentResult, DecisionEngine
from coordination_intelligence.company_dna.schema import (
    AuthorityThreshold,
    CommunicationStyle,
    CompanyDNA,
    CoreValues,
    DecisionPrinciple,
    EscalationPath,
)
from coordination_intelligence.models import (
    AuthorityLevel,
    Blocker,
    BlockerType,
    ChannelType,
    ResolutionAction,
    ResolutionPlan,
    Severity,
)


@pytest.fixture
def acme_dna() -> CompanyDNA:
    return CompanyDNA(
        name="Acme Corp",
        core_values=CoreValues(
            values=["transparency", "speed", "quality"],
            priorities=["unblock people", "ship fast", "learn always"],
            anti_patterns=["blame", "bureaucracy"],
        ),
        decision_principles=[
            DecisionPrinciple(
                name="speed_first",
                description="Prefer faster resolution paths.",
                weight=3.0,
                keywords=["fast", "quick", "immediate", "unblock"],
            ),
            DecisionPrinciple(
                name="people_first",
                description="Prioritize team member well-being.",
                weight=2.0,
                keywords=["help", "support", "assist", "team"],
            ),
        ],
        authority=AuthorityThreshold(
            immediate_max_severity="medium",
            standard_max_severity="high",
            require_approval_for=["reassign", "escalate"],
        ),
        escalation=EscalationPath(
            levels=["team_lead", "manager", "director"],
            skip_allowed=False,
        ),
        communication=CommunicationStyle(
            tone="professional",
            prefer_async=True,
            meeting_as_last_resort=True,
        ),
    )


@pytest.fixture
def acme_yaml(acme_dna: CompanyDNA) -> str:
    """Write Acme DNA to a temp YAML file and return the path."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    data = acme_dna.model_dump()
    yaml.dump(data, tmp, default_flow_style=False)
    tmp.close()
    return tmp.name


class TestCompanyDNASchema:
    def test_default_dna(self):
        dna = CompanyDNA()
        assert dna.name == "Default Organization"
        assert len(dna.core_values.values) > 0

    def test_custom_dna(self, acme_dna):
        assert acme_dna.name == "Acme Corp"
        assert "transparency" in acme_dna.core_values.values
        assert len(acme_dna.decision_principles) == 2

    def test_from_yaml(self, acme_yaml):
        dna = CompanyDNA.from_yaml(acme_yaml)
        assert dna.name == "Acme Corp"
        assert len(dna.core_values.values) == 3

    def test_from_yaml_missing_file(self):
        with pytest.raises(FileNotFoundError):
            CompanyDNA.from_yaml("/nonexistent/path.yaml")

    def test_from_yaml_invalid_content(self):
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        tmp.write("just a string, not a mapping")
        tmp.close()
        with pytest.raises(ValueError, match="Expected a YAML mapping"):
            CompanyDNA.from_yaml(tmp.name)

    def test_to_yaml_roundtrip(self, acme_dna):
        tmp = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False)
        tmp.close()
        acme_dna.to_yaml(tmp.name)
        loaded = CompanyDNA.from_yaml(tmp.name)
        assert loaded.name == acme_dna.name
        assert loaded.core_values.values == acme_dna.core_values.values

    def test_core_values_validation(self):
        with pytest.raises(ValueError, match="At least one value"):
            CoreValues(values=[], priorities=["test"])

    def test_decision_principle_weight_bounds(self):
        # Valid weights.
        p = DecisionPrinciple(name="test", weight=5.0)
        assert p.weight == 5.0

        # Out of bounds.
        with pytest.raises(Exception):
            DecisionPrinciple(name="test", weight=15.0)

    def test_escalation_path(self):
        ep = EscalationPath(levels=["lead", "manager", "vp"], skip_allowed=True, max_skip_levels=2)
        assert len(ep.levels) == 3
        assert ep.skip_allowed is True

    def test_communication_defaults(self):
        cs = CommunicationStyle()
        assert cs.tone == "professional"
        assert cs.max_message_length == 500


class TestDecisionEngine:
    def test_aligned_plan(self, acme_dna, dependency_blocker):
        engine = DecisionEngine(acme_dna)
        plan = ResolutionPlan(
            blocker_id=dependency_blocker.id,
            action=ResolutionAction.NOTIFY,
            authority_level=AuthorityLevel.IMMEDIATE,
            message="Quick help to unblock the team.",
        )
        result = engine.evaluate(plan, dependency_blocker)
        assert isinstance(result, AlignmentResult)
        assert result.score > 0.0
        assert len(result.reasons) > 0

    def test_authority_mismatch(self, acme_dna, technical_blocker):
        engine = DecisionEngine(acme_dna)
        # ESCALATE with IMMEDIATE authority should fail authority check.
        plan = ResolutionPlan(
            blocker_id=technical_blocker.id,
            action=ResolutionAction.ESCALATE,
            authority_level=AuthorityLevel.IMMEDIATE,
        )
        result = engine.evaluate(plan, technical_blocker)
        assert result.score < 0.5

    def test_anti_pattern_detected(self, acme_dna, alice):
        engine = DecisionEngine(acme_dna)
        b = Blocker(
            title="Blame the frontend team",
            description="It's their fault. Bureaucracy slowed us down.",
            affected_employee_ids=[alice.id],
        )
        plan = ResolutionPlan(
            blocker_id=b.id,
            action=ResolutionAction.NOTIFY,
            authority_level=AuthorityLevel.STANDARD,
        )
        result = engine.evaluate(plan, b)
        # Anti-pattern "blame" should reduce score.
        assert any("Anti-pattern" in r for r in result.reasons)

    def test_should_execute_true(self, acme_dna, dependency_blocker):
        engine = DecisionEngine(acme_dna, min_score=0.3)
        plan = ResolutionPlan(
            blocker_id=dependency_blocker.id,
            action=ResolutionAction.NOTIFY,
            authority_level=AuthorityLevel.STANDARD,
        )
        assert engine.should_execute(plan, dependency_blocker) is True

    def test_should_execute_false(self, acme_dna, technical_blocker):
        engine = DecisionEngine(acme_dna, min_score=0.95)
        plan = ResolutionPlan(
            blocker_id=technical_blocker.id,
            action=ResolutionAction.ESCALATE,
            authority_level=AuthorityLevel.IMMEDIATE,
        )
        assert engine.should_execute(plan, technical_blocker) is False

    def test_evaluation_log(self, acme_dna, dependency_blocker):
        engine = DecisionEngine(acme_dna)
        plan = ResolutionPlan(
            blocker_id=dependency_blocker.id,
            action=ResolutionAction.NOTIFY,
            authority_level=AuthorityLevel.STANDARD,
        )
        engine.evaluate(plan, dependency_blocker)
        assert len(engine.evaluation_log) == 1

    def test_meeting_as_last_resort(self, acme_dna, dependency_blocker):
        engine = DecisionEngine(acme_dna)
        plan = ResolutionPlan(
            blocker_id=dependency_blocker.id,
            action=ResolutionAction.SCHEDULE_MEETING,
            authority_level=AuthorityLevel.STANDARD,
        )
        result = engine.evaluate(plan, dependency_blocker)
        assert any("last resort" in r for r in result.reasons)

    def test_no_principles(self, dependency_blocker):
        dna = CompanyDNA(decision_principles=[])
        engine = DecisionEngine(dna)
        plan = ResolutionPlan(
            blocker_id=dependency_blocker.id,
            action=ResolutionAction.NOTIFY,
            authority_level=AuthorityLevel.STANDARD,
        )
        result = engine.evaluate(plan, dependency_blocker)
        assert any("No decision principles" in r for r in result.reasons)
