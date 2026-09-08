from __future__ import annotations

from collections import defaultdict
import hashlib

from risa.core.models import Event, UnnamedConceptCandidate
from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label


def discover_unnamed_candidates(state: RisaState) -> dict[str, UnnamedConceptCandidate]:
    """Propose cross-target schemas from primary Event evidence only."""
    previous_candidates = state.unnamed_concept_candidates
    groups: dict[tuple[str, str, tuple[str, ...]], list[Event]] = defaultdict(list)
    all_by_action_role: dict[tuple[str, str], list[Event]] = defaultdict(list)
    for event in state.events_by_id.values():
        if (
            not event.transition_succeeded
            or not event.target
            or not event.observed_effects
            or event.source.startswith(("derived:", "replay:"))
        ):
            continue
        action = normalize_label(event.action)
        outcome = tuple(sorted({normalize_label(item) for item in event.observed_effects}))
        for role in sorted({normalize_label(item) for item in event.target_roles}):
            groups[(action, role, outcome)].append(event)
            all_by_action_role[(action, role)].append(event)

    candidates: dict[str, UnnamedConceptCandidate] = {}
    for (action, role, outcome), events in sorted(groups.items()):
        targets = {normalize_label(event.target or "") for event in events}
        sources = {event.source for event in events}
        episodes = {event.episode_id for event in events}
        if len(targets) < 2 or len(sources) < 2 or len(episodes) < 2:
            continue
        signature = f"{action}|target_role:{role}|{'+'.join(outcome)}"
        candidate_id = f"candidate:{hashlib.sha256(signature.encode()).hexdigest()[:16]}"
        counterexamples = [
            event
            for event in all_by_action_role[(action, role)]
            if tuple(sorted({normalize_label(item) for item in event.observed_effects})) != outcome
        ]
        concrete_length = sum(
            len(action)
            + len(normalize_label(event.target or ""))
            + len(role)
            + sum(len(effect) for effect in outcome)
            for event in events
        )
        schema_length = (
            len(action)
            + len(role)
            + sum(len(effect) for effect in outcome)
            + sum(len(target) for target in targets)
        )
        candidate = UnnamedConceptCandidate(
            id=candidate_id,
            structural_schema={
                "action": action,
                "target_role": role,
                "effects": list(outcome),
            },
            typed_role_variables={"target": role},
            supporting_event_ids=sorted(event.id for event in events),
            counterexample_event_ids=sorted(event.id for event in counterexamples),
            source_diversity=len(sources),
            episode_diversity=len(episodes),
            actor_diversity=len({normalize_label(event.actor) for event in events}),
            target_diversity=len(targets),
            context_diversity=len(
                {tuple(sorted(normalize_label(tag) for tag in event.context_tags)) for event in events}
            ),
            description_length_delta=concrete_length - schema_length,
            reconstruction_gain=round(len(events) / (len(events) + len(counterexamples)), 6),
            exception_cost=len(counterexamples),
        )
        _restore_unchanged_evaluation(candidate, previous_candidates.get(candidate_id))
        candidates[candidate_id] = candidate

    candidates.update(_discover_temporal_sequence_candidates(state, previous_candidates))
    state.unnamed_concept_candidates = candidates
    rebuild_candidate_inference_index(state)
    return candidates


def rebuild_candidate_inference_index(state: RisaState) -> None:
    """Rebuild the derived index; source Events and persisted graph stay unchanged."""
    state.candidate_inference_index.clear()
    for candidate in state.unnamed_concept_candidates.values():
        if candidate.lifecycle_status != "adopted":
            continue
        kind = str(candidate.structural_schema.get("kind", "single_transition"))
        if kind == "temporal_sequence":
            steps = candidate.structural_schema.get("steps", [])
            goal_effects = candidate.structural_schema.get("goal_effects", [])
            role = normalize_label(
                str(candidate.structural_schema.get("target_role", ""))
            )
            actor_role = normalize_label(
                str(candidate.structural_schema.get("actor_role", ""))
            )
            if not isinstance(steps, list) or not steps or not role:
                continue
            first_step = steps[0]
            if not isinstance(first_step, dict):
                continue
            start_action = normalize_label(str(first_step.get("action", "")))
            indexed_goal_effects = goal_effects if isinstance(goal_effects, list) else []
            for goal_effect in indexed_goal_effects:
                goal = normalize_label(str(goal_effect))
                if start_action and goal:
                    role_key = (
                        f"plan_start:{start_action}:goal:{goal}:target_role:{role}"
                    )
                    if actor_role:
                        role_key += f":actor_role:{actor_role}"
                    _add_candidate_index(
                        state,
                        role_key,
                        candidate.id,
                    )
                    _add_candidate_index(
                        state,
                        f"plan_start:{start_action}:goal:{goal}",
                        candidate.id,
                    )
            continue
        action = normalize_label(str(candidate.structural_schema.get("action", "")))
        role = normalize_label(str(candidate.structural_schema.get("target_role", "")))
        if not action or not role:
            continue
        key = f"action:{action}:target_role:{role}"
        _add_candidate_index(state, key, candidate.id)


