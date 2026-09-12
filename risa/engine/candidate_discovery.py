from __future__ import annotations

from collections import defaultdict
import hashlib

from risa.core.models import Event, UnnamedConceptCandidate
from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label
from risa.engine.role_induction import (
    effective_event_target_roles,
    is_induced_role,
    target_relation_position_signature,
)


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
        for role in effective_event_target_roles(event):
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
        structural_schema: dict[str, object] = {
            "action": action,
            "target_role": role,
            "effects": list(outcome),
        }
        if is_induced_role(role):
            structural_schema["target_role_origin"] = "induced_structure"
            structural_schema["target_role_signature"] = list(
                target_relation_position_signature(
                    target=events[0].target,
                    entity_bindings=events[0].entity_bindings,
                    entity_relations=events[0].entity_relations,
                )
            )
        candidate = UnnamedConceptCandidate(
            id=candidate_id,
            structural_schema=structural_schema,
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
    candidates.update(_discover_relational_sequence_candidates(state, previous_candidates))
    state.unnamed_concept_candidates = candidates
    from risa.engine.candidate_lifecycle import propose_context_derivations

    propose_context_derivations(state)
    for candidate in sorted(
        (
            item
            for item in previous_candidates.values()
            if item.derivation_generation > 0
        ),
        key=lambda item: (item.derivation_generation, item.id),
    ):
        if candidate.id in candidates:
            _restore_unchanged_evaluation(candidates[candidate.id], candidate)
            continue
        if all(
            parent_id in candidates
            and candidate.parent_evidence_digests.get(parent_id)
            == _candidate_lineage_fingerprint(candidates[parent_id])
            for parent_id in candidate.parent_candidate_ids
        ):
            candidates[candidate.id] = candidate
    state.unnamed_concept_candidates = candidates
    rebuild_candidate_inference_index(state)
    return candidates


def rebuild_candidate_inference_index(state: RisaState) -> None:
    """Rebuild the derived index; source Events and persisted graph stay unchanged."""
    state.candidate_inference_index.clear()
    for candidate in state.unnamed_concept_candidates.values():
        if candidate.lifecycle_status != "adopted" or candidate.dormant:
            continue
        kind = str(candidate.structural_schema.get("kind", "single_transition"))
        if kind in {"temporal_sequence", "relational_sequence"}:
            steps = candidate.structural_schema.get("steps", [])
            goal_effects = candidate.structural_schema.get("goal_effects", [])
            role = normalize_label(
                str(candidate.structural_schema.get("target_role", ""))
            )
            actor_role = normalize_label(
                str(candidate.structural_schema.get("actor_role", ""))
            )
            if not isinstance(steps, list) or not steps:
                continue
            first_step = steps[0]
            if not isinstance(first_step, dict):
                continue
            start_action = normalize_label(str(first_step.get("action", "")))
            indexed_goal_effects = goal_effects if isinstance(goal_effects, list) else []
            for goal_effect in indexed_goal_effects:
                goal = normalize_label(str(goal_effect))
                if start_action and goal and role:
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
                elif start_action and goal:
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
    context_tags: list[str] | set[str] | tuple[str, ...] = (),
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
        and not state.unnamed_concept_candidates[candidate_id].dormant
        and _candidate_context_matches(
            state.unnamed_concept_candidates[candidate_id], context_tags
        )
    ]


def _candidate_context_matches(
    candidate: UnnamedConceptCandidate,
    context_tags: list[str] | set[str] | tuple[str, ...],
) -> bool:
    available = {normalize_label(tag) for tag in context_tags}
    required = candidate.structural_schema.get("required_context_tags", [])
    if isinstance(required, list) and not {
        normalize_label(str(tag)) for tag in required
    }.issubset(available):
        return False
    alternatives = candidate.structural_schema.get(
        "required_context_alternatives", []
    )
    if isinstance(alternatives, list) and alternatives:
        return any(
            isinstance(item, list)
            and {normalize_label(str(tag)) for tag in item}.issubset(available)
            for item in alternatives
        )
    return True


