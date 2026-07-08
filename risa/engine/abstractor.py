from __future__ import annotations

from risa.core.models import Edge, Node
from risa.core.state import RisaState
from risa.engine.metabolism import reward_concept_cell, should_prune_or_sleep


def rebuild_concepts(state: RisaState, min_support: int = 2, min_actors: int = 2) -> None:
    state.concept_members = {}

    for pattern in state.patterns.values():
        if pattern.support < min_support or len(pattern.actors) < min_actors:
            continue

        action = next(iter(pattern.actions))
        effect = next(iter(pattern.effects))
        concept_id = f"concept:shared_{action}_{effect}"
        concept_label = f"shared_{action}_{effect}"
        state.graph.add_or_update_node(
            Node(
                id=concept_id,
                kind="concept",
                label=concept_label,
                attributes={"shared_action": action, "shared_effect": effect},
                abstraction_level=1,
                stability=min(1.0, float(pattern.support) / 5.0),
                recent_activity=min(5.0, float(pattern.support)),
                energy=min(1.0, 0.4 + (0.1 * min(pattern.support, 4))),
            )
        )
        state.concept_members[concept_id] = sorted(pattern.actors)
        values = state.activation_index.setdefault(f"concept:{concept_id}", [])
        if effect not in values:
            values.append(effect)

        action_id = f"process:{action}"
        effect_id = f"state:{effect}"
        state.graph.add_or_update_edge(
            Edge(source=concept_id, target=action_id, relation_type="participates_in", evidence_count=pattern.support)
        )
        state.graph.add_or_update_edge(
            Edge(source=concept_id, target=effect_id, relation_type="predicts", evidence_count=pattern.support)
        )

        for actor in pattern.actors:
            actor_id = f"entity:{actor}"
            state.graph.add_or_update_edge(
                Edge(source=actor_id, target=concept_id, relation_type="instance_of", evidence_count=pattern.support)
            )

        reward_concept_cell(state, concept_id, support=pattern.support, member_count=len(pattern.actors))

    _apply_concept_constraints(state)


def _apply_concept_constraints(state: RisaState) -> None:
    for node in state.graph.nodes_by_id.values():
        if node.kind != "concept":
            continue
        if should_prune_or_sleep(state, node.id):
            node.dormant = True
