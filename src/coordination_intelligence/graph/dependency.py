"""Dependency graph using NetworkX DiGraph.

Models employees, tasks, and dependencies as nodes and edges in a
directed graph. Supports adding/removing entities and querying
relationships.
"""

from __future__ import annotations

from uuid import UUID

import networkx as nx

from coordination_intelligence.models import Blocker, Employee, Task


class DependencyGraph:
    """Organizational dependency graph.

    Nodes represent employees and tasks. Edges represent dependencies
    (task depends on task, employee assigned to task, blocker between
    entities).

    Node types are stored in the ``node_type`` attribute:
    - ``"employee"`` for Employee nodes
    - ``"task"`` for Task nodes

    Edge types are stored in the ``edge_type`` attribute:
    - ``"dependency"`` for task-to-task dependencies
    - ``"assignment"`` for employee-to-task assignments
    - ``"blocker"`` for blocker edges
    """

    def __init__(self) -> None:
        self._graph = nx.DiGraph()

    @property
    def graph(self) -> nx.DiGraph:
        """Return the underlying NetworkX DiGraph."""
        return self._graph

    @property
    def node_count(self) -> int:
        """Total number of nodes."""
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        """Total number of edges."""
        return self._graph.number_of_edges()

    # ------------------------------------------------------------------
    # Add / remove entities
    # ------------------------------------------------------------------

    def add_employee(self, employee: Employee) -> None:
        """Add an employee node to the graph."""
        self._graph.add_node(
            str(employee.id),
            node_type="employee",
            name=employee.name,
            role=employee.role,
            team=employee.team,
        )

    def add_task(self, task: Task) -> None:
        """Add a task node and its dependency edges."""
        self._graph.add_node(
            str(task.id),
            node_type="task",
            title=task.title,
            completed=task.completed,
        )

        # Add dependency edges.
        for dep_id in task.depends_on:
            dep_key = str(dep_id)
            if dep_key not in self._graph:
                # Create a placeholder node for the dependency.
                self._graph.add_node(dep_key, node_type="task", title="unknown")
            self._graph.add_edge(dep_key, str(task.id), edge_type="dependency")

        # Add assignment edge.
        if task.assignee_id:
            assignee_key = str(task.assignee_id)
            if assignee_key in self._graph:
                self._graph.add_edge(
                    assignee_key, str(task.id), edge_type="assignment"
                )

    def add_blocker(self, blocker: Blocker) -> None:
        """Add blocker edges between affected entities."""
        blocker_key = f"blocker:{blocker.id}"
        self._graph.add_node(
            blocker_key,
            node_type="blocker",
            title=blocker.title,
            severity=blocker.severity.value if blocker.severity else "medium",
        )

        for emp_id in blocker.affected_employee_ids:
            emp_key = str(emp_id)
            if emp_key in self._graph:
                self._graph.add_edge(blocker_key, emp_key, edge_type="blocker")

        for task_id in blocker.affected_task_ids:
            task_key = str(task_id)
            if task_key in self._graph:
                self._graph.add_edge(blocker_key, task_key, edge_type="blocker")

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all its edges."""
        if node_id in self._graph:
            self._graph.remove_node(node_id)

    def remove_employee(self, employee_id: UUID) -> None:
        """Remove an employee node."""
        self.remove_node(str(employee_id))

    def remove_task(self, task_id: UUID) -> None:
        """Remove a task node."""
        self.remove_node(str(task_id))

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_dependencies(self, task_id: UUID) -> list[str]:
        """Get IDs of tasks that a given task depends on (predecessors)."""
        key = str(task_id)
        if key not in self._graph:
            return []
        return [
            pred
            for pred in self._graph.predecessors(key)
            if self._graph.nodes[pred].get("node_type") == "task"
            and self._graph.edges[pred, key].get("edge_type") == "dependency"
        ]

    def get_dependents(self, task_id: UUID) -> list[str]:
        """Get IDs of tasks that depend on a given task (successors)."""
        key = str(task_id)
        if key not in self._graph:
            return []
        return [
            succ
            for succ in self._graph.successors(key)
            if self._graph.nodes[succ].get("node_type") == "task"
            and self._graph.edges[key, succ].get("edge_type") == "dependency"
        ]

    def get_employee_tasks(self, employee_id: UUID) -> list[str]:
        """Get task IDs assigned to an employee."""
        key = str(employee_id)
        if key not in self._graph:
            return []
        return [
            succ
            for succ in self._graph.successors(key)
            if self._graph.edges[key, succ].get("edge_type") == "assignment"
        ]

    def get_blockers_for(self, node_id: str) -> list[str]:
        """Get blocker node IDs affecting a given node."""
        if node_id not in self._graph:
            return []
        return [
            pred
            for pred in self._graph.predecessors(node_id)
            if self._graph.nodes[pred].get("node_type") == "blocker"
        ]

    def has_cycle(self) -> bool:
        """Check if the graph contains any cycles."""
        try:
            nx.find_cycle(self._graph)
            return True
        except nx.NetworkXNoCycle:
            return False

    def topological_order(self) -> list[str] | None:
        """Return nodes in topological order, or None if cycles exist."""
        if self.has_cycle():
            return None
        return list(nx.topological_sort(self._graph))
