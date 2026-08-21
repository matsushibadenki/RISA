from __future__ import annotations

from itertools import combinations

from risa.core.models import Edge
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
    validation_score: float = 0.5,
) -> None:
    node = state.graph.get_node(node_id)
    if node is None:
        return

    node.dormant = False
    node.recent_activity = min(10.0, node.recent_activity + min(3.0, support / 2.0))
    node.energy = min(
        1.0,
        node.energy + min(0.4, (support * 0.05) + (member_count * 0.03) + (validation_score * 0.08)),
    )
    node.stability = max(
        node.stability,
        min(1.0, ((support / max(member_count, 1)) / 2.0) * max(0.4, validation_score)),
    )


def reinforce_coactivation(
    state: RisaState,
    node_ids: list[str],
    timestamp: int,
    reliability_gain: float = 0.08,
    plasticity_decay: float = 0.03,
    bonus_energy_gain: float = 0.03,
    bonus_activity_gain: float = 0.2,
) -> None:
    unique_ids = sorted(set(node_ids))
    if len(unique_ids) < 2:
        return

    for left_id, right_id in combinations(unique_ids, 2):
        left_node = state.graph.get_node(left_id)
        right_node = state.graph.get_node(right_id)
        if left_node is None or right_node is None:
            continue

        edge = state.graph.add_or_update_edge(
            Edge(
                source=left_id,
                target=right_id,
                relation_type="co_activates_with",
                evidence_count=1,
                reliability=reliability_gain,
                plasticity=max(0.1, 1.0 - plasticity_decay),
                last_updated=timestamp,
            )
        )
        edge.reliability = min(1.0, edge.reliability + reliability_gain)
        edge.plasticity = max(0.1, edge.plasticity - plasticity_decay)
        edge.last_updated = timestamp

        _activate_node(
            left_node,
            timestamp,
            energy_gain=bonus_energy_gain,
            activity_gain=bonus_activity_gain,
        )
        _activate_node(
            right_node,
            timestamp,
            energy_gain=bonus_energy_gain,
            activity_gain=bonus_activity_gain,
        )


def apply_competition_inhibition(
    state: RisaState,
    action_id: str,
    losing_effect_id: str,
    winning_effect_ids: list[str],
    timestamp: int,
    reliability_penalty: float = 0.05,
    plasticity_rebound: float = 0.04,
    winner_reliability_gain: float = 0.03,
) -> None:
    losing_edge = _find_edge(state, action_id, losing_effect_id, "co_activates_with")
    if losing_edge is not None:
        losing_edge.reliability = max(0.0, losing_edge.reliability - reliability_penalty)
        losing_edge.plasticity = min(1.0, losing_edge.plasticity + plasticity_rebound)
        losing_edge.last_updated = timestamp

    for winning_effect_id in winning_effect_ids:
        winning_edge = _find_edge(state, action_id, winning_effect_id, "co_activates_with")
        if winning_edge is not None:
            winning_edge.reliability = min(1.0, winning_edge.reliability + winner_reliability_gain)
            winning_edge.plasticity = max(0.1, winning_edge.plasticity - (plasticity_rebound / 2.0))
            winning_edge.last_updated = timestamp


def reinforce_reproducible_relation(
    state: RisaState,
    source: str,
    target: str,
    relation_type: str,
    timestamp: int,
    reliability_gain: float = 0.025,
    plasticity_decay: float = 0.02,
) -> None:
    """Stabilize a directly observed relation without creating a new one."""
    edge = state.graph.edges_by_key.get((source, target, relation_type))
    if edge is None:
        return

    edge.reliability = min(1.0, edge.reliability + reliability_gain)
    edge.plasticity = max(0.1, edge.plasticity - plasticity_decay)
    edge.last_updated = timestamp


def apply_prediction_outcome_plasticity(
    state: RisaState,
    action_id: str,
    predicted_effect_id: str,
    matched: bool,
    timestamp: int,
    reliability_gain: float = 0.035,
    reliability_penalty: float = 0.04,
    plasticity_decay: float = 0.025,
    plasticity_rebound: float = 0.04,
) -> None:
    """Update an existing action-to-effect path from its predicted outcome."""
    edge = state.graph.edges_by_key.get((action_id, predicted_effect_id, "affects"))
    if edge is None:
        return

    if matched:
        edge.reliability = min(1.0, edge.reliability + reliability_gain)
        edge.plasticity = max(0.1, edge.plasticity - plasticity_decay)
    else:
        edge.reliability = max(0.0, edge.reliability - reliability_penalty)
        edge.plasticity = min(1.0, edge.plasticity + plasticity_rebound)
    edge.last_updated = timestamp


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


def _find_edge(
    state: RisaState,
    source: str,
    target: str,
    relation_type: str,
) -> Edge | None:
    return state.graph.edges_by_key.get((source, target, relation_type)) or state.graph.edges_by_key.get(
        (target, source, relation_type)
    )
