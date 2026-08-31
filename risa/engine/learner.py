from __future__ import annotations

from risa.core.models import Edge, Event, Pattern, StructuralPattern, StructuralPrimitive, StructureDelta
from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label
from risa.engine.validator import validation_effect_support


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
        pattern.validation_score = validation_effect_support(
            state,
            actor=actor,
            action=action,
            context_key=context_key,
            effect=effect_label,
        )
        _update_structural_pattern(
            state,
            actor=actor,
            action=action,
            effect=effect_label,
            context_key=context_key,
            pattern_id=pattern_id,
        )
        _update_structural_primitive(
            state,
            event_id=event.id,
            action=action,
            effect=effect_label,
            preconditions=[normalize_label(condition) for condition in event.preconditions],
            consumed_states=[normalize_label(consumed) for consumed in event.consumed_states],
            state_group_updates={
                normalize_label(group): normalize_label(state_name)
                for group, state_name in event.state_group_updates.items()
            },
            numeric_preconditions={
                normalize_label(name): float(value)
                for name, value in event.numeric_preconditions.items()
            },
            state_variable_deltas={
                normalize_label(name): float(value)
                for name, value in event.state_variable_deltas.items()
            },
            context_key=context_key,
            pattern_id=pattern_id,
            validation_score=pattern.validation_score,
        )

        # Activation index narrows prediction to locally relevant effects and concepts.
        _index_append(state.activation_index, f"actor:{actor}", effect_label)
        _index_append(state.activation_index, f"action:{action}", effect_label)
        _index_append(state.activation_index, f"context:{context_key}", effect_label)
        _index_append(state.activation_index, f"actor_action:{actor}:{action}", effect_label)


def _index_append(index: dict[str, list[str]], key: str, value: str) -> None:
    values = index.setdefault(key, [])
    if value not in values:
        values.append(value)


def _update_structural_pattern(
    state: RisaState,
    actor: str,
    action: str,
    effect: str,
    context_key: str,
    pattern_id: str,
) -> None:
    role_signature = "entity->process->state"
    structural_id = f"structural:{role_signature}:{context_key}"
    structural_pattern = state.structural_patterns.get(structural_id)
    if structural_pattern is None:
        structural_pattern = StructuralPattern(
            id=structural_id,
            signature=structural_id,
            role_signature=role_signature,
        )
        state.structural_patterns[structural_id] = structural_pattern

    structural_pattern.support += 1
    structural_pattern.actors.add(actor)
    structural_pattern.actions.add(action)
    structural_pattern.effects.add(effect)
    structural_pattern.validation_score = validation_effect_support(
        state,
        actor=actor,
        action=action,
        context_key=context_key,
        effect=effect,
    )
    if context_key != "__no_context__":
        structural_pattern.context_tags.update(context_key.split("|"))
    structural_pattern.member_pattern_ids.add(pattern_id)
    _update_structure_deltas(state, structural_pattern)


def _update_structural_primitive(
    state: RisaState,
    event_id: str,
    action: str,
    effect: str,
    preconditions: list[str],
    consumed_states: list[str],
    state_group_updates: dict[str, str],
    numeric_preconditions: dict[str, float],
    state_variable_deltas: dict[str, float],
    context_key: str,
    pattern_id: str,
    validation_score: float,
) -> None:
    role_signature = "entity->process->state"
    state_group_updates = {
        group: state_name
        for group, state_name in state_group_updates.items()
        if state_name == effect
    }
    condition_key = "+".join(sorted(preconditions))
    consumed_key = "+".join(sorted(consumed_states))
    group_key = "+".join(
        f"{group}={state_name}" for group, state_name in sorted(state_group_updates.items())
    )
    numeric_key = "+".join(
        f"{name}>={value:g}" for name, value in sorted(numeric_preconditions.items())
    )
    delta_key = "+".join(
        f"{name}={value:+g}" for name, value in sorted(state_variable_deltas.items())
    )
    primitive_suffix = f"{action}->{effect}" if not condition_key else f"{condition_key}::{action}->{effect}"
    if consumed_key:
        primitive_suffix = f"{primitive_suffix}::consume:{consumed_key}"
    if group_key:
        primitive_suffix = f"{primitive_suffix}::groups:{group_key}"
    if numeric_key:
        primitive_suffix = f"{primitive_suffix}::require:{numeric_key}"
    if delta_key:
        primitive_suffix = f"{primitive_suffix}::delta:{delta_key}"
    primitive_id = f"primitive:transition:{role_signature}:{primitive_suffix}"
    primitive = state.structural_primitives.get(primitive_id)
    if primitive is None:
        primitive = StructuralPrimitive(
            id=primitive_id,
            relation_type="transition",
            role_signature=role_signature,
            input_conditions={f"process:{action}"},
            input_state_conditions={f"state:{condition}" for condition in preconditions},
            consumed_states={f"state:{consumed}" for consumed in consumed_states},
            state_group_updates=dict(state_group_updates),
            numeric_preconditions=dict(numeric_preconditions),
            state_variable_deltas=dict(state_variable_deltas),
            output_state=effect,
        )
        state.structural_primitives[primitive_id] = primitive

    if primitive.superseded_by:
        context_tags = set() if context_key == "__no_context__" else set(context_key.split("|"))
        variant = next(
            (
                state.structural_primitives.get(variant_id)
                for variant_id in sorted(primitive.superseded_by)
                if state.structural_primitives.get(variant_id) is not None
                and state.structural_primitives[variant_id].context_tags == context_tags
            ),
            None,
        )
        if variant is not None:
            primitive = variant
            primitive_id = variant.id

    primitive.support += 1
    primitive.validation_score = validation_score
    primitive.member_pattern_ids.add(pattern_id)
    primitive.input_state_conditions.update(f"state:{condition}" for condition in preconditions)
    primitive.consumed_states.update(f"state:{consumed}" for consumed in consumed_states)
    primitive.state_group_updates.update(state_group_updates)
    primitive.numeric_preconditions.update(numeric_preconditions)
    primitive.state_variable_deltas.update(state_variable_deltas)
    for group, state_name in state_group_updates.items():
        state.exclusive_state_groups.setdefault(group, set()).add(f"state:{state_name}")
    primitive.evidence_event_ids.add(event_id)
    if context_key != "__no_context__":
        primitive.context_tags.update(context_key.split("|"))
    refresh_primitive_adoption(primitive)
    _index_append(state.event_primitive_ids, event_id, primitive_id)


