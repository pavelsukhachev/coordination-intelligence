#!/usr/bin/env python3
"""Basic usage of the Coordination Intelligence framework.

This example shows how to:
1. Create employees and tasks.
2. Run a check-in through the ARL.
3. View detected blockers and resolution results.
4. Calculate the CDI score.
"""

from datetime import datetime, timedelta

from coordination_intelligence import (
    CheckIn,
    Employee,
    Task,
)
from coordination_intelligence.arl import AutonomousResolutionLoop
from coordination_intelligence.cdi import CDIProxy
from coordination_intelligence.models import CDIMetrics


def main() -> None:
    # Create synthetic employees.
    alice = Employee(name="Alice", role="Backend Engineer", team="Platform")
    bob = Employee(name="Bob", role="Frontend Engineer", team="Product")
    charlie = Employee(name="Charlie", role="Engineering Manager", team="Platform")

    # Create tasks with dependencies.
    task_api = Task(title="Build REST API", assignee_id=alice.id)
    task_ui = Task(
        title="Build Dashboard UI",
        assignee_id=bob.id,
        depends_on=[task_api.id],
    )
    task_deploy = Task(
        title="Deploy to Staging",
        assignee_id=alice.id,
        due_date=datetime.now() - timedelta(days=2),  # Overdue!
    )

    # Simulate check-ins.
    alice_checkin = CheckIn(
        employee_id=alice.id,
        accomplished="Finished database schema design.",
        working_on="REST API implementation.",
        blockers="Waiting on Bob for API contract review.",
        needs_help=False,
        sentiment=0.5,
    )

    bob_checkin = CheckIn(
        employee_id=bob.id,
        accomplished="Completed wireframes.",
        working_on="Component library setup.",
        blockers="",
        needs_help=False,
        sentiment=0.8,
    )

    # Run the Autonomous Resolution Loop.
    print("=" * 60)
    print("Coordination Intelligence - Basic Usage Example")
    print("=" * 60)

    loop = AutonomousResolutionLoop()
    results = loop.run_cycle(
        checkins=[alice_checkin, bob_checkin],
        tasks=[task_api, task_ui, task_deploy],
    )

    print(f"\nDetected {loop.metrics.total_detected} blocker(s)")
    print(f"Resolved {loop.metrics.total_resolved} blocker(s)")
    print(f"Escalated {loop.metrics.total_escalated} blocker(s)")

    for i, result in enumerate(results, 1):
        status = "OK" if result.success else "FAIL"
        print(f"  [{status}] {result.message}")

    # Calculate CDI score.
    print("\n" + "-" * 60)
    print("Coordination Debt Index (CDI)")
    print("-" * 60)

    proxy = CDIProxy()
    cdi = proxy.calculate(CDIMetrics(
        meeting_hours_per_week=8.0,
        recurring_meeting_ratio=0.4,
        blocker_resolution_days=3.0,
        message_volume_per_day=80.0,
        task_delay_rate=0.15,
        handoff_time_hours=4.0,
    ))

    print(f"  Score: {cdi.score}")
    print(f"  Benchmark: {cdi.benchmark.value}")
    print("  Recommendations:")
    for rec in cdi.recommendations:
        print(f"    - {rec}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    main()