def matching_adopted_candidates(
    state: RisaState,
    action: str,
    target_roles: list[str] | set[str] | tuple[str, ...],
) -> list[UnnamedConceptCandidate]:
    candidate_ids: set[str] = set()
    normalized_action = normalize_label(action)
    for role in target_roles:
        key = f"action:{normalized_action}:target_role:{normalize_label(role)}"
        candidate_ids.update(state.candidate_inference_index.get(key, []))
    return [
        state.unnamed_concept_candidates[candidate_id]
        for candidate_id in sorted(candidate_ids)
        if candidate_id in state.unnamed_concept_candidates
        and state.unnamed_concept_candidates[candidate_id].lifecycle_status == "adopted"
    ]


def matching_adopted_plan_candidates(
    state: RisaState,
    start_action: str,
    target_effect: str,
    target_roles: list[str] | set[str] | tuple[str, ...],
    actor_roles: list[str] | set[str] | tuple[str, ...] = (),
) -> list[UnnamedConceptCandidate]:
    """Return adopted temporal schemas matching a role-bound plan query."""
    candidate_ids: set[str] = set()
    normalized_action = normalize_label(start_action)
    normalized_effect = normalize_label(target_effect)
    for role in target_roles:
        target_key = (
            f"plan_start:{normalized_action}:goal:{normalized_effect}:"
            f"target_role:{normalize_label(role)}"
        )
        candidate_ids.update(state.candidate_inference_index.get(target_key, []))
        for actor_role in actor_roles:
            key = f"{target_key}:actor_role:{normalize_label(actor_role)}"
            candidate_ids.update(state.candidate_inference_index.get(key, []))
    return [
        state.unnamed_concept_candidates[candidate_id]
        for candidate_id in sorted(candidate_ids)
        if candidate_id in state.unnamed_concept_candidates
        and state.unnamed_concept_candidates[candidate_id].lifecycle_status == "adopted"
        and state.unnamed_concept_candidates[candidate_id].structural_schema.get("kind")
        == "temporal_sequence"
    ]


def has_adopted_plan_candidate_for_goal(
    state: RisaState,
    start_action: str,
    target_effect: str,
) -> bool:
    """Report whether an adopted typed plan covers a start/goal pair at any role."""
    key = (
        f"plan_start:{normalize_label(start_action)}:"
        f"goal:{normalize_label(target_effect)}"
    )
    return any(
        candidate_id in state.unnamed_concept_candidates
        and state.unnamed_concept_candidates[candidate_id].lifecycle_status == "adopted"
        for candidate_id in state.candidate_inference_index.get(key, [])
    )


