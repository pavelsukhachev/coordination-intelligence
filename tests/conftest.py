"""Shared test fixtures for the Coordination Intelligence test suite."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from coordination_intelligence.models import (
    Blocker,
    BlockerStatus,
    BlockerType,
    ChannelType,
    CheckIn,
    Employee,
    Severity,
    Task,
)


@pytest.fixture
def alice() -> Employee:
    return Employee(name="Alice", role="Engineer", team="Backend", email="alice@acme.test")


@pytest.fixture
def bob() -> Employee:
    return Employee(
        name="Bob",
        role="Designer",
        team="Frontend",
        email="bob@acme.test",
        preferred_channel=ChannelType.EMAIL,
    )


@pytest.fixture
def charlie() -> Employee:
    return Employee(
        name="Charlie",
        role="Manager",
        team="Backend",
        email="charlie@acme.test",
        preferred_channel=ChannelType.SMS,
    )


@pytest.fixture
def simple_checkin(alice: Employee) -> CheckIn:
    return CheckIn(
        employee_id=alice.id,
        accomplished="Finished API endpoint.",
        working_on="Database migration.",
        blockers="Waiting on Bob for design specs.",
        needs_help=False,
        sentiment=0.6,
    )


@pytest.fixture
def blocked_checkin(alice: Employee) -> CheckIn:
    return CheckIn(
        employee_id=alice.id,
        accomplished="Nothing. Stuck on deployment.",
        working_on="Trying to fix the pipeline.",
        blockers="Build is broken. Need access to staging server. Critical deadline today.",
        needs_help=True,
        sentiment=0.1,
    )


@pytest.fixture
def clean_checkin(bob: Employee) -> CheckIn:
    return CheckIn(
        employee_id=bob.id,
        accomplished="Completed wireframes for dashboard.",
        working_on="Starting high-fidelity mockups.",
        blockers="",
        needs_help=False,
        sentiment=0.9,
    )


@pytest.fixture
def overdue_task(alice: Employee) -> Task:
    return Task(
        title="API Documentation",
        assignee_id=alice.id,
        due_date=datetime.now() - timedelta(days=5),
        completed=False,
    )


@pytest.fixture
def stalled_task(bob: Employee) -> Task:
    return Task(
        title="Design System Update",
        assignee_id=bob.id,
        stalled_since=datetime.now() - timedelta(days=7),
        completed=False,
    )


@pytest.fixture
def completed_task() -> Task:
    return Task(title="Setup CI", completed=True)


@pytest.fixture
def dependency_blocker(alice: Employee) -> Blocker:
    return Blocker(
        title="Waiting on design specs from Bob",
        description="Blocked by dependency on design team deliverable.",
        blocker_type=BlockerType.DEPENDENCY,
        severity=Severity.HIGH,
        status=BlockerStatus.CLASSIFIED,
        affected_employee_ids=[alice.id],
    )


@pytest.fixture
def technical_blocker(alice: Employee) -> Blocker:
    return Blocker(
        title="Build pipeline broken",
        description="CI/CD pipeline failing on test stage. Build error in deployment.",
        blocker_type=BlockerType.TECHNICAL,
        severity=Severity.CRITICAL,
        status=BlockerStatus.CLASSIFIED,
        affected_employee_ids=[alice.id],
    )


@pytest.fixture
def knowledge_blocker(bob: Employee) -> Blocker:
    return Blocker(
        title="Unclear how to use new API",
        description="Need guidance on the new authentication API. Documentation is missing.",
        blocker_type=BlockerType.KNOWLEDGE,
        severity=Severity.MEDIUM,
        status=BlockerStatus.CLASSIFIED,
        affected_employee_ids=[bob.id],
    )
