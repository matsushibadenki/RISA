from __future__ import annotations

from risa.core.models import Edge, Event, Pattern
from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label


def learn_from_event(state: RisaState, event: Event) -> None:
    actor = normalize_label(event.actor)
    action = normalize_label(event.action)
    context_key = "|".join(sorted(normalize_label(tag) for tag in event.context_tags)) or "__no_context__"

    actor_bucket = state.actor_action_effect_counts.setdefault(actor, {})
    effect_bucket = actor_bucket.setdefault(action, {})
    action_bucket = state.action_effect_counts.setdefault(action, {})
    actor_context_bucket = state.actor_action_context_effect_counts.setdefault(actor, {}).setdefault(action, {})
    context_effect_bucket = actor_context_bucket.setdefault(context_key, {})
    action_context_bucket = state.action_context_effect_counts.setdefault(action, {})
    action_context_effect_bucket = action_context_bucket.setdefault(context_key, {})

    for effect in event.observed_effects:
        effect_label = normalize_label(effect)
        effect_bucket[effect_label] = effect_bucket.get(effect_label, 0) + 1
        action_bucket[effect_label] = action_bucket.get(effect_label, 0) + 1
        context_effect_bucket[effect_label] = context_effect_bucket.get(effect_label, 0) + 1
        action_context_effect_bucket[effect_label] = action_context_effect_bucket.get(effect_label, 0) + 1

        pattern_id = f"pattern:{action}->{effect_label}"
        pattern = state.patterns.get(pattern_id)
        if pattern is None:
            pattern = Pattern(id=pattern_id, signature=f"{action}->{effect_label}")
            state.patterns[pattern_id] = pattern
        pattern.event_count += 1
        pattern.support += 1
        pattern.actors.add(actor)
        pattern.actions.add(action)
        pattern.effects.add(effect_label)
        pattern.context_tags.update(normalize_label(tag) for tag in event.context_tags)

        # Activation index narrows prediction to locally relevant effects and concepts.
        _index_append(state.activation_index, f"actor:{actor}", effect_label)
        _index_append(state.activation_index, f"action:{action}", effect_label)
        _index_append(state.activation_index, f"context:{context_key}", effect_label)
        _index_append(state.activation_index, f"actor_action:{actor}:{action}", effect_label)


def _index_append(index: dict[str, list[str]], key: str, value: str) -> None:
    values = index.setdefault(key, [])
    if value not in values:
        values.append(value)


def link_temporal_precedence(state: RisaState, previous_event: Event | None, current_event: Event) -> None:
    if previous_event is None:
        return

    previous_action = f"process:{normalize_label(previous_event.action)}"
    current_action = f"process:{normalize_label(current_event.action)}"
    state.graph.add_or_update_edge(
        Edge(
            source=previous_action,
            target=current_action,
            relation_type="precedes",
            context_tags=tuple(sorted(normalize_label(tag) for tag in current_event.context_tags)),
            evidence_count=1,
            last_updated=current_event.timestamp,
        )
    )
