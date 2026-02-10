"""Core data models for the Coordination Intelligence framework.

All models use Pydantic v2 BaseModel for validation and serialization.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BlockerType(str, Enum):
    """Five categories of organizational blockers."""

    DEPENDENCY = "dependency"
    RESOURCE = "resource"
    TECHNICAL = "technical"
    KNOWLEDGE = "knowledge"
    ORGANIZATIONAL = "organizational"


class Severity(str, Enum):
    """Blocker severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuthorityLevel(str, Enum):
    """Authority required to resolve a blocker."""

    IMMEDIATE = "immediate"  # Agent can resolve on its own
    STANDARD = "standard"  # Needs team-lead approval
    ELEVATED = "elevated"  # Needs director/exec approval


class ResolutionAction(str, Enum):
    """Actions the framework can take to resolve blockers."""

    NOTIFY = "notify"
    SCHEDULE_MEETING = "schedule_meeting"
    REASSIGN = "reassign"
    ESCALATE = "escalate"
    PROVIDE_INFO = "provide_info"
    CONNECT_PEERS = "connect_peers"


class BlockerStatus(str, Enum):
    """Lifecycle status of a blocker."""

    DETECTED = "detected"
    CLASSIFIED = "classified"
    ROUTED = "routed"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    STALE = "stale"


class ChannelType(str, Enum):
    """Communication channels."""

    SLACK = "slack"
    EMAIL = "email"
    SMS = "sms"


class CDIBenchmark(str, Enum):
    """Coordination Debt Index benchmark tiers."""

    ELITE = "elite"
    GOOD = "good"
    AVERAGE = "average"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class Employee(BaseModel):
    """Represents a team member in the organization."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    role: str = ""
    team: str = ""
    email: str = ""
    preferred_channel: ChannelType = ChannelType.SLACK
    timezone: str = "UTC"

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Employee):
            return NotImplemented
        return self.id == other.id


class Task(BaseModel):
    """Represents a work item that can be blocked."""

    id: UUID = Field(default_factory=uuid4)
    title: str
    assignee_id: UUID | None = None
    depends_on: list[UUID] = Field(default_factory=list)
    due_date: datetime | None = None
    completed: bool = False
    stalled_since: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CheckIn(BaseModel):
    """A structured check-in response from a team member."""

    employee_id: UUID
    timestamp: datetime = Field(default_factory=datetime.now)
    accomplished: str = ""
    working_on: str = ""
    blockers: str = ""
    needs_help: bool = False
    sentiment: float = 0.5  # 0.0 = frustrated, 1.0 = great


class Blocker(BaseModel):
    """A detected organizational blocker."""

    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str = ""
    blocker_type: BlockerType | None = None
    severity: Severity = Severity.MEDIUM
    status: BlockerStatus = BlockerStatus.DETECTED
    authority_level: AuthorityLevel = AuthorityLevel.STANDARD
    affected_employee_ids: list[UUID] = Field(default_factory=list)
    affected_task_ids: list[UUID] = Field(default_factory=list)
    source_check_in_id: UUID | None = None
    detected_at: datetime = Field(default_factory=datetime.now)
    resolved_at: datetime | None = None
    resolution_action: ResolutionAction | None = None
    resolution_notes: str = ""
    escalation_count: int = 0
    quiet_resolution: bool = False


class ResolutionPlan(BaseModel):
    """A plan for resolving a blocker."""

    blocker_id: UUID
    action: ResolutionAction
    authority_level: AuthorityLevel
    target_employee_ids: list[UUID] = Field(default_factory=list)
    channel: ChannelType = ChannelType.SLACK
    message: str = ""
    deadline: datetime | None = None
    alignment_score: float = 0.0  # 0.0-1.0 alignment with Company DNA
    fallback_action: ResolutionAction | None = None


class ChannelScore(BaseModel):
    """Scoring result for a communication channel."""

    channel: ChannelType
    score: float = 0.0
    response_rate: float = 0.0
    response_speed: float = 0.0
    preference: float = 0.0
    urgency_match: float = 0.0
    complexity_match: float = 0.0


class CDIMetrics(BaseModel):
    """Input metrics for Coordination Debt Index calculation."""

    meeting_hours_per_week: float = 0.0
    recurring_meeting_ratio: float = 0.0
    blocker_resolution_days: float = 0.0
    message_volume_per_day: float = 0.0
    task_delay_rate: float = 0.0
    handoff_time_hours: float = 0.0


class CDIResult(BaseModel):
    """Result of a CDI calculation."""

    score: float = 0.0
    benchmark: CDIBenchmark = CDIBenchmark.AVERAGE
    component_scores: dict[str, float] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)


class EscalationConfig(BaseModel):
    """Configuration for escalation timelines."""

    first_reminder: timedelta = Field(default=timedelta(hours=4))
    second_reminder: timedelta = Field(default=timedelta(hours=12))
    escalate_to_manager: timedelta = Field(default=timedelta(hours=24))
    escalate_to_director: timedelta = Field(default=timedelta(hours=48))


class ARLConfig(BaseModel):
    """Configuration for the Autonomous Resolution Loop."""

    escalation: EscalationConfig = Field(default_factory=EscalationConfig)
    max_retries: int = 3
    quiet_resolution_first: bool = True
    min_alignment_score: float = 0.6
