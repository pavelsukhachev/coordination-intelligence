"""Coordination Intelligence: Autonomous Agent Framework for Organizational Blocker Resolution.

This package implements the Autonomous Resolution Loop (ARL) framework
for detecting, classifying, routing, and resolving organizational blockers.

Reference implementation accompanying the TechRxiv paper:
"Coordination Intelligence: An Autonomous Agent Framework for
Organizational Blocker Resolution"
"""

__version__ = "0.1.0"

from coordination_intelligence.models import (
    ARLConfig,
    AuthorityLevel,
    Blocker,
    BlockerStatus,
    BlockerType,
    CDIBenchmark,
    CDIMetrics,
    CDIResult,
    ChannelScore,
    ChannelType,
    CheckIn,
    Employee,
    EscalationConfig,
    ResolutionAction,
    ResolutionPlan,
    Severity,
    Task,
)

__all__ = [
    "__version__",
    "ARLConfig",
    "AuthorityLevel",
    "Blocker",
    "BlockerStatus",
    "BlockerType",
    "CDIBenchmark",
    "CDIMetrics",
    "CDIResult",
    "ChannelScore",
    "ChannelType",
    "CheckIn",
    "Employee",
    "EscalationConfig",
    "ResolutionAction",
    "ResolutionPlan",
    "Severity",
    "Task",
]
