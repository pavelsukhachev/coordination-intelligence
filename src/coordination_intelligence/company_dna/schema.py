"""Pydantic models for Company DNA configuration.

Company DNA defines how an organization makes decisions, communicates,
and resolves conflicts. It is loaded from a YAML configuration file
and validated at startup.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class CoreValues(BaseModel):
    """Organization's core values that guide decision-making."""

    values: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)
    anti_patterns: list[str] = Field(default_factory=list)

    @field_validator("values", "priorities")
    @classmethod
    def at_least_one(cls, v: list[str]) -> list[str]:
        """Ensure at least one value is defined."""
        if not v:
            raise ValueError("At least one value is required.")
        return v


class DecisionPrinciple(BaseModel):
    """A principle that guides how decisions are made."""

    name: str
    description: str = ""
    weight: float = Field(default=1.0, ge=0.0, le=10.0)
    keywords: list[str] = Field(default_factory=list)


class AuthorityThreshold(BaseModel):
    """Defines when escalation is required."""

    immediate_max_severity: str = "medium"
    standard_max_severity: str = "high"
    require_approval_for: list[str] = Field(
        default_factory=lambda: ["reassign", "escalate"]
    )
    auto_escalate_after_hours: float = 24.0


class EscalationPath(BaseModel):
    """Defines the escalation chain."""

    levels: list[str] = Field(
        default_factory=lambda: ["team_lead", "manager", "director", "vp"]
    )
    skip_allowed: bool = False
    max_skip_levels: int = 1


class CommunicationStyle(BaseModel):
    """Organization's communication preferences."""

    tone: str = "professional"
    urgency_threshold_for_sms: str = "critical"
    prefer_async: bool = True
    meeting_as_last_resort: bool = True
    max_message_length: int = 500
    include_context: bool = True


class CompanyDNA(BaseModel):
    """Complete Company DNA configuration.

    Load from YAML with ``CompanyDNA.from_yaml(path)``.
    """

    name: str = "Default Organization"
    core_values: CoreValues = Field(
        default_factory=lambda: CoreValues(
            values=["transparency", "speed", "quality"],
            priorities=["unblock people", "ship fast", "learn always"],
        )
    )
    decision_principles: list[DecisionPrinciple] = Field(default_factory=list)
    authority: AuthorityThreshold = Field(default_factory=AuthorityThreshold)
    escalation: EscalationPath = Field(default_factory=EscalationPath)
    communication: CommunicationStyle = Field(default_factory=CommunicationStyle)

    @classmethod
    def from_yaml(cls, path: str | Path) -> CompanyDNA:
        """Load Company DNA from a YAML file.

        Args:
            path: Path to the YAML configuration file.

        Returns:
            A validated CompanyDNA instance.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the YAML is invalid.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Company DNA file not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Expected a YAML mapping, got {type(data).__name__}")

        return cls.model_validate(data)

    def to_yaml(self, path: str | Path) -> None:
        """Save Company DNA to a YAML file."""
        path = Path(path)
        data = self.model_dump()
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
