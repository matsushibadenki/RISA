"""Read-only diagnostics for distinct clean-Replay evidence by context."""

from __future__ import annotations

from risa.core.models import PredictionQuery
from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label
from risa.engine.predictor import predict_next_effect


def contextual_replay_errors(
    state: RisaState, *, max_events: int | None = None,
) -> dict[str, object]:
    """Score each selected Event once, without updating Replay or candidate state.

    This is a retrospective check on learned Events, not held-out accuracy.
    Counts are distinct evidence Events rather than cumulative Replay applications.
    """
    if max_events is not None and max_events < 0:
        raise ValueError("max_events must be non-negative or None")
    events = sorted(state.events_by_id.values(), key=lambda event: (event.timestamp, event.id))
    selected = events[-max_events:] if max_events else (events if max_events is None else [])
    groups: dict[tuple[str, str], dict[str, object]] = {}
    for event in selected:
        primitive_ids = state.event_primitive_ids.get(event.id, [])
        if not primitive_ids or not event.observed_effects:
            continue
        prediction = predict_next_effect(state, PredictionQuery(
            actor=event.actor, action=event.action, target=event.target,
            context_tags=list(event.context_tags),
            actor_roles=list(event.actor_roles),
            target_roles=list(event.target_roles),
            entity_bindings=dict(event.entity_bindings),
            entity_relations=list(event.entity_relations),
        ))
        correct = {
            normalize_label(effect) for effect in prediction.predicted_effects
        } == {normalize_label(effect) for effect in event.observed_effects}
        context = "|".join(sorted(normalize_label(tag) for tag in event.context_tags)) or "__no_context__"
        for primitive_id in set(primitive_ids):
            primitive = state.structural_primitives.get(primitive_id)
            if primitive is None:
                continue
            row = groups.setdefault((primitive_id, context), {
                "primitive_id": primitive_id, "context": context,
                "distinct_events": 0, "incorrect_events": 0,
                "incorrect_event_ids": [],
            })
            row["distinct_events"] += 1
            if not correct:
                row["incorrect_events"] += 1
                row["incorrect_event_ids"].append(event.id)
    rows = []
    for (primitive_id, _), row in sorted(groups.items()):
        primitive = state.structural_primitives[primitive_id]
        row["error_rate"] = row["incorrect_events"] / row["distinct_events"]
        row["cumulative_replay_count"] = primitive.replay_count
        row["cumulative_replay_score"] = primitive.replay_score
        rows.append(row)
    return {"selected_events": len(selected), "rows": rows}
