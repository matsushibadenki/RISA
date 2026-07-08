from __future__ import annotations

from risa.core.models import Event
from risa.core.state import RisaState
from risa.engine.abstractor import rebuild_concepts
from risa.engine.graph_builder import ingest_event
from risa.engine.learner import learn_from_event, link_temporal_precedence
from risa.engine.metabolism import decay_nodes


def train_events(state: RisaState, events: list[Event]) -> RisaState:
    previous_event: Event | None = None
    for event in sorted(events, key=lambda item: item.timestamp):
        decay_nodes(state, event.timestamp)
        ingest_event(state, event)
        learn_from_event(state, event)
        link_temporal_precedence(state, previous_event, event)
        previous_event = event
    rebuild_concepts(state)
    return state
