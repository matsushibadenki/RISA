from __future__ import annotations

from bisect import bisect_right

from risa.core.models import Event
from risa.core.state import RisaState


def index_event_order(state: RisaState, event: Event) -> None:
    """Maintain a derived chronological index without persisting duplicate data."""
    event_key = (event.timestamp, event.id)
    if not state.event_order:
        state.event_order.append(event.id)
        return
    last = state.events_by_id[state.event_order[-1]]
    if event_key >= (last.timestamp, last.id):
        state.event_order.append(event.id)
        return
    position = bisect_right(
        state.event_order,
        event_key,
        key=lambda event_id: (
            state.events_by_id[event_id].timestamp,
            state.events_by_id[event_id].id,
        ),
    )
    state.event_order.insert(position, event.id)


def rebuild_event_order(state: RisaState) -> None:
    state.event_order = [
        event.id
        for event in sorted(
            state.events_by_id.values(), key=lambda item: (item.timestamp, item.id)
        )
    ]


def replay_event_window(
    state: RisaState,
    max_events: int | None,
) -> tuple[list[Event], int]:
    """Return chronological replay events and the number examined to select them."""
    if max_events is not None and max_events < 0:
        raise ValueError("max_events must be non-negative or None")
    if not _event_order_is_current(state):
        rebuild_event_order(state)
        selection_work = len(state.events_by_id)
    else:
        selection_work = len(state.event_order)
        if max_events is not None:
            selection_work = min(selection_work, max_events)
    event_ids = state.event_order
    if max_events is not None:
        event_ids = event_ids[-max_events:] if max_events else []
    return [state.events_by_id[event_id] for event_id in event_ids], selection_work


def _event_order_is_current(state: RisaState) -> bool:
    if len(state.event_order) != len(state.events_by_id):
        return False
    if not state.event_order:
        return True
    return (
        state.event_order[0] in state.events_by_id
        and state.event_order[-1] in state.events_by_id
    )
