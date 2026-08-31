from __future__ import annotations

from risa.core.models import Edge, Event, Node
from risa.core.state import RisaState
from risa.engine.metabolism import activate_nodes, reinforce_coactivation, reinforce_reproducible_relation


def normalize_label(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _node_id(kind: str, label: str) -> str:
    return f"{kind}:{normalize_label(label)}"


def ingest_event(state: RisaState, event: Event) -> None:
    state.events_by_id[event.id] = event

    actor_id = _node_id("entity", event.actor)
    action_id = _node_id("process", event.action)
    event_id = _node_id("event", event.id)
    coactive_node_ids = [actor_id, action_id]

    state.graph.add_or_update_node(
        Node(id=actor_id, kind="entity", label=normalize_label(event.actor), created_at=event.timestamp, usage_count=1)
    )
    state.graph.add_or_update_node(
        Node(id=action_id, kind="process", label=normalize_label(event.action), created_at=event.timestamp, usage_count=1)
    )
    state.graph.add_or_update_node(
        Node(
            id=event_id,
            kind="event",
            label=normalize_label(event.id),
            attributes={"actor": normalize_label(event.actor), "action": normalize_label(event.action)},
            created_at=event.timestamp,
            usage_count=1,
        )
    )
    state.graph.add_or_update_edge(
        Edge(
            source=actor_id,
            target=event_id,
            relation_type="participates_in_event",
            context_tags=tuple(sorted(event.context_tags)),
            evidence_count=1,
            last_updated=event.timestamp,
        )
    )

    for condition in event.preconditions:
        condition_id = _node_id("state", condition)
        coactive_node_ids.append(condition_id)
        state.graph.add_or_update_node(
            Node(id=condition_id, kind="state", label=normalize_label(condition), created_at=event.timestamp, usage_count=1)
        )
        state.graph.add_or_update_edge(
            Edge(
                source=event_id,
                target=condition_id,
                relation_type="has_precondition",
                context_tags=tuple(sorted(event.context_tags)),
                evidence_count=1,
                last_updated=event.timestamp,
            )
        )
        state.graph.add_or_update_edge(
            Edge(
                source=condition_id,
                target=action_id,
                relation_type="enables",
                context_tags=tuple(sorted(event.context_tags)),
                evidence_count=1,
                last_updated=event.timestamp,
            )
        )
        activate_nodes(state, [condition_id], event.timestamp)

    for consumed in event.consumed_states:
        consumed_id = _node_id("state", consumed)
        coactive_node_ids.append(consumed_id)
        state.graph.add_or_update_node(
            Node(
                id=consumed_id,
                kind="state",
                label=normalize_label(consumed),
                created_at=event.timestamp,
                usage_count=1,
            )
        )
        state.graph.add_or_update_edge(
            Edge(
                source=event_id,
                target=consumed_id,
                relation_type="consumes_state",
                context_tags=tuple(sorted(event.context_tags)),
                evidence_count=1,
                last_updated=event.timestamp,
            )
        )
        activate_nodes(state, [consumed_id], event.timestamp)

    for group, state_name in event.state_group_updates.items():
        group_id = _node_id("state_group", group)
        state_id = _node_id("state", state_name)
        state.graph.add_or_update_node(
            Node(
                id=group_id,
                kind="state_group",
                label=normalize_label(group),
                created_at=event.timestamp,
                usage_count=1,
            )
        )
        state.graph.add_or_update_node(
            Node(
                id=state_id,
                kind="state",
                label=normalize_label(state_name),
                created_at=event.timestamp,
                usage_count=1,
            )
        )
        state.graph.add_or_update_edge(
            Edge(
                source=event_id,
                target=group_id,
                relation_type="updates_state_group",
                context_tags=tuple(sorted(event.context_tags)),
                evidence_count=1,
                last_updated=event.timestamp,
            )
        )
        state.graph.add_or_update_edge(
            Edge(
                source=group_id,
                target=state_id,
                relation_type="allows_state",
                context_tags=tuple(sorted(event.context_tags)),
                evidence_count=1,
                last_updated=event.timestamp,
            )
        )

    for variable in sorted(set(event.numeric_preconditions) | set(event.state_variable_deltas)):
        variable_id = _node_id("state_variable", variable)
        spec = state.state_variable_specs.get(normalize_label(variable))
        attributes = {}
        if spec is not None:
            attributes = {
                "unit": spec.unit,
                "minimum": "" if spec.minimum is None else str(spec.minimum),
                "maximum": "" if spec.maximum is None else str(spec.maximum),
            }
        state.graph.add_or_update_node(
            Node(
                id=variable_id,
                kind="state_variable",
                label=normalize_label(variable),
                created_at=event.timestamp,
                usage_count=1,
                attributes=attributes,
            )
        )
        if variable in event.numeric_preconditions:
            state.graph.add_or_update_edge(
                Edge(
                    source=event_id,
                    target=variable_id,
                    relation_type="requires_state_variable",
                    context_tags=tuple(sorted(event.context_tags)),
                    evidence_count=1,
                    last_updated=event.timestamp,
                )
            )
        if variable in event.state_variable_deltas:
            state.graph.add_or_update_edge(
                Edge(
                    source=event_id,
                    target=variable_id,
                    relation_type="changes_state_variable",
                    context_tags=tuple(sorted(event.context_tags)),
                    evidence_count=1,
                    last_updated=event.timestamp,
                )
            )
    state.graph.add_or_update_edge(
        Edge(
            source=event_id,
            target=action_id,
            relation_type="instantiates",
            context_tags=tuple(sorted(event.context_tags)),
            evidence_count=1,
            last_updated=event.timestamp,
        )
    )
    state.graph.add_or_update_edge(
        Edge(
            source=actor_id,
            target=action_id,
            relation_type="participates_in",
            context_tags=tuple(sorted(event.context_tags)),
            evidence_count=1,
            last_updated=event.timestamp,
        )
    )

    if event.target:
        target_id = _node_id("entity", event.target)
        coactive_node_ids.append(target_id)
        state.graph.add_or_update_node(
            Node(id=target_id, kind="entity", label=normalize_label(event.target), created_at=event.timestamp, usage_count=1)
        )
        state.graph.add_or_update_edge(
            Edge(
                source=event_id,
                target=target_id,
                relation_type="acts_on",
                context_tags=tuple(sorted(event.context_tags)),
                evidence_count=1,
                last_updated=event.timestamp,
            )
        )

    activate_nodes(
        state,
        [actor_id, action_id, event_id] + ([target_id] if event.target else []),
        event.timestamp,
    )

    for effect in event.observed_effects:
        effect_id = _node_id("state", effect)
        coactive_node_ids.append(effect_id)
        state.graph.add_or_update_node(
            Node(id=effect_id, kind="state", label=normalize_label(effect), created_at=event.timestamp, usage_count=1)
        )
        state.graph.add_or_update_edge(
            Edge(
                source=event_id,
                target=effect_id,
                relation_type="results_in",
                context_tags=tuple(sorted(event.context_tags)),
                evidence_count=1,
                last_updated=event.timestamp,
            )
        )
        activate_nodes(state, [effect_id], event.timestamp)
        state.graph.add_or_update_edge(
            Edge(
                source=action_id,
                target=effect_id,
                relation_type="affects",
                context_tags=tuple(sorted(event.context_tags)),
                evidence_count=1,
                last_updated=event.timestamp,
            )
        )
        reinforce_reproducible_relation(
            state,
            source=action_id,
            target=effect_id,
            relation_type="affects",
            timestamp=event.timestamp,
        )

    reinforce_coactivation(state, coactive_node_ids, event.timestamp)