def _discover_temporal_sequence_candidates(
    state: RisaState,
    previous_candidates: dict[str, UnnamedConceptCandidate],
) -> dict[str, UnnamedConceptCandidate]:
    """Find two-step, same-target schemas whose first effect enables the second step."""
    by_episode: dict[str, list[Event]] = defaultdict(list)
    for event in state.events_by_id.values():
        if (
            event.target
            and not event.source.startswith(("derived:", "replay:"))
        ):
            by_episode[event.episode_id or "__default__"].append(event)

    pair_groups: dict[
        tuple[object, ...], list[tuple[Event, Event, str, str]]
    ] = defaultdict(list)
    all_by_start_role: dict[
        tuple[str, str, str], list[tuple[Event, Event, str, str]]
    ] = defaultdict(list)
    for episode_events in by_episode.values():
        ordered = sorted(episode_events, key=lambda item: (item.timestamp, item.id))
        for first, second in zip(ordered, ordered[1:]):
            if normalize_label(first.target or "") != normalize_label(second.target or ""):
                continue
            shared_roles = {
                normalize_label(role) for role in first.target_roles
            }.intersection(normalize_label(role) for role in second.target_roles)
            shared_actor_roles: set[str] = set()
            if normalize_label(first.actor) == normalize_label(second.actor):
                shared_actor_roles = {
                    normalize_label(role) for role in first.actor_roles
                }.intersection(normalize_label(role) for role in second.actor_roles)
            actor_role_options = sorted(shared_actor_roles) or [""]
            for role in sorted(shared_roles):
                for actor_role in actor_role_options:
                    all_by_start_role[
                        (normalize_label(first.action), role, actor_role)
                    ].append((first, second, role, actor_role))
            if (
                not first.transition_succeeded
                or not second.transition_succeeded
                or not first.observed_effects
                or not second.observed_effects
            ):
                continue
            first_effects = _normalized_tuple(first.observed_effects)
            second_requirements = _event_state_requirements(second)
            if not set(first_effects).intersection(second_requirements):
                continue
            first_step = _event_step_signature(first)
            second_step = _event_step_signature(second)
            for role in sorted(shared_roles):
                for actor_role in actor_role_options:
                    signature = (role, actor_role, first_step, second_step)
                    record = (first, second, role, actor_role)
                    pair_groups[signature].append(record)

    candidates: dict[str, UnnamedConceptCandidate] = {}
    for (role, actor_role, first_step, second_step), records in sorted(
        pair_groups.items()
    ):
        targets = {normalize_label(first.target or "") for first, _, _, _ in records}
        sources = {
            event.source for first, second, _, _ in records for event in (first, second)
        }
        episodes = {first.episode_id for first, _, _, _ in records}
        if len(targets) < 2 or len(sources) < 2 or len(episodes) < 2:
            continue
        first_schema = _step_schema(first_step)
        second_schema = _step_schema(second_step)
        goal_effects = list(second_schema["effects"])
        signature_text = repr(
            ("temporal_sequence", role, actor_role, first_step, second_step)
        )
        candidate_id = (
            f"candidate:temporal:{hashlib.sha256(signature_text.encode()).hexdigest()[:16]}"
        )
        counterexample_ids: set[str] = set()
        for other_first, other_second, _, _ in all_by_start_role[
            (first_schema["action"], role, actor_role)
        ]:
            if not (
                other_first.transition_succeeded
                and other_second.transition_succeeded
                and other_first.observed_effects
                and other_second.observed_effects
            ) or (
                _event_step_signature(other_first),
                _event_step_signature(other_second),
            ) != (first_step, second_step):
                counterexample_ids.update((other_first.id, other_second.id))
        supporting_ids = sorted(
            {
                event.id
                for first, second, _, _ in records
                for event in (first, second)
            }
        )
        concrete_length = sum(
            len(normalize_label(first.target or ""))
            + len(repr(_event_step_signature(first)))
            + len(repr(_event_step_signature(second)))
            for first, second, _, _ in records
        )
        schema_length = (
            len(role) + len(actor_role) + len(repr(first_step)) + len(repr(second_step))
        )
        structural_schema: dict[str, object] = {
            "kind": "temporal_sequence",
            "target_role": role,
            "target_binding": "same_target",
            "steps": [first_schema, second_schema],
            "goal_effects": goal_effects,
        }
        typed_role_variables = {"target": role}
        if actor_role:
            identity_relations = {
                normalize_label(first.actor) == normalize_label(first.target or "")
                for first, _, _, _ in records
            }
            variable_constraints: list[dict[str, str]] = []
            if len(identity_relations) == 1:
                variable_constraints.append(
                    {
                        "left": "actor",
                        "relation": "equal" if True in identity_relations else "not_equal",
                        "right": "target",
                    }
                )
            structural_schema.update(
                {
                    "actor_role": actor_role,
                    "actor_binding": "same_actor",
                    "variable_constraints": variable_constraints,
                }
            )
            typed_role_variables["actor"] = actor_role
        candidate = UnnamedConceptCandidate(
            id=candidate_id,
            structural_schema=structural_schema,
            typed_role_variables=typed_role_variables,
            supporting_event_ids=supporting_ids,
            counterexample_event_ids=sorted(counterexample_ids.difference(supporting_ids)),
            source_diversity=len(sources),
            episode_diversity=len(episodes),
            actor_diversity=len(
                {
                    normalize_label(event.actor)
                    for first, second, _, _ in records
                    for event in (first, second)
                }
            ),
            target_diversity=len(targets),
            context_diversity=len(
                {
                    tuple(sorted(normalize_label(tag) for tag in event.context_tags))
                    for first, second, _, _ in records
                    for event in (first, second)
                }
            ),
            description_length_delta=concrete_length - schema_length,
            reconstruction_gain=round(
                len(records) / (len(records) + len(counterexample_ids)), 6
            ),
            exception_cost=len(counterexample_ids),
        )
        _restore_unchanged_evaluation(candidate, previous_candidates.get(candidate_id))
        candidates[candidate_id] = candidate
    return candidates


def _normalized_tuple(values: list[str]) -> tuple[str, ...]:
    return tuple(sorted({normalize_label(value) for value in values}))


def _event_state_requirements(event: Event) -> tuple[str, ...]:
    requirements = {normalize_label(value) for value in event.preconditions}
    if event.before_state_observed:
        requirements.update(normalize_label(value) for value in event.observed_states_before)
    return tuple(sorted(requirements))


