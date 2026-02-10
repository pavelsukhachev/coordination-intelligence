#!/usr/bin/env python3
"""Synthetic blocker scenarios for testing and demonstration.

Contains 20+ realistic but fully synthetic scenarios covering all
five blocker types at various severity levels. All names, companies,
and details are fictional.
"""

from datetime import datetime, timedelta
from uuid import uuid4

from coordination_intelligence import (
    Blocker,
    BlockerType,
    CheckIn,
    Employee,
    Severity,
    Task,
)


def create_employees() -> dict[str, Employee]:
    """Create a synthetic team of employees."""
    return {
        "alice": Employee(name="Alice", role="Backend Engineer", team="Platform"),
        "bob": Employee(name="Bob", role="Frontend Engineer", team="Product"),
        "charlie": Employee(name="Charlie", role="Engineering Manager", team="Platform"),
        "diana": Employee(name="Diana", role="DevOps Engineer", team="Infrastructure"),
        "eve": Employee(name="Eve", role="Data Scientist", team="ML"),
        "frank": Employee(name="Frank", role="QA Engineer", team="Quality"),
        "grace": Employee(name="Grace", role="Product Manager", team="Product"),
        "henry": Employee(name="Henry", role="Designer", team="Design"),
    }


def create_dependency_scenarios(employees: dict[str, Employee]) -> list[CheckIn]:
    """Scenarios where work is blocked by dependencies on others."""
    return [
        # Scenario 1: Waiting on API contract.
        CheckIn(
            employee_id=employees["bob"].id,
            accomplished="Completed login page mockup.",
            working_on="Dashboard data integration.",
            blockers="Waiting on Alice for REST API endpoint specs.",
            sentiment=0.4,
        ),
        # Scenario 2: Blocked by code review.
        CheckIn(
            employee_id=employees["alice"].id,
            accomplished="Finished payment module refactor.",
            working_on="Waiting for review.",
            blockers="PR pending review from Charlie for 3 days.",
            sentiment=0.3,
        ),
        # Scenario 3: Cross-team handoff.
        CheckIn(
            employee_id=employees["diana"].id,
            accomplished="Prepared deployment pipeline.",
            working_on="Staging environment setup.",
            blockers="Depends on ML team to provide model artifact. Handoff not complete.",
            sentiment=0.5,
        ),
        # Scenario 4: Upstream data dependency.
        CheckIn(
            employee_id=employees["eve"].id,
            accomplished="Built feature engineering pipeline.",
            working_on="Model training.",
            blockers="Waiting for data team to fix upstream data quality issues.",
            sentiment=0.4,
        ),
    ]


def create_resource_scenarios(employees: dict[str, Employee]) -> list[CheckIn]:
    """Scenarios where resources are insufficient."""
    return [
        # Scenario 5: No compute capacity.
        CheckIn(
            employee_id=employees["eve"].id,
            accomplished="Designed model architecture.",
            working_on="Training experiments.",
            blockers="No GPU capacity available. Server queue full. Need more resources.",
            sentiment=0.3,
        ),
        # Scenario 6: Team overloaded.
        CheckIn(
            employee_id=employees["frank"].id,
            accomplished="Tested login flow.",
            working_on="Regression suite.",
            blockers="Team has no bandwidth. Overloaded with 3 parallel releases.",
            sentiment=0.2,
        ),
        # Scenario 7: License expired.
        CheckIn(
            employee_id=employees["henry"].id,
            accomplished="Started design system audit.",
            working_on="Creating new components.",
            blockers="Design tool license expired. Access denied to shared library.",
            sentiment=0.4,
        ),
    ]


def create_technical_scenarios(employees: dict[str, Employee]) -> list[CheckIn]:
    """Scenarios with technical problems."""
    return [
        # Scenario 8: Build broken.
        CheckIn(
            employee_id=employees["alice"].id,
            accomplished="Started feature branch.",
            working_on="Integration tests.",
            blockers="CI/CD pipeline broken. Build error in test stage. Deploy failing.",
            needs_help=True,
            sentiment=0.2,
        ),
        # Scenario 9: Performance issue.
        CheckIn(
            employee_id=employees["bob"].id,
            accomplished="Completed dashboard charts.",
            working_on="Performance tuning.",
            blockers="Timeout on large queries. Memory leak in the data layer.",
            sentiment=0.3,
        ),
        # Scenario 10: API integration bug.
        CheckIn(
            employee_id=employees["diana"].id,
            accomplished="Updated deployment scripts.",
            working_on="Service mesh configuration.",
            blockers="Bug in the API gateway. Error 502 on all integration calls.",
            needs_help=True,
            sentiment=0.1,
        ),
        # Scenario 11: Test regression.
        CheckIn(
            employee_id=employees["frank"].id,
            accomplished="Added new test cases.",
            working_on="Fixing flaky tests.",
            blockers="Regression in payment module. 12 tests failing after merge.",
            sentiment=0.3,
        ),
    ]


