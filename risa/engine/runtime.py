from __future__ import annotations

from risa.core.models import Event
from risa.core.state import RisaState
from risa.engine.abstractor import rebuild_concepts
from risa.engine.adaptation import execute_safe_adaptations
from risa.engine.graph_builder import ingest_event
from risa.engine.graph_builder import normalize_label
from risa.engine.learner import learn_from_event, link_temporal_precedence
from risa.engine.metabolism import decay_nodes
from risa.engine.replay import replay_structural_memory
from risa.engine.state_variables import merge_state_variable_specs
from risa.engine.validator import validate_event_prediction


def train_events(state: RisaState, events: list[Event]) -> RisaState:
    state.state_variable_specs = merge_state_variable_specs(state.state_variable_specs, events)
    incoming_ids = {event.id for event in events}
    existing_events = sorted(
        (event for event in state.events_by_id.values() if event.id not in incoming_ids),
        key=lambda item: (item.timestamp, item.id),
    )
    previous_global: Event | None = existing_events[-1] if existing_events else None
    previous_by_actor: dict[str, Event] = {}
    for event in existing_events:
        previous_by_actor[normalize_label(event.actor)] = event

    for event in sorted(events, key=lambda item: (item.timestamp, item.id)):
        decay_nodes(state, event.timestamp)
        validate_event_prediction(state, event)
        ingest_event(state, event)
        learn_from_event(state, event)
        actor = normalize_label(event.actor)
        link_temporal_precedence(state, previous_by_actor.get(actor), event, "precedes")
        link_temporal_precedence(state, previous_global, event, "globally_precedes")
        previous_by_actor[actor] = event
        previous_global = event
    rebuild_concepts(state)
    replay_structural_memory(state)
    execute_safe_adaptations(state)
    return state