def matching_adopted_plan_candidates(
    state: RisaState,
    start_action: str,
    target_effect: str,
    target_roles: list[str] | set[str] | tuple[str, ...],
    actor_roles: list[str] | set[str] | tuple[str, ...] = (),
    entity_role_bindings: dict[str, list[str]] | None = None,
) -> list[UnnamedConceptCandidate]:
    """Return adopted temporal schemas matching a role-bound plan query."""
    normalized_action = normalize_label(start_action)
    normalized_effect = normalize_label(target_effect)
    generic_key = f"plan_start:{normalized_action}:goal:{normalized_effect}"
    candidate_ids = set(state.candidate_inference_index.get(generic_key, []))
    query_roles = {
        variable: {normalize_label(role) for role in roles}
        for variable, roles in (entity_role_bindings or {}).items()
    }
    query_roles.setdefault("target", set()).update(
        normalize_label(role) for role in target_roles
    )
    query_roles.setdefault("actor", set()).update(
        normalize_label(role) for role in actor_roles
    )
    return [
        state.unnamed_concept_candidates[candidate_id]
        for candidate_id in sorted(candidate_ids)
        if candidate_id in state.unnamed_concept_candidates
        and state.unnamed_concept_candidates[candidate_id].lifecycle_status == "adopted"
        and not state.unnamed_concept_candidates[candidate_id].dormant
        and state.unnamed_concept_candidates[candidate_id].structural_schema.get("kind")
        in {"temporal_sequence", "relational_sequence"}
        and _candidate_roles_match(
            state.unnamed_concept_candidates[candidate_id], query_roles
        )
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
        and not state.unnamed_concept_candidates[candidate_id].dormant
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
            shared_roles = set(effective_event_target_roles(first)).intersection(
                effective_event_target_roles(second)
            )
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


def _discover_relational_sequence_candidates(
    state: RisaState,
    previous_candidates: dict[str, UnnamedConceptCandidate],
) -> dict[str, UnnamedConceptCandidate]:
    """Discover two-step schemas over an arbitrary set of named entity variables."""
    by_episode: dict[str, list[Event]] = defaultdict(list)
    for event in state.events_by_id.values():
        if event.entity_bindings and not event.source.startswith(("derived:", "replay:")):
            by_episode[event.episode_id or "__default__"].append(event)

    groups: dict[tuple[object, ...], list[tuple[Event, Event]]] = defaultdict(list)
    failures_by_base: dict[tuple[object, ...], list[tuple[Event, Event]]] = defaultdict(list)
    for episode_events in by_episode.values():
        ordered = sorted(episode_events, key=lambda item: (item.timestamp, item.id))
        for first, second in zip(ordered, ordered[1:]):
            variables = sorted(set(first.entity_bindings).intersection(second.entity_bindings))
            if len(variables) < 2 or any(
                normalize_label(first.entity_bindings[variable])
                != normalize_label(second.entity_bindings[variable])
                for variable in variables
            ):
                continue
            role_items: list[tuple[str, str]] = []
            for variable in variables:
                shared_roles = {
                    normalize_label(role)
                    for role in first.entity_role_bindings.get(variable, [])
                }.intersection(
                    normalize_label(role)
                    for role in second.entity_role_bindings.get(variable, [])
                )
                if not shared_roles:
                    break
                role_items.append((normalize_label(variable), sorted(shared_roles)[0]))
            if len(role_items) != len(variables):
                continue
            if not (
                _entity_relations_are_observed(first)
                and _entity_relations_are_observed(second)
            ):
                continue
            constraints = _entity_identity_constraints(first, variables)
            base_signature = (
                tuple(role_items),
                constraints,
                normalize_label(first.action),
                normalize_label(second.action),
            )
            if (
                not first.transition_succeeded
                or not second.transition_succeeded
                or not first.observed_effects
                or not second.observed_effects
                or not set(_normalized_tuple(first.observed_effects)).intersection(
                    _event_state_requirements(second)
                )
            ):
                if not first.transition_succeeded or not second.transition_succeeded:
                    failures_by_base[base_signature].append((first, second))
                continue
            signature = (
                tuple(role_items),
                constraints,
                _event_step_signature(first),
                _event_step_signature(second),
            )
            groups[signature].append((first, second))

    candidates: dict[str, UnnamedConceptCandidate] = {}
    for signature, records in sorted(groups.items(), key=lambda item: repr(item[0])):
        role_items, constraints, first_step, second_step = signature
        binding_instances = {
            tuple(
                (variable, normalize_label(first.entity_bindings[variable]))
                for variable, _ in role_items
            )
            for first, _ in records
        }
        sources = {event.source for pair in records for event in pair}
        episodes = {first.episode_id for first, _ in records}
        if len(binding_instances) < 2 or len(sources) < 2 or len(episodes) < 2:
            continue
        relation_observations = [
            (
                set(_normalized_entity_relations(first.entity_relations)),
                set(_normalized_entity_relations(second.entity_relations)),
            )
            for first, second in records
        ]
        relation_steps = tuple(
            tuple(sorted(set.intersection(*(observation[index] for observation in relation_observations))))
            for index in range(2)
        )
        base_signature = (
            role_items,
            constraints,
            normalize_label(str(first_step[0])),
            normalize_label(str(second_step[0])),
        )
        matched_failures = failures_by_base.get(base_signature, [])
        counterexample_pairs: list[tuple[Event, Event]] = []
        relation_negative_pairs: list[tuple[Event, Event]] = []
        for failed_pair in matched_failures:
            failed_relations = (
                set(_normalized_entity_relations(failed_pair[0].entity_relations)),
                set(_normalized_entity_relations(failed_pair[1].entity_relations)),
            )
            if all(
                set(required).issubset(observed)
                for required, observed in zip(relation_steps, failed_relations)
            ):
                counterexample_pairs.append(failed_pair)
            else:
                relation_negative_pairs.append(failed_pair)
        signature_text = repr(("relational_sequence", signature))
        candidate_id = (
            "candidate:relational:"
            + hashlib.sha256(signature_text.encode()).hexdigest()[:16]
        )
        steps = [_step_schema(first_step), _step_schema(second_step)]
        for step, relations in zip(steps, relation_steps):
            step["entity_relations"] = [
                {"source": source, "relation": relation, "target": target}
                for source, relation, target in relations
            ]
        supporting_ids = sorted({event.id for pair in records for event in pair})
        counterexample_ids = sorted(
            {event.id for pair in counterexample_pairs for event in pair}
        )
        relation_negative_ids = sorted(
            {event.id for pair in relation_negative_pairs for event in pair}
        )
        relation_requirement_evidence = []
        for step_index, required_relations in enumerate(relation_steps):
            relation_requirement_evidence.append(
                [
                    {
                        "source": source,
                        "relation": relation,
                        "target": target,
                        "success_support": len(records),
                        "failure_absence_support": sum(
                            (source, relation, target)
                            not in set(
                                _normalized_entity_relations(
                                    pair[step_index].entity_relations
                                )
                            )
                            for pair in matched_failures
                        ),
                    }
                    for source, relation, target in required_relations
                ]
            )
        concrete_length = sum(
            len(repr(first.entity_bindings))
            + len(repr(first.entity_relations))
            + len(repr(second.entity_relations))
            + len(repr(_event_step_signature(first)))
            + len(repr(_event_step_signature(second)))
            for first, second in records
        )
        schema_length = len(repr(signature))
        role_variables = dict(role_items)
        candidate = UnnamedConceptCandidate(
            id=candidate_id,
            structural_schema={
                "kind": "relational_sequence",
                "entity_binding": "same_by_variable",
                "entity_role_bindings": role_variables,
                "variable_constraints": [
                    {"left": left, "relation": relation, "right": right}
                    for left, relation, right in constraints
                ],
                "steps": steps,
                "goal_effects": list(steps[-1]["effects"]),
                "relation_requirement_evidence": relation_requirement_evidence,
                "relation_negative_event_ids": relation_negative_ids,
            },
            typed_role_variables=role_variables,
            supporting_event_ids=supporting_ids,
            counterexample_event_ids=counterexample_ids,
            source_diversity=len(sources),
            episode_diversity=len(episodes),
            actor_diversity=len(
                {normalize_label(event.actor) for pair in records for event in pair}
            ),
            target_diversity=len(binding_instances),
            context_diversity=len(
                {
                    tuple(sorted(normalize_label(tag) for tag in event.context_tags))
                    for pair in records
                    for event in pair
                }
            ),
            description_length_delta=concrete_length - schema_length,
            reconstruction_gain=round(
                len(records) / (len(records) + len(counterexample_pairs)), 6
            ),
            exception_cost=len(counterexample_pairs),
        )
        _restore_unchanged_evaluation(candidate, previous_candidates.get(candidate_id))
        candidates[candidate_id] = candidate
    return candidates


def _normalized_entity_relations(
    relations: list[dict[str, str]],
) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        sorted(
            (
                normalize_label(relation.get("source", "")),
                normalize_label(relation.get("relation", "")),
                normalize_label(relation.get("target", "")),
            )
            for relation in relations
        )
    )