def create_knowledge_scenarios(employees: dict[str, Employee]) -> list[CheckIn]:
    """Scenarios where knowledge gaps are the blocker."""
    return [
        # Scenario 12: New technology.
        CheckIn(
            employee_id=employees["bob"].id,
            accomplished="Read documentation.",
            working_on="Trying new framework.",
            blockers="Don't know how to configure the new state management library.",
            sentiment=0.4,
        ),
        # Scenario 13: Missing docs.
        CheckIn(
            employee_id=employees["alice"].id,
            accomplished="Started API migration.",
            working_on="Authentication module.",
            blockers="Documentation missing for internal auth service. Need guidance.",
            sentiment=0.5,
        ),
        # Scenario 14: Onboarding gap.
        CheckIn(
            employee_id=employees["eve"].id,
            accomplished="Set up local environment.",
            working_on="Understanding codebase.",
            blockers="Onboarding not complete. Unfamiliar with deployment process.",
            sentiment=0.4,
        ),
        # Scenario 15: Training needed.
        CheckIn(
            employee_id=employees["frank"].id,
            accomplished="Manual testing done.",
            working_on="Automation framework.",
            blockers="Need training on the new test automation tool. Learning curve is steep.",
            sentiment=0.5,
        ),
    ]


def create_organizational_scenarios(employees: dict[str, Employee]) -> list[CheckIn]:
    """Scenarios with organizational blockers."""
    return [
        # Scenario 16: Priority conflict.
        CheckIn(
            employee_id=employees["alice"].id,
            accomplished="Worked on feature A.",
            working_on="Trying to also handle feature B.",
            blockers="Conflicting priorities from product and engineering. Decision needed.",
            sentiment=0.3,
        ),
        # Scenario 17: Cross-team alignment.
        CheckIn(
            employee_id=employees["grace"].id,
            accomplished="Wrote product spec.",
            working_on="Getting stakeholder buy-in.",
            blockers="Cross-team alignment meeting keeps getting rescheduled.",
            sentiment=0.4,
        ),
        # Scenario 18: Approval chain.
        CheckIn(
            employee_id=employees["charlie"].id,
            accomplished="Prepared budget request.",
            working_on="Vendor evaluation.",
            blockers="Approval chain for new tooling is 3 levels deep. Process is slow.",
            sentiment=0.3,
        ),
        # Scenario 19: Communication breakdown.
        CheckIn(
            employee_id=employees["henry"].id,
            accomplished="Completed design review.",
            working_on="Updating based on feedback.",
            blockers="Communication gap between design and engineering. Schedule conflict.",
            sentiment=0.4,
        ),
        # Scenario 20: Re-org confusion.
        CheckIn(
            employee_id=employees["diana"].id,
            accomplished="Migrated infrastructure configs.",
            working_on="Setting up monitoring.",
            blockers="After re-org, unclear who owns the monitoring process now.",
            sentiment=0.3,
        ),
    ]


def create_overdue_tasks(employees: dict[str, Employee]) -> list[Task]:
    """Create overdue task scenarios."""
    now = datetime.now()
    return [
        # Scenario 21: Slightly overdue.
        Task(
            title="Update API docs",
            assignee_id=employees["alice"].id,
            due_date=now - timedelta(days=2),
        ),
        # Scenario 22: Severely overdue.
        Task(
            title="Security audit",
            assignee_id=employees["diana"].id,
            due_date=now - timedelta(days=14),
        ),
        # Scenario 23: Stalled task.
        Task(
            title="Performance benchmarks",
            assignee_id=employees["eve"].id,
            stalled_since=now - timedelta(days=10),
        ),
    ]


def get_all_scenarios() -> dict:
    """Return all synthetic scenarios organized by type.

    Returns a dictionary with keys:
    - employees: dict of Employee objects
    - checkins: list of all CheckIn scenarios
    - tasks: list of all Task scenarios
    - scenario_count: total number of scenarios
    """
    employees = create_employees()

    checkins = (
        create_dependency_scenarios(employees)
        + create_resource_scenarios(employees)
        + create_technical_scenarios(employees)
        + create_knowledge_scenarios(employees)
        + create_organizational_scenarios(employees)
    )

    tasks = create_overdue_tasks(employees)

    return {
        "employees": employees,
        "checkins": checkins,
        "tasks": tasks,
        "scenario_count": len(checkins) + len(tasks),
    }


if __name__ == "__main__":
    scenarios = get_all_scenarios()
    print(f"Created {scenarios['scenario_count']} synthetic scenarios:")
    print(f"  - {len(scenarios['checkins'])} check-in scenarios")
    print(f"  - {len(scenarios['tasks'])} task scenarios")
    print(f"  - {len(scenarios['employees'])} employees")

    # Run all scenarios through the ARL.
    from coordination_intelligence.arl import AutonomousResolutionLoop

    loop = AutonomousResolutionLoop()
    results = loop.run_cycle(
        checkins=scenarios["checkins"],
        tasks=scenarios["tasks"],
    )

    print(f"\nARL Results:")
    print(f"  Detected: {loop.metrics.total_detected}")
    print(f"  Resolved: {loop.metrics.total_resolved}")
    print(f"  Escalated: {loop.metrics.total_escalated}")
    print(f"  Resolution rate: {loop.metrics.summary()['resolution_rate']:.1%}")

    # Show blocker type distribution.
    from collections import Counter
    types = Counter(
        entry["blocker_type"]
        for entry in loop.learning_log
        if entry.get("blocker_type")
    )
    print(f"\nBlocker Type Distribution:")
    for btype, count in types.most_common():
        print(f"  {btype}: {count}")
