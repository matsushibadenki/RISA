from __future__ import annotations

from risa.core.models import Node
from risa.core.state import RisaState


def activate_nodes(
    state: RisaState,
    node_ids: list[str],
    timestamp: int,
    energy_gain: float = 0.2,
    activity_gain: float = 1.0,
) -> None:
    for node_id in node_ids:
        node = state.graph.get_node(node_id)
        if node is None:
            continue
        _activate_node(node, timestamp, energy_gain=energy_gain, activity_gain=activity_gain)


def decay_nodes(
    state: RisaState,
    current_timestamp: int,
    decay_rate: float = 0.08,
    connection_cost_rate: float = 0.015,
    dormancy_energy_threshold: float = 0.12,
    dormancy_idle_threshold: int = 50,
) -> None:
    for node in state.graph.nodes_by_id.values():
        if node.last_activated_at == 0:
            idle_steps = max(0, current_timestamp - node.created_at)
        else:
            idle_steps = max(0, current_timestamp - node.last_activated_at)

        if idle_steps <= 0:
            continue

        connection_cost = _connection_cost(state, node.id, connection_cost_rate)
        node.recent_activity = max(0.0, node.recent_activity - (decay_rate * idle_steps))
        node.energy = max(0.0, node.energy - (((decay_rate / 2.0) + connection_cost) * idle_steps))

        if node.energy <= dormancy_energy_threshold and idle_steps >= dormancy_idle_threshold:
            node.dormant = True


def reward_concept_cell(
    state: RisaState,
    node_id: str,
    support: int,
    member_count: int,
) -> None:
    node = state.graph.get_node(node_id)
    if node is None:
        return

    node.dormant = False
    node.recent_activity = min(10.0, node.recent_activity + min(3.0, support / 2.0))
    node.energy = min(1.0, node.energy + min(0.4, (support * 0.05) + (member_count * 0.03)))
    node.stability = max(node.stability, min(1.0, (support / max(member_count, 1)) / 2.0))


def should_prune_or_sleep(
    state: RisaState,
    node_id: str,
    min_energy: float = 0.08,
    max_connection_budget: int = 8,
) -> bool:
    node = state.graph.get_node(node_id)
    if node is None:
        return False

    total_degree = state.graph.degree_in(node_id) + state.graph.degree_out(node_id)
    return node.energy <= min_energy and total_degree >= max_connection_budget


def _activate_node(
    node: Node,
    timestamp: int,
    energy_gain: float,
    activity_gain: float,
) -> None:
    node.dormant = False
    node.last_activated_at = timestamp
    node.recent_activity = min(10.0, node.recent_activity + activity_gain)
    node.energy = min(1.0, node.energy + energy_gain)
    node.stability = max(node.stability, min(1.0, node.energy))


def _connection_cost(state: RisaState, node_id: str, connection_cost_rate: float) -> float:
    total_degree = state.graph.degree_in(node_id) + state.graph.degree_out(node_id)
    return total_degree * connection_cost_rate