def _entity_relations_are_observed(event: Event) -> bool:
    """Treat legacy non-empty relation lists as complete observations."""
    return event.entity_relations_observed or bool(event.entity_relations)


def _entity_identity_constraints(
    event: Event,
    variables: list[str],
) -> tuple[tuple[str, str, str], ...]:
    constraints = []
    for index, left in enumerate(variables):
        for right in variables[index + 1 :]:
            relation = (
                "equal"
                if normalize_label(event.entity_bindings[left])
                == normalize_label(event.entity_bindings[right])
                else "not_equal"
            )
            constraints.append((normalize_label(left), relation, normalize_label(right)))
    return tuple(constraints)


def _candidate_roles_match(
    candidate: UnnamedConceptCandidate,
    query_roles: dict[str, set[str]],
) -> bool:
    return all(
        normalize_label(role) in query_roles.get(normalize_label(variable), set())
        for variable, role in candidate.typed_role_variables.items()
    )


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
    candidate.parent_heldout_prediction_delta = previous.parent_heldout_prediction_delta
    candidate.parent_heldout_composition_delta = previous.parent_heldout_composition_delta
    candidate.parent_prediction_delta_ci_lower = previous.parent_prediction_delta_ci_lower
    candidate.parent_composition_delta_ci_lower = previous.parent_composition_delta_ci_lower
    candidate.selected_for_final = previous.selected_for_final
    candidate.dormant = previous.dormant


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
    protected_evidence = _candidate_protected_evidence(state, candidate_id)
    overlap = protected_evidence.intersection(evaluation_event_ids)
    if overlap:
        raise ValueError(
            "candidate evaluation overlaps candidate or ancestor evidence: "
            f"{sorted(overlap)}"
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


def evaluate_derived_candidate(
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
    parent_prediction_delta: float,
    parent_composition_delta: float,
    parent_prediction_delta_ci_lower: float,
    parent_composition_delta_ci_lower: float,
    minimum_gain: float = 0.05,
) -> UnnamedConceptCandidate:
    """Evaluate a derived candidate against a baseline and its strongest parent."""
    candidate = state.unnamed_concept_candidates[candidate_id]
    if candidate.derivation_generation <= 0 or not candidate.parent_candidate_ids:
        raise ValueError("derived evaluation requires a candidate with parents")
    if partition == "final" and not candidate.selected_for_final:
        raise ValueError(
            "final evaluation requires development selection for a derived candidate"
        )
    parent_has_supported_gain = (
        parent_prediction_delta >= minimum_gain
        and parent_prediction_delta_ci_lower > 0.0
    ) or (
        parent_composition_delta >= minimum_gain
        and parent_composition_delta_ci_lower > 0.0
    )
    evaluated = evaluate_unnamed_candidate(
        state,
        candidate_id,
        partition=partition,
        evaluation_event_ids=evaluation_event_ids,
        prediction_delta=prediction_delta,
        composition_delta=composition_delta,
        prediction_delta_ci_lower=prediction_delta_ci_lower,
        composition_delta_ci_lower=composition_delta_ci_lower,
        false_generalization_delta=false_generalization_delta,
        minimum_gain=minimum_gain,
    )
    evaluated.parent_heldout_prediction_delta = parent_prediction_delta
    evaluated.parent_heldout_composition_delta = parent_composition_delta
    evaluated.parent_prediction_delta_ci_lower = parent_prediction_delta_ci_lower
    evaluated.parent_composition_delta_ci_lower = parent_composition_delta_ci_lower
    if not parent_has_supported_gain:
        evaluated.lifecycle_status = "rejected"
        rebuild_candidate_inference_index(state)
    elif partition == "development":
        evaluated.selected_for_final = False
    elif evaluated.lifecycle_status == "adopted":
        _dormant_replaced_ancestors(state, evaluated)
        rebuild_candidate_inference_index(state)
    return evaluated


def select_derived_candidates_for_final(
    state: RisaState,
    candidate_ids: list[str],
    *,
    max_selected: int = 1,
) -> list[UnnamedConceptCandidate]:
    """Select a bounded development winner set before touching final evidence."""
    if max_selected < 1:
        raise ValueError("max_selected must be positive")
    candidates = [state.unnamed_concept_candidates[item] for item in candidate_ids]
    if not candidates or any(candidate.derivation_generation <= 0 for candidate in candidates):
        raise ValueError("selection requires at least one derived candidate")
    eligible = [
        candidate
        for candidate in candidates
        if candidate.lifecycle_status == "provisional"
        and candidate.development_evaluation_event_ids
        and not candidate.final_evaluation_event_ids
    ]
    if not eligible:
        raise ValueError("selection requires a provisional development evaluation")
    development_partitions = {
        tuple(candidate.development_evaluation_event_ids) for candidate in eligible
    }
    if len(development_partitions) != 1:
        raise ValueError("selection candidates must share one development partition")
    selected_ids = {
        candidate.id
        for candidate in sorted(
            eligible,
            key=lambda item: (
                -max(
                    item.parent_prediction_delta_ci_lower,
                    item.parent_composition_delta_ci_lower,
                ),
                -max(
                    item.parent_heldout_prediction_delta,
                    item.parent_heldout_composition_delta,
                ),
                -max(item.prediction_delta_ci_lower, item.composition_delta_ci_lower),
                item.id,
            ),
        )[:max_selected]
    }
    for candidate in candidates:
        candidate.selected_for_final = candidate.id in selected_ids
        if candidate.lifecycle_status == "provisional" and not candidate.selected_for_final:
            candidate.lifecycle_status = "rejected"
    rebuild_candidate_inference_index(state)
    return [state.unnamed_concept_candidates[item] for item in sorted(selected_ids)]


def _dormant_replaced_ancestors(
    state: RisaState, candidate: UnnamedConceptCandidate
) -> None:
    """Deactivate adopted ancestors whose broader transition is replaced by a child."""
    transition_keys = ("action", "target_role", "effects")
    expected = tuple(candidate.structural_schema.get(key) for key in transition_keys)
    pending = list(candidate.parent_candidate_ids)
    visited: set[str] = set()
    while pending:
        ancestor_id = pending.pop()
        if ancestor_id in visited:
            continue
        visited.add(ancestor_id)
        ancestor = state.unnamed_concept_candidates.get(ancestor_id)
        if ancestor is None:
            continue
        if (
            ancestor.lifecycle_status == "adopted"
            and tuple(ancestor.structural_schema.get(key) for key in transition_keys)
            == expected
        ):
            ancestor.dormant = True
        pending.extend(ancestor.parent_candidate_ids)


def _candidate_protected_evidence(state: RisaState, candidate_id: str) -> set[str]:
    from risa.engine.candidate_lifecycle import validate_candidate_ancestry

    validate_candidate_ancestry(state, candidate_id)
    candidate = state.unnamed_concept_candidates[candidate_id]
    protected: set[str] = set(candidate.supporting_event_ids)
    pending = list(candidate.parent_candidate_ids)
    visited: set[str] = set()
    while pending:
        current_id = pending.pop()
        if current_id in visited:
            continue
        visited.add(current_id)
        current = state.unnamed_concept_candidates.get(current_id)
        if current is None:
            raise ValueError(f"candidate ancestry references missing parent '{current_id}'")
        protected.update(current.supporting_event_ids)
        protected.update(current.evaluation_event_ids)
        pending.extend(current.parent_candidate_ids)
    return protected


def _candidate_lineage_fingerprint(candidate: UnnamedConceptCandidate) -> str:
    payload = repr(
        (
            candidate.structural_schema,
            candidate.typed_role_variables,
            candidate.supporting_event_ids,
            candidate.counterexample_event_ids,
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:20]
