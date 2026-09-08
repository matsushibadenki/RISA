from __future__ import annotations

from risa.core.models import (
    ApplicabilityHypothesis,
    ChangeHypothesis,
    Edge,
    Event,
    Pattern,
    StructuralPattern,
    StructuralPrimitive,
    StructureDelta,
)
from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label
from risa.engine.evidence import index_event_evidence
from risa.engine.validator import validation_effect_support


def learn_from_event(state: RisaState, event: Event) -> None:
    index_event_evidence(state, event)
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
    target = normalize_label(event.target) if event.target else ""
    actor_target_effect_bucket = (
        state.actor_action_target_context_effect_counts.setdefault(
            _target_evidence_key(actor, action, target, context_key), {}
        )
        if target
        else None
    )
    target_effect_bucket = (
        state.action_target_context_effect_counts.setdefault(
            _target_evidence_key("*", action, target, context_key), {}
        )
        if target
        else None
    )
    target_role_effect_buckets = [
        state.action_target_role_context_effect_counts.setdefault(
            _target_evidence_key("role", action, normalize_label(role), context_key),
            {},
        )
        for role in sorted(set(event.target_roles))
    ]
    outcome_effects = sorted({normalize_label(effect) for effect in event.observed_effects})
    outcome_pattern_ids: set[str] = set()
    outcome_validation_scores: list[float] = []

    for effect_label in outcome_effects:
        effect_bucket[effect_label] = effect_bucket.get(effect_label, 0) + 1
        action_bucket[effect_label] = action_bucket.get(effect_label, 0) + 1
        context_effect_bucket[effect_label] = context_effect_bucket.get(effect_label, 0) + 1
        action_context_effect_bucket[effect_label] = action_context_effect_bucket.get(effect_label, 0) + 1
        if actor_target_effect_bucket is not None:
            actor_target_effect_bucket[effect_label] = actor_target_effect_bucket.get(effect_label, 0) + 1
        if target_effect_bucket is not None:
            target_effect_bucket[effect_label] = target_effect_bucket.get(effect_label, 0) + 1
        for role_bucket in target_role_effect_buckets:
            role_bucket[effect_label] = role_bucket.get(effect_label, 0) + 1

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
        outcome_pattern_ids.add(pattern_id)
        outcome_validation_scores.append(pattern.validation_score)
        _update_structural_pattern(
            state,
            actor=actor,
            action=action,
            effect=effect_label,
            context_key=context_key,
            pattern_id=pattern_id,
        )
        # Activation index narrows prediction to locally relevant effects and concepts.
        _index_append(state.activation_index, f"actor:{actor}", effect_label)
        _index_append(state.activation_index, f"action:{action}", effect_label)
        _index_append(state.activation_index, f"context:{context_key}", effect_label)
        _index_append(state.activation_index, f"actor_action:{actor}:{action}", effect_label)

    if outcome_effects:
        _update_structural_primitive(
            state,
            event_id=event.id,
            action=action,
            effects=outcome_effects,
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
            pattern_ids=outcome_pattern_ids,
            validation_score=(
                sum(outcome_validation_scores) / len(outcome_validation_scores)
                if outcome_validation_scores
                else 0.5
            ),
        )
        _update_change_hypothesis(state, event, outcome_effects, context_key)
    _refresh_applicability_hypotheses(state, action)


def _refresh_applicability_hypotheses(
    state: RisaState,
    action: str,
    minimum_successes: int = 2,
) -> None:
    relevant = [
        event
        for event in state.events_by_id.values()
        if normalize_label(event.action) == action
    ]
    failures = [
        event
        for event in relevant
        if not event.transition_succeeded and event.before_state_observed
    ]
    for primitive in state.structural_primitives.values():
        if f"process:{action}" not in primitive.input_conditions:
            continue
        successes = [
            event
            for event in relevant
            if event.transition_succeeded
            and {normalize_label(effect) for effect in event.observed_effects}
            == primitive.produced_states
            and event.before_state_observed
        ]
        old_learned = set(primitive.learned_state_conditions)
        primitive.input_state_conditions.difference_update(old_learned)
        if len(successes) < minimum_successes or not failures:
            primitive.learned_state_conditions.clear()
            state.applicability_hypotheses.pop(primitive.id, None)
            continue
        common_success = set.intersection(
            *(
                {f"state:{normalize_label(item)}" for item in event.observed_states_before}
                for event in successes
            )
        )
        failure_states = {
            f"state:{normalize_label(item)}"
            for event in failures
            for item in event.observed_states_before
        }
        learned = common_success - failure_states
        primitive.learned_state_conditions = learned
        primitive.input_state_conditions.update(learned)
        if learned:
            state.applicability_hypotheses[primitive.id] = ApplicabilityHypothesis(
                primitive_id=primitive.id,
                required_states=sorted(item.removeprefix("state:") for item in learned),
                supporting_event_ids=sorted(event.id for event in successes),
                counterexample_event_ids=sorted(event.id for event in failures),
            )
        else:
            state.applicability_hypotheses.pop(primitive.id, None)


def _update_change_hypothesis(
    state: RisaState,
    event: Event,
    outcome_effects: list[str],
    context_key: str,
    minimum_run: int = 3,
) -> None:
    action = normalize_label(event.action)
    target = normalize_label(event.target or "")
    relevant = [
        candidate
        for candidate in sorted(
            state.events_by_id.values(), key=lambda item: (item.timestamp, item.id)
        )
        if normalize_label(candidate.action) == action
        and normalize_label(candidate.target or "") == target
        and (
            "|".join(sorted(normalize_label(tag) for tag in candidate.context_tags))
            or "__no_context__"
        )
        == context_key
    ]
    if len(relevant) < minimum_run + 1:
        return
    current = tuple(outcome_effects)
    recent = relevant[-minimum_run:]
    if any(
        tuple(sorted({normalize_label(effect) for effect in item.observed_effects})) != current
        for item in recent
    ):
        return
    previous_event = relevant[-minimum_run - 1]
    previous = tuple(
        sorted({normalize_label(effect) for effect in previous_event.observed_effects})
    )
    if previous == current:
        return
    hypothesis_id = f"change:{action}:{target}:{context_key}"
    state.change_hypotheses[hypothesis_id] = ChangeHypothesis(
        id=hypothesis_id,
        action=action,
        target=target,
        context_key=context_key,
        previous_outcome=list(previous),
        current_outcome=list(current),
        detected_at=event.timestamp,
        evidence_event_ids=[item.id for item in recent],
        support=minimum_run,
    )


def _index_append(index: dict[str, list[str]], key: str, value: str) -> None:
    values = index.setdefault(key, [])
    if value not in values:
        values.append(value)


def _target_evidence_key(actor: str, action: str, target: str, context_key: str) -> str:
    return "\x1f".join((actor, action, target, context_key))


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
    effects: list[str],
    preconditions: list[str],
    consumed_states: list[str],
    state_group_updates: dict[str, str],
    numeric_preconditions: dict[str, float],
    state_variable_deltas: dict[str, float],
    context_key: str,
    pattern_ids: set[str],
    validation_score: float,
) -> None:
    role_signature = "entity->process->state"
    state_group_updates = {
        group: state_name
        for group, state_name in state_group_updates.items()
        if state_name in effects
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
    outcome_key = "+".join(sorted(effects))
    primitive_suffix = f"{action}->{outcome_key}" if not condition_key else f"{condition_key}::{action}->{outcome_key}"
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
            output_state=sorted(effects)[0],
            output_states=set(effects),
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
    primitive.output_states.update(effects)
    primitive.member_pattern_ids.update(pattern_ids)
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
