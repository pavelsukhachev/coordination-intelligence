# Coordination Intelligence

An autonomous agent framework for organizational blocker resolution.

This is the reference implementation for the paper:
*"Coordination Intelligence: An Autonomous Agent Framework for Organizational Blocker Resolution"*

## What It Does

Teams lose hours to blockers. Waiting on reviews. Stuck on access. Unclear priorities. This framework detects blockers, classifies them, and resolves them automatically.

The core innovation is the **Autonomous Resolution Loop (ARL)**:

```
DETECT -> CLASSIFY -> ROUTE -> ENGAGE -> COORDINATE -> RESOLVE -> VERIFY -> LEARN
```

Eight steps. One loop. Blockers resolved before they compound.

## Architecture

```
coordination-intelligence/
  src/coordination_intelligence/
    arl/              # Autonomous Resolution Loop (core)
      detector.py     # Detects blockers from check-ins and tasks
      classifier.py   # Classifies into 5 blocker types
      router.py       # Routes to resolution strategies
      resolver.py     # Executes resolution actions
      loop.py         # Orchestrates the 8-step cycle
    company_dna/      # Organizational configuration
      schema.py       # Pydantic models for Company DNA
      engine.py       # Decision engine (alignment scoring)
    channels/         # Communication channel selection
      selector.py     # ML-inspired multi-factor scoring
      adapters/       # Slack, Email, SMS adapters
    graph/            # Dependency analysis
      dependency.py   # NetworkX-based dependency graph
      analysis.py     # Blast radius, bottlenecks, critical path
    cdi/              # Coordination Debt Index
      proxy.py        # CDI calculator (0-100 score)
    quiet/            # Invisible resolution
      resolver.py     # Quiet resolution flow
    models.py         # Core data models (Pydantic)
```

## Five Blocker Types

| Type | Description | Example |
|------|------------|---------|
| **DEPENDENCY** | Waiting on another person or team | "Blocked by API review" |
| **RESOURCE** | Not enough capacity, licenses, access | "No GPU available" |
| **TECHNICAL** | Bugs, crashes, pipeline failures | "Build broken" |
| **KNOWLEDGE** | Missing docs, training, expertise | "Don't know how to use this" |
| **ORGANIZATIONAL** | Process, policy, priority conflicts | "Conflicting priorities" |

## Installation

```bash
pip install -e ".[dev]"
```

Requires Python 3.11+.

## Quick Start

```python
from coordination_intelligence import Employee, CheckIn, Task
from coordination_intelligence.arl import AutonomousResolutionLoop

# Create employees.
alice = Employee(name="Alice", role="Engineer", team="Backend")
bob = Employee(name="Bob", role="Designer", team="Frontend")

# Simulate a check-in.
checkin = CheckIn(
    employee_id=alice.id,
    accomplished="Finished API endpoint.",
    working_on="Database migration.",
    blockers="Waiting on Bob for design specs.",
)

# Run the ARL.
loop = AutonomousResolutionLoop()
results = loop.run_cycle(checkins=[checkin])

print(f"Detected: {loop.metrics.total_detected}")
print(f"Resolved: {loop.metrics.total_resolved}")
```

## CDI Score

The Coordination Debt Index (CDI) quantifies coordination overhead on a 0-100 scale.

```python
from coordination_intelligence.cdi import CDIProxy
from coordination_intelligence.models import CDIMetrics

proxy = CDIProxy()
result = proxy.calculate(CDIMetrics(
    meeting_hours_per_week=8.0,
    recurring_meeting_ratio=0.4,
    blocker_resolution_days=3.0,
    message_volume_per_day=80.0,
    task_delay_rate=0.15,
    handoff_time_hours=4.0,
))

print(f"CDI Score: {result.score}")      # e.g. 42.5
print(f"Benchmark: {result.benchmark}")  # e.g. AVERAGE
```

**Benchmarks:**

| Score | Tier | Meaning |
|-------|------|---------|
| 15-25 | Elite | Minimal coordination overhead |
| 26-40 | Good | Healthy coordination |
| 41-55 | Average | Room for improvement |
| 56-70 | High | Significant coordination tax |
| 71+ | Critical | Intervention needed |

## Company DNA

Configure the framework to match your organization's values, decision principles, and communication style. Load from YAML:

```python
from coordination_intelligence.company_dna import CompanyDNA, DecisionEngine

dna = CompanyDNA.from_yaml("examples/company_dna_config.yaml")
engine = DecisionEngine(dna)
```

The decision engine checks every resolution plan against your DNA. Actions that score below the alignment threshold are escalated instead of auto-executed.

## Dependency Graph

Model organizational dependencies. Find bottlenecks. Calculate blast radius.

```python
from coordination_intelligence.graph import DependencyGraph, GraphAnalyzer

graph = DependencyGraph()
graph.add_employee(alice)
graph.add_task(task)

analyzer = GraphAnalyzer(graph)
radius = analyzer.blast_radius(str(task.id))
bottlenecks = analyzer.identify_bottlenecks(top_n=5)
```

## Tests

```bash
pytest
```

97 tests. All pass.

## API Reference

### Core Models

- `Employee` - Team member with name, role, team, preferred channel
- `Task` - Work item with dependencies and due dates
- `CheckIn` - Structured check-in response
- `Blocker` - Detected organizational blocker
- `ResolutionPlan` - Plan for resolving a blocker

### ARL Classes

- `BlockerDetector` - Detects blockers from check-ins and tasks
- `BlockerClassifier` - Classifies blockers into 5 types
- `ResolutionRouter` - Routes to resolution strategies
- `ResolutionExecutor` - Executes resolution actions
- `AutonomousResolutionLoop` - Orchestrates the full cycle

### Supporting Modules

- `CompanyDNA` / `DecisionEngine` - Organizational alignment
- `ChannelSelector` - ML-inspired channel selection
- `DependencyGraph` / `GraphAnalyzer` - Dependency analysis
- `CDIProxy` - Coordination Debt Index calculator
- `QuietResolver` - Invisible resolution flow

## Citation

```bibtex
@software{sukhachev2026coordination,
  author = {Sukhachev, Pavel},
  title = {Coordination Intelligence: An Autonomous Agent Framework for Organizational Blocker Resolution},
  year = {2026},
  url = {https://github.com/pavelsukhachev/coordination-intelligence},
  version = {0.1.0}
}
```

## License

Apache 2.0. See [LICENSE](LICENSE).