def refresh_primitive_adoption(primitive: StructuralPrimitive) -> None:
    evidence_count = len(primitive.evidence_event_ids)
    primitive.reuse_score = min(1.0, evidence_count / 3.0)
    # This is a small-data proxy, not a full Minimum Description Length calculation.
    primitive.compression_proxy = max(0.0, (evidence_count - 1) / (evidence_count + 1))
    primitive.adoption_score = (
        (0.30 * primitive.validation_score)
        + (0.25 * primitive.reuse_score)
        + (0.15 * primitive.compression_proxy)
        + (0.15 * primitive.replay_score)
        + (0.15 * primitive.deployment_replay_score)
    )
    primitive.adopted = (
        not primitive.superseded_by
        and evidence_count >= 2
        and primitive.adoption_score >= 0.55
    )


def _update_structure_deltas(state: RisaState, structural_pattern: StructuralPattern) -> None:
    for other_pattern in state.structural_patterns.values():
        if other_pattern.id == structural_pattern.id:
            continue
        if other_pattern.role_signature != structural_pattern.role_signature:
            continue

        delta = _build_structure_delta(other_pattern, structural_pattern)
        state.structure_deltas[delta.id] = delta


def _build_structure_delta(source: StructuralPattern, target: StructuralPattern) -> StructureDelta:
    operations: list[str] = []

    for action in sorted(target.actions - source.actions):
        operations.append(f"ADD_ACTION:{action}")
    for action in sorted(source.actions - target.actions):
        operations.append(f"REMOVE_ACTION:{action}")

    for effect in sorted(target.effects - source.effects):
        operations.append(f"ADD_EFFECT:{effect}")
    for effect in sorted(source.effects - target.effects):
        operations.append(f"REMOVE_EFFECT:{effect}")

    for context in sorted(target.context_tags - source.context_tags):
        operations.append(f"ADD_CONTEXT:{context}")
    for context in sorted(source.context_tags - target.context_tags):
        operations.append(f"REMOVE_CONTEXT:{context}")

    shared_support = min(source.support, target.support)
    delta_id = f"delta:{source.id}=>{target.id}"
    return StructureDelta(
        id=delta_id,
        source_pattern_id=source.id,
        target_pattern_id=target.id,
        role_signature=source.role_signature,
        operations=operations,
        support=shared_support,
        context_tags=set(source.context_tags) | set(target.context_tags),
    )


def link_temporal_precedence(
    state: RisaState,
    previous_event: Event | None,
    current_event: Event,
    relation_type: str = "precedes",
) -> None:
    if previous_event is None:
        return

    previous_action = f"process:{normalize_label(previous_event.action)}"
    current_action = f"process:{normalize_label(current_event.action)}"
    state.graph.add_or_update_edge(
        Edge(
            source=previous_action,
            target=current_action,
            relation_type=relation_type,
            context_tags=tuple(sorted(normalize_label(tag) for tag in current_event.context_tags)),
            evidence_count=1,
            last_updated=current_event.timestamp,
        )
    )
    previous_event_id = f"event:{normalize_label(previous_event.id)}"
    current_event_id = f"event:{normalize_label(current_event.id)}"
    state.graph.add_or_update_edge(
        Edge(
            source=previous_event_id,
            target=current_event_id,
            relation_type=f"event_{relation_type}",
            context_tags=tuple(sorted(normalize_label(tag) for tag in current_event.context_tags)),
            evidence_count=1,
            last_updated=current_event.timestamp,
        )
    )
