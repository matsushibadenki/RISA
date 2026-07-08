from __future__ import annotations

from risa.core.models import Edge, Event, Node
from risa.core.state import RisaState
from risa.engine.metabolism import activate_nodes


def normalize_label(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _node_id(kind: str, label: str) -> str:
    return f"{kind}:{normalize_label(label)}"


def ingest_event(state: RisaState, event: Event) -> None:
    state.events_by_id[event.id] = event

    actor_id = _node_id("entity", event.actor)
    action_id = _node_id("process", event.action)
    event_id = _node_id("event", event.id)

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
