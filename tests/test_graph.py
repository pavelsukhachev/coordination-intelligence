"""Tests for the dependency graph and analysis module."""

from __future__ import annotations

from uuid import uuid4

import pytest

from coordination_intelligence.graph.analysis import GraphAnalyzer
from coordination_intelligence.graph.dependency import DependencyGraph
from coordination_intelligence.models import (
    Blocker,
    BlockerType,
    Employee,
    Severity,
    Task,
)


@pytest.fixture
def graph() -> DependencyGraph:
    return DependencyGraph()


@pytest.fixture
def populated_graph(alice, bob, charlie) -> DependencyGraph:
    """A graph with employees and a chain of dependent tasks."""
    g = DependencyGraph()
    g.add_employee(alice)
    g.add_employee(bob)
    g.add_employee(charlie)

    # Create a task chain: t1 -> t2 -> t3
    t1 = Task(title="Setup DB", assignee_id=alice.id)
    t2 = Task(title="Build API", assignee_id=bob.id, depends_on=[t1.id])
    t3 = Task(title="Build UI", assignee_id=charlie.id, depends_on=[t2.id])

    g.add_task(t1)
    g.add_task(t2)
    g.add_task(t3)

    return g


class TestDependencyGraph:
    def test_empty_graph(self, graph):
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_add_employee(self, graph, alice):
        graph.add_employee(alice)
        assert graph.node_count == 1
        assert graph.graph.nodes[str(alice.id)]["node_type"] == "employee"

    def test_add_task(self, graph, alice):
        t = Task(title="Write tests", assignee_id=alice.id)
        graph.add_employee(alice)
        graph.add_task(t)
        assert graph.node_count == 2  # employee + task
        assert graph.edge_count == 1  # assignment edge

    def test_add_task_with_dependency(self, graph):
        t1 = Task(title="First")
        t2 = Task(title="Second", depends_on=[t1.id])
        graph.add_task(t1)
        graph.add_task(t2)
        deps = graph.get_dependencies(t2.id)
        assert str(t1.id) in deps

    def test_get_dependents(self, graph):
        t1 = Task(title="First")
        t2 = Task(title="Second", depends_on=[t1.id])
        graph.add_task(t1)
        graph.add_task(t2)
        dependents = graph.get_dependents(t1.id)
        assert str(t2.id) in dependents

    def test_get_employee_tasks(self, graph, alice):
        graph.add_employee(alice)
        t1 = Task(title="Task A", assignee_id=alice.id)
        t2 = Task(title="Task B", assignee_id=alice.id)
        graph.add_task(t1)
        graph.add_task(t2)
        tasks = graph.get_employee_tasks(alice.id)
        assert len(tasks) == 2

    def test_add_blocker(self, graph, alice):
        graph.add_employee(alice)
        b = Blocker(
            title="Server down",
            severity=Severity.HIGH,
            affected_employee_ids=[alice.id],
        )
        graph.add_blocker(b)
        blockers = graph.get_blockers_for(str(alice.id))
        assert len(blockers) == 1

    def test_remove_employee(self, graph, alice):
        graph.add_employee(alice)
        assert graph.node_count == 1
        graph.remove_employee(alice.id)
        assert graph.node_count == 0

    def test_remove_task(self, graph):
        t = Task(title="Test")
        graph.add_task(t)
        graph.remove_task(t.id)
        assert graph.node_count == 0

    def test_no_cycle_in_dag(self, populated_graph):
        assert populated_graph.has_cycle() is False

    def test_topological_order(self, populated_graph):
        order = populated_graph.topological_order()
        assert order is not None
        assert len(order) > 0

    def test_dependencies_for_unknown_task(self, graph):
        assert graph.get_dependencies(uuid4()) == []

    def test_dependents_for_unknown_task(self, graph):
        assert graph.get_dependents(uuid4()) == []

    def test_employee_tasks_for_unknown(self, graph):
        assert graph.get_employee_tasks(uuid4()) == []

    def test_blockers_for_unknown_node(self, graph):
        assert graph.get_blockers_for("nonexistent") == []


class TestGraphAnalyzer:
    def test_blast_radius_linear_chain(self, populated_graph):
        analyzer = GraphAnalyzer(populated_graph)
        # Find the first task node (Setup DB).
        task_nodes = [
            n for n, d in populated_graph.graph.nodes(data=True)
            if d.get("title") == "Setup DB"
        ]
        assert len(task_nodes) == 1
        radius = analyzer.blast_radius(task_nodes[0])
        # Should include the downstream tasks.
        assert len(radius) >= 2

    def test_blast_radius_leaf_node(self, populated_graph):
        analyzer = GraphAnalyzer(populated_graph)
        task_nodes = [
            n for n, d in populated_graph.graph.nodes(data=True)
            if d.get("title") == "Build UI"
        ]
        radius = analyzer.blast_radius(task_nodes[0])
        assert len(radius) == 0  # Leaf has no dependents.

    def test_blast_radius_unknown_node(self, populated_graph):
        analyzer = GraphAnalyzer(populated_graph)
        assert analyzer.blast_radius("nonexistent") == []

    def test_identify_bottlenecks(self, populated_graph):
        analyzer = GraphAnalyzer(populated_graph)
        bottlenecks = analyzer.identify_bottlenecks(top_n=3)
        assert isinstance(bottlenecks, list)
        for b in bottlenecks:
            assert "node_id" in b
            assert "composite_score" in b

    def test_bottlenecks_empty_graph(self):
        g = DependencyGraph()
        analyzer = GraphAnalyzer(g)
        assert analyzer.identify_bottlenecks() == []

    def test_predict_cascade_delay(self, populated_graph):
        analyzer = GraphAnalyzer(populated_graph)
        task_nodes = [
            n for n, d in populated_graph.graph.nodes(data=True)
            if d.get("title") == "Setup DB"
        ]
        delays = analyzer.predict_cascade_delay(task_nodes[0], delay_per_hop=2.0)
        assert len(delays) >= 2
        # Each hop adds 2 days.
        for node_id, delay in delays.items():
            assert delay >= 2.0

    def test_predict_cascade_unknown_node(self, populated_graph):
        analyzer = GraphAnalyzer(populated_graph)
        assert analyzer.predict_cascade_delay("nonexistent") == {}

    def test_find_critical_path(self, populated_graph):
        analyzer = GraphAnalyzer(populated_graph)
        path = analyzer.find_critical_path()
        assert len(path) >= 3  # At least 3 nodes in our chain.

    def test_critical_path_empty_graph(self):
        g = DependencyGraph()
        analyzer = GraphAnalyzer(g)
        assert analyzer.find_critical_path() == []

    def test_connected_components(self, populated_graph):
        analyzer = GraphAnalyzer(populated_graph)
        count = analyzer.connected_components_count()
        assert count >= 1

    def test_isolation_score_connected(self, populated_graph):
        analyzer = GraphAnalyzer(populated_graph)
        score = analyzer.isolation_score()
        assert 0.0 <= score <= 1.0

    def test_isolation_score_empty(self):
        g = DependencyGraph()
        analyzer = GraphAnalyzer(g)
        assert analyzer.isolation_score() == 0.0

    def test_node_risk_scores(self, populated_graph):
        analyzer = GraphAnalyzer(populated_graph)
        risks = analyzer.node_risk_scores()
        assert len(risks) > 0
        for score in risks.values():
            assert 0.0 <= score <= 1.0

    def test_node_risk_scores_empty(self):
        g = DependencyGraph()
        analyzer = GraphAnalyzer(g)
        assert analyzer.node_risk_scores() == {}
