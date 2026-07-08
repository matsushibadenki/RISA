from __future__ import annotations

from collections import defaultdict

from risa.core.models import Edge, Node


class GraphStore:
    def __init__(self) -> None:
        self.nodes_by_id: dict[str, Node] = {}
        self.edges_by_key: dict[tuple[str, str, str], Edge] = {}
        self.adjacency_out: dict[str, set[tuple[str, str]]] = defaultdict(set)
        self.adjacency_in: dict[str, set[tuple[str, str]]] = defaultdict(set)

    def add_or_update_node(self, node: Node) -> Node:
        existing = self.nodes_by_id.get(node.id)
        if existing is None:
            self.nodes_by_id[node.id] = node
            return node

        existing.usage_count += 1
        existing.stability = max(existing.stability, node.stability)
        if node.attributes:
            existing.attributes.update(node.attributes)
        return existing

    def add_or_update_edge(self, edge: Edge) -> Edge:
        key = (edge.source, edge.target, edge.relation_type)
        existing = self.edges_by_key.get(key)
        if existing is None:
            edge.evidence_count = max(edge.evidence_count, 1)
            self.edges_by_key[key] = edge
            self.adjacency_out[edge.source].add((edge.target, edge.relation_type))
            self.adjacency_in[edge.target].add((edge.source, edge.relation_type))
            return edge

        existing.evidence_count += max(edge.evidence_count, 1)
        existing.last_updated = max(existing.last_updated, edge.last_updated)
        existing.context_tags = tuple(sorted(set(existing.context_tags) | set(edge.context_tags)))
        return existing

    def get_node(self, node_id: str) -> Node | None:
        return self.nodes_by_id.get(node_id)

    def outgoing(self, node_id: str) -> list[Edge]:
        edges: list[Edge] = []
        for target, relation_type in self.adjacency_out.get(node_id, set()):
            edge = self.edges_by_key.get((node_id, target, relation_type))
            if edge is not None:
                edges.append(edge)
        return edges

    def to_dict(self) -> dict:
        return {
            "nodes": [node.to_dict() for node in self.nodes_by_id.values()],
            "edges": [edge.to_dict() for edge in self.edges_by_key.values()],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GraphStore":
        store = cls()
        for node_data in data.get("nodes", []):
            store.add_or_update_node(Node(**node_data))
        for edge_data in data.get("edges", []):
            edge_data = dict(edge_data)
            edge_data["context_tags"] = tuple(edge_data.get("context_tags", []))
            store.add_or_update_edge(Edge(**edge_data))
        return store

