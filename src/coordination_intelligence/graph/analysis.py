"""Graph analysis algorithms for organizational insights.

Provides blast radius calculation, bottleneck identification,
cascade delay prediction, and critical path finding.
"""

from __future__ import annotations

from collections import deque

import networkx as nx

from coordination_intelligence.graph.dependency import DependencyGraph


class GraphAnalyzer:
    """Analyzes a DependencyGraph for organizational insights.

    All methods operate on the underlying NetworkX DiGraph.
    """

    def __init__(self, dep_graph: DependencyGraph) -> None:
        self.dep_graph = dep_graph

    @property
    def _g(self) -> nx.DiGraph:
        return self.dep_graph.graph

    def blast_radius(self, node_id: str) -> list[str]:
        """Calculate the blast radius of a blocker or node using BFS.

        Returns all nodes that would be transitively affected if this
        node is blocked. Includes direct and indirect dependents.
        """
        if node_id not in self._g:
            return []

        visited: set[str] = set()
        queue: deque[str] = deque([node_id])

        while queue:
            current = queue.popleft()
            for successor in self._g.successors(current):
                if successor not in visited:
                    visited.add(successor)
                    queue.append(successor)

        return sorted(visited)

    def identify_bottlenecks(self, top_n: int = 5) -> list[dict[str, object]]:
        """Identify bottleneck nodes using in-degree and betweenness centrality.

        A bottleneck is a node with high in-degree (many things depend
        on it) and high betweenness centrality (it sits on many shortest
        paths).

        Returns the top N bottlenecks sorted by composite score.
        """
        if self._g.number_of_nodes() == 0:
            return []

        in_degrees = dict(self._g.in_degree())
        betweenness = nx.betweenness_centrality(self._g)

        # Normalize in-degree to 0-1 range.
        max_in = max(in_degrees.values()) if in_degrees else 1
        if max_in == 0:
            max_in = 1

        results: list[dict[str, object]] = []
        for node_id in self._g.nodes():
            norm_in = in_degrees.get(node_id, 0) / max_in
            bc = betweenness.get(node_id, 0.0)

            # Composite: 60% in-degree + 40% betweenness.
            composite = 0.6 * norm_in + 0.4 * bc

            if composite > 0:
                results.append({
                    "node_id": node_id,
                    "node_type": self._g.nodes[node_id].get("node_type", "unknown"),
                    "name": self._g.nodes[node_id].get(
                        "name", self._g.nodes[node_id].get("title", node_id)
                    ),
                    "in_degree": in_degrees.get(node_id, 0),
                    "betweenness": round(bc, 4),
                    "composite_score": round(composite, 4),
                })

        results.sort(key=lambda x: x["composite_score"], reverse=True)  # type: ignore[arg-type]
        return results[:top_n]

    def predict_cascade_delay(
        self, blocked_node_id: str, delay_per_hop: float = 1.0
    ) -> dict[str, float]:
        """Predict cascade delays from a blocked node.

        Uses BFS to calculate the propagated delay to each downstream
        node. Each hop adds ``delay_per_hop`` days of delay.

        Returns a dict mapping node_id -> predicted delay in days.
        """
        if blocked_node_id not in self._g:
            return {}

        delays: dict[str, float] = {}
        queue: deque[tuple[str, float]] = deque([(blocked_node_id, 0.0)])
        visited: set[str] = {blocked_node_id}

        while queue:
            current, current_delay = queue.popleft()
            for successor in self._g.successors(current):
                if successor not in visited:
                    visited.add(successor)
                    new_delay = current_delay + delay_per_hop
                    delays[successor] = new_delay
                    queue.append((successor, new_delay))

        return delays

    def find_critical_path(self) -> list[str]:
        """Find the longest path in the DAG (critical path).

        The critical path is the sequence of dependent tasks that
        determines the minimum project duration.

        Returns an empty list if the graph has cycles.
        """
        if self.dep_graph.has_cycle():
            return []

        if self._g.number_of_nodes() == 0:
            return []

        return nx.dag_longest_path(self._g)

    def connected_components_count(self) -> int:
        """Count weakly connected components in the graph.

        More components = more isolated teams or workstreams.
        """
        return nx.number_weakly_connected_components(self._g)

    def isolation_score(self) -> float:
        """Calculate team isolation score (0.0 = fully connected, 1.0 = fully isolated).

        Based on the ratio of connected components to total nodes.
        """
        n = self._g.number_of_nodes()
        if n <= 1:
            return 0.0
        components = self.connected_components_count()
        return (components - 1) / (n - 1)

    def node_risk_scores(self) -> dict[str, float]:
        """Calculate risk score for each node based on centrality metrics.

        Higher risk = more dependencies flowing through this node.
        Risk is the average of normalized in-degree, out-degree,
        and betweenness centrality.
        """
        if self._g.number_of_nodes() == 0:
            return {}

        in_deg = dict(self._g.in_degree())
        out_deg = dict(self._g.out_degree())
        betweenness = nx.betweenness_centrality(self._g)

        max_in = max(in_deg.values()) if in_deg else 1
        max_out = max(out_deg.values()) if out_deg else 1
        if max_in == 0:
            max_in = 1
        if max_out == 0:
            max_out = 1

        risks: dict[str, float] = {}
        for node_id in self._g.nodes():
            norm_in = in_deg.get(node_id, 0) / max_in
            norm_out = out_deg.get(node_id, 0) / max_out
            bc = betweenness.get(node_id, 0.0)
            risks[node_id] = round((norm_in + norm_out + bc) / 3, 4)

        return risks