def _event_step_signature(event: Event) -> tuple[object, ...]:
    return (
        normalize_label(event.action),
        _event_state_requirements(event),
        _normalized_tuple(event.consumed_states),
        tuple(sorted((normalize_label(key), float(value)) for key, value in event.numeric_preconditions.items())),
        tuple(sorted((normalize_label(key), float(value)) for key, value in event.state_variable_deltas.items())),
        _normalized_tuple(event.observed_effects),
    )


def _step_schema(signature: tuple[object, ...]) -> dict[str, object]:
    action, requirements, consumed, numeric, deltas, effects = signature
    return {
        "action": action,
        "target_variable": "target",
        "requires": list(requirements),
        "consumes": list(consumed),
        "numeric_preconditions": dict(numeric),
        "state_variable_deltas": dict(deltas),
        "effects": list(effects),
    }


def _restore_unchanged_evaluation(
    candidate: UnnamedConceptCandidate,
    previous: UnnamedConceptCandidate | None,
) -> None:
    if (
        previous is None
        or previous.supporting_event_ids != candidate.supporting_event_ids
        or previous.counterexample_event_ids != candidate.counterexample_event_ids
    ):
        return
    candidate.lifecycle_status = previous.lifecycle_status
    candidate.evaluation_event_ids = list(previous.evaluation_event_ids)
    candidate.development_evaluation_event_ids = list(
        previous.development_evaluation_event_ids
    )
    candidate.final_evaluation_event_ids = list(previous.final_evaluation_event_ids)
    candidate.heldout_prediction_delta = previous.heldout_prediction_delta
    candidate.heldout_composition_delta = previous.heldout_composition_delta
    candidate.prediction_delta_ci_lower = previous.prediction_delta_ci_lower
    candidate.composition_delta_ci_lower = previous.composition_delta_ci_lower
    candidate.false_generalization_delta = previous.false_generalization_delta


def _add_candidate_index(state: RisaState, key: str, candidate_id: str) -> None:
    values = state.candidate_inference_index.setdefault(key, [])
    if candidate_id not in values:
        values.append(candidate_id)


def evaluate_unnamed_candidate(
    state: RisaState,
    candidate_id: str,
    *,
    partition: str,
    evaluation_event_ids: list[str],
    prediction_delta: float,
    composition_delta: float,
    prediction_delta_ci_lower: float,
    composition_delta_ci_lower: float,
    false_generalization_delta: float,
    minimum_gain: float = 0.05,
) -> UnnamedConceptCandidate:
    candidate = state.unnamed_concept_candidates[candidate_id]
    overlap = set(candidate.supporting_event_ids).intersection(evaluation_event_ids)
    if overlap:
        raise ValueError(
            f"candidate evaluation overlaps supporting evidence: {sorted(overlap)}"
        )
    if partition not in {"development", "final"}:
        raise ValueError("partition must be 'development' or 'final'")
    if partition == "final" and candidate.lifecycle_status != "provisional":
        raise ValueError("final evaluation requires a provisional candidate")
    partition_ids = set(evaluation_event_ids)
    if partition == "development":
        cross_partition_overlap = partition_ids.intersection(
            candidate.final_evaluation_event_ids
        )
    else:
        cross_partition_overlap = partition_ids.intersection(
            candidate.development_evaluation_event_ids
        )
    if cross_partition_overlap:
        raise ValueError(
            "candidate evaluation overlaps development/final evidence: "
            f"{sorted(cross_partition_overlap)}"
        )
    candidate.evaluation_event_ids = sorted(
        set(candidate.evaluation_event_ids).union(evaluation_event_ids)
    )
    if partition == "development":
        candidate.development_evaluation_event_ids = sorted(
            set(candidate.development_evaluation_event_ids).union(evaluation_event_ids)
        )
    else:
        candidate.final_evaluation_event_ids = sorted(
            set(candidate.final_evaluation_event_ids).union(evaluation_event_ids)
        )
    candidate.heldout_prediction_delta = prediction_delta
    candidate.heldout_composition_delta = composition_delta
    candidate.prediction_delta_ci_lower = prediction_delta_ci_lower
    candidate.composition_delta_ci_lower = composition_delta_ci_lower
    candidate.false_generalization_delta = false_generalization_delta

    has_supported_gain = (
        prediction_delta >= minimum_gain and prediction_delta_ci_lower > 0.0
    ) or (
        composition_delta >= minimum_gain and composition_delta_ci_lower > 0.0
    )
    passes = (
        candidate.description_length_delta > 0
        and has_supported_gain
        and false_generalization_delta <= 0.0
    )
    if partition == "development":
        candidate.lifecycle_status = "provisional" if passes else "rejected"
    else:
        candidate.lifecycle_status = "adopted" if passes else "rejected"
    rebuild_candidate_inference_index(state)
    return candidate
