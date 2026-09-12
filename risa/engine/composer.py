from __future__ import annotations

from collections import deque

from risa.core.models import (
    CompositionResult,
    StructuralPrimitive,
    UnnamedConceptCandidate,
)
from risa.core.state import RisaState
from risa.engine.candidate_discovery import (
    has_adopted_plan_candidate_for_goal,
    matching_adopted_candidates,
    matching_adopted_plan_candidates,
)
from risa.engine.graph_builder import normalize_label
from risa.engine.role_induction import effective_query_target_roles
from risa.engine.transitions import apply_primitive_transition


def forecast_next_effects(
    state: RisaState,
    action: str,
    current_states: list[str] | None = None,
    current_variables: dict[str, float] | None = None,
    context_tags: list[str] | None = None,
    max_candidates: int = 3,
    include_supported_alternatives: bool = False,
    target_roles: list[str] | None = None,
    enable_candidate_concepts: bool = True,
    target: str | None = None,
    entity_bindings: dict[str, str] | None = None,
    entity_relations: list[dict[str, str]] | None = None,
    enable_role_induction: bool = True,
) -> list[CompositionResult]:
    """Return locally applicable next-state candidates without collapsing uncertainty."""
    normalized_action = normalize_label(action)
    context = {normalize_label(tag) for tag in context_tags or []}
    available_states = {f"state:{normalize_label(state_name)}" for state_name in current_states or []}
    available_variables = {
        normalize_label(name): float(value) for name, value in (current_variables or {}).items()
    }
    target_roles = effective_query_target_roles(
        target=target,
        supplied_roles=target_roles or [],
        entity_bindings=entity_bindings or {},
        entity_relations=entity_relations or [],
        enable_role_induction=enable_role_induction,
    )
    candidates: list[CompositionResult] = []

    for primitive in _adopted_primitives_for_action(
        state,
        normalized_action,
        context,
        available_states,
        available_variables,
        include_supported_alternatives=include_supported_alternatives,
        target_roles=target_roles or [],
        enable_candidate_concepts=enable_candidate_concepts,
    ):
        score = _primitive_score(primitive, context)
        produced_states = sorted(primitive.produced_states)
        application = apply_primitive_transition(
            state,
            primitive,
            available_states,
            available_variables,
        )
        if application is None:
            continue
        candidates.append(
            CompositionResult(
                target_effect=produced_states[0],
                added_states=application.added_states,
                removed_states=application.removed_states,
                variable_deltas=application.variable_deltas,
                resulting_variables=application.resulting_variables,
                primitive_ids=[primitive.id],
                supporting_paths=[
                    [
                        *sorted(primitive.input_state_conditions),
                        f"process:{normalized_action}",
                        primitive.id,
                        *[f"state:{state_name}" for state_name in produced_states],
                    ]
                ],
                score=round(score, 4),
                explanation=(
                    f"Forecast atomic outcome {produced_states} from an adopted primitive "
                    f"applicable to action '{normalized_action}'."
                ),
            )
        )

    candidates.sort(key=lambda candidate: (-candidate.score, candidate.target_effect, candidate.primitive_ids))
    return candidates[:max_candidates]


def compose_to_effect(
    state: RisaState,
    start_action: str,
    target_effect: str,
    context_tags: list[str] | None = None,
    start_states: list[str] | None = None,
    start_variables: dict[str, float] | None = None,
    max_steps: int = 3,
    target_roles: list[str] | None = None,
    actor_roles: list[str] | None = None,
    actor: str | None = None,
    target: str | None = None,
    entity_bindings: dict[str, str] | None = None,
    entity_role_bindings: dict[str, list[str]] | None = None,
    entity_relations: list[dict[str, str]] | None = None,
    enable_candidate_concepts: bool = True,
    enable_role_induction: bool = True,
) -> CompositionResult:
    """Find a local sequence of adopted transition primitives toward an effect."""
    action = normalize_label(start_action)
    effect = normalize_label(target_effect)
    context = {normalize_label(tag) for tag in context_tags or []}
    initial_states = {f"state:{normalize_label(state_name)}" for state_name in start_states or []}
    initial_variables = {
        normalize_label(name): float(value) for name, value in (start_variables or {}).items()
    }
    target_roles = effective_query_target_roles(
        target=target,
        supplied_roles=target_roles or [],
        entity_bindings=entity_bindings or {},
        entity_relations=entity_relations or [],
        enable_role_induction=enable_role_induction,
    )
    if enable_candidate_concepts:
        role_matching_plans = matching_adopted_plan_candidates(
            state,
            action,
            effect,
            target_roles or [],
            actor_roles or [],
            entity_role_bindings or {},
        )
        query_entity_bindings = {
            normalize_label(variable): normalize_label(identity)
            for variable, identity in (entity_bindings or {}).items()
        }
        if actor is not None:
            query_entity_bindings.setdefault("actor", normalize_label(actor))
        if target is not None:
            query_entity_bindings.setdefault("target", normalize_label(target))
        constraint_matching_plans = [
            candidate
            for candidate in role_matching_plans
            if _candidate_identity_constraints_match(
                candidate, query_entity_bindings
            )
            and _candidate_relation_constraints_match(
                candidate, entity_relations or []
            )
        ]
        if role_matching_plans and not constraint_matching_plans:
            return CompositionResult(
                target_effect=effect,
                explanation=(
                    f"Abstained because concrete entity identities or relations violate "
                    f"an adopted typed plan for action '{action}' and effect '{effect}'."
                ),
            )
        candidate_result = _compose_adopted_candidate_plan(
            state,
            constraint_matching_plans,
            action,
            effect,
            initial_states,
            initial_variables,
            max_steps,
        )
        if candidate_result is not None:
            return candidate_result
        if (
            not role_matching_plans
            and has_adopted_plan_candidate_for_goal(state, action, effect)
        ):
            normalized_roles = sorted(
                {normalize_label(role) for role in target_roles or []}
            )
            return CompositionResult(
                target_effect=effect,
                explanation=(
                    f"Abstained because adopted typed plans for action '{action}' and "
                    f"effect '{effect}' do not match query role bindings; "
                    f"target roles are {normalized_roles}."
                ),
            )
    queue = deque([(action, initial_states, initial_variables, [], [], 1.0, 0)])
    best_depth_by_action: dict[str, int] = {action: 0}

    while queue:
        current_action, available_states, available_variables, primitive_ids, paths, score, depth = queue.popleft()
        for primitive in _adopted_primitives_for_action(
            state,
            current_action,
            context,
            available_states,
            available_variables,
            target_roles=target_roles or [],
            enable_candidate_concepts=enable_candidate_concepts,
        ):
            primitive_score = _primitive_score(primitive, context)
            produced_states = sorted(primitive.produced_states)
            next_ids = [*primitive_ids, primitive.id]
            next_paths = [
                *paths,
                [
                    f"process:{current_action}",
                    primitive.id,
                    *[f"state:{state_name}" for state_name in produced_states],
                ],
            ]
            next_score = score * primitive_score
            application = apply_primitive_transition(
                state,
                primitive,
                available_states,
                available_variables,
            )
            if application is None:
                continue
            next_states = {f"state:{state_name}" for state_name in application.resulting_states}
            next_variables = application.resulting_variables

            if effect in primitive.produced_states:
                return CompositionResult(
                    target_effect=effect,
                    added_states=application.added_states,
                    removed_states=application.removed_states,
                    variable_deltas=application.variable_deltas,
                    resulting_variables=application.resulting_variables,
                    primitive_ids=next_ids,
                    supporting_paths=next_paths,
                    score=round(next_score, 4),
                    explanation=(
                        f"Composed {len(next_ids)} adopted structural primitives from action "
                        f"'{action}' toward effect '{effect}'."
                    ),
                )
            if depth >= max_steps - 1:
                continue

            for next_action, precedence_score in next_actions(state, current_action, context):
                next_depth = depth + 1
                if next_depth >= best_depth_by_action.get(next_action, max_steps):
                    continue
                best_depth_by_action[next_action] = next_depth
                queue.append(
                    (
                        next_action,
                        next_states,
                        next_variables,
                        next_ids,
                        [*next_paths, [f"process:{current_action}", "precedes", f"process:{next_action}"]],
                        next_score * precedence_score,
                        next_depth,
                    )
                )

    return CompositionResult(
        target_effect=effect,
        explanation=f"No adopted local primitive composition found from action '{action}' to effect '{effect}'.",
    )


def _compose_adopted_candidate_plan(
    state: RisaState,
    candidates: list[UnnamedConceptCandidate],
    start_action: str,
    target_effect: str,
    initial_states: set[str],
    initial_variables: dict[str, float],
    max_steps: int,
) -> CompositionResult | None:
    """Apply a learned same-target macro without materializing it in stored memory."""
    for candidate in candidates:
        raw_steps = candidate.structural_schema.get("steps", [])
        if not isinstance(raw_steps, list) or not raw_steps or len(raw_steps) > max_steps:
            continue
        available_states = set(initial_states)
        available_variables = dict(initial_variables)
        primitive_ids: list[str] = []
        paths: list[list[str]] = []
        removed_states: set[str] = set()
        applicable = True
        for index, raw_step in enumerate(raw_steps):
            if not isinstance(raw_step, dict):
                applicable = False
                break
            step_action = normalize_label(str(raw_step.get("action", "")))
            effects = {
                normalize_label(str(value)) for value in raw_step.get("effects", [])
            }
            if not step_action or not effects:
                applicable = False
                break
            primitive_id = f"derived:{candidate.id}:step:{index + 1}"
            primitive = StructuralPrimitive(
                id=primitive_id,
                relation_type="candidate_temporal_step",
                role_signature=(
                    "variables:"
                    + ",".join(
                        f"{variable}={role}"
                        for variable, role in sorted(
                            candidate.typed_role_variables.items()
                        )
                    )
                    + ":binding:same_by_variable"
                ),
                input_conditions={f"process:{step_action}"},
                input_state_conditions={
                    f"state:{normalize_label(str(value))}"
                    for value in raw_step.get("requires", [])
                },
                consumed_states={
                    f"state:{normalize_label(str(value))}"
                    for value in raw_step.get("consumes", [])
                },
                numeric_preconditions={
                    normalize_label(str(name)): float(value)
                    for name, value in dict(
                        raw_step.get("numeric_preconditions", {})
                    ).items()
                },
                state_variable_deltas={
                    normalize_label(str(name)): float(value)
                    for name, value in dict(
                        raw_step.get("state_variable_deltas", {})
                    ).items()
                },
                output_states=effects,
                evidence_event_ids=set(candidate.supporting_event_ids),
                support=len(candidate.supporting_event_ids),
                validation_score=min(
                    1.0, 0.5 + candidate.heldout_composition_delta
                ),
                reuse_score=candidate.reconstruction_gain,
                compression_proxy=float(candidate.description_length_delta),
                adoption_score=min(
                    1.0,
                    0.5
                    + candidate.heldout_composition_delta
                    + (0.25 * candidate.reconstruction_gain),
                ),
                adopted=True,
            )
            application = apply_primitive_transition(
                state, primitive, available_states, available_variables
            )
            if application is None:
                applicable = False
                break
            primitive_ids.append(primitive_id)
            paths.append(
                [
                    candidate.id,
                    *[
                        f"bind:{variable}=same_{variable}"
                        for variable in sorted(candidate.typed_role_variables)
                    ],
                    *[
                        "relation:"
                        + ":".join(
                            (
                                str(relation.get("source", "")),
                                str(relation.get("relation", "")),
                                str(relation.get("target", "")),
                            )
                        )
                        for relation in raw_step.get("entity_relations", [])
                        if isinstance(relation, dict)
                    ],
                    f"process:{step_action}",
                    primitive_id,
                    *[f"state:{value}" for value in sorted(effects)],
                ]
            )
            removed_states.update(application.removed_states)
            available_states = {
                f"state:{value}" for value in application.resulting_states
            }
            available_variables = application.resulting_variables
        if not applicable or f"state:{target_effect}" not in available_states:
            continue
        initial_state_names = {
            value.removeprefix("state:") for value in initial_states
        }
        resulting_state_names = {
            value.removeprefix("state:") for value in available_states
        }
        variable_deltas = {
            name: round(value - initial_variables.get(name, 0.0), 12)
            for name, value in available_variables.items()
            if value != initial_variables.get(name, 0.0)
        }
        return CompositionResult(
            target_effect=target_effect,
            added_states=sorted(resulting_state_names.difference(initial_state_names)),
            removed_states=sorted(removed_states),
            variable_deltas=variable_deltas,
            resulting_variables=available_variables,
            primitive_ids=primitive_ids,
            supporting_paths=paths,
            score=round(
                min(
                    1.0,
                    0.5
                    + candidate.heldout_composition_delta
                    + (0.25 * candidate.reconstruction_gain),
                ),
                4,
            ),
            explanation=(
                f"Applied adopted temporal candidate '{candidate.id}' as a "
                f"{len(primitive_ids)}-step same-target composition toward "
                f"effect '{target_effect}'."
            ),
        )
    return None


def _candidate_identity_constraints_match(
    candidate: UnnamedConceptCandidate,
    bindings: dict[str, str],
) -> bool:
    constraints = candidate.structural_schema.get("variable_constraints", [])
    if not isinstance(constraints, list):
        return True
    for constraint in constraints:
        if not isinstance(constraint, dict):
            continue
        left = bindings.get(normalize_label(str(constraint.get("left", ""))))
        right = bindings.get(normalize_label(str(constraint.get("right", ""))))
        relation = str(constraint.get("relation", ""))
        if left is None or right is None:
            continue
        if relation == "equal" and left != right:
            return False
        if relation == "not_equal" and left == right:
            return False
    return True


def _candidate_relation_constraints_match(
    candidate: UnnamedConceptCandidate,
    query_relations: list[dict[str, str]],
) -> bool:
    required: set[tuple[str, str, str]] = set()
    raw_steps = candidate.structural_schema.get("steps", [])
    if not isinstance(raw_steps, list):
        return True
    for step in raw_steps:
        if not isinstance(step, dict):
            continue
        for relation in step.get("entity_relations", []):
            if isinstance(relation, dict):
                required.add(
                    (
                        normalize_label(str(relation.get("source", ""))),
                        normalize_label(str(relation.get("relation", ""))),
                        normalize_label(str(relation.get("target", ""))),
                    )
                )
    if not required:
        return True
    available = {
        (
            normalize_label(str(relation.get("source", ""))),
            normalize_label(str(relation.get("relation", ""))),
            normalize_label(str(relation.get("target", ""))),
        )
        for relation in query_relations
    }
    return required.issubset(available)


def _adopted_primitives_for_action(
    state: RisaState,
    action: str,
    context: set[str],
    available_states: set[str],
    available_variables: dict[str, float],
    include_supported_alternatives: bool = False,
    target_roles: list[str] | None = None,
    enable_candidate_concepts: bool = True,
) -> list[StructuralPrimitive]:
    input_condition = f"process:{action}"
    primitives = [
        primitive
        for primitive in state.structural_primitives.values()
        if (primitive.adopted or (include_supported_alternatives and _is_supported_alternative(primitive)))
        and input_condition in primitive.input_conditions
        and apply_primitive_transition(
            state,
            primitive,
            available_states,
            available_variables,
        ) is not None
        and _context_compatible(primitive.context_tags, context)
    ]
    if enable_candidate_concepts:
        primitives.extend(
            _candidate_primitives_for_action(
                state, action, target_roles or [], context
            )
        )
    return primitives


def _candidate_primitives_for_action(
    state: RisaState,
    action: str,
    target_roles: list[str],
    context: set[str],
) -> list[StructuralPrimitive]:
    derived: list[StructuralPrimitive] = []
    for candidate in matching_adopted_candidates(
        state, action, target_roles, context
    ):
        effects = {
            normalize_label(str(effect))
            for effect in candidate.structural_schema.get("effects", [])
        }
        if not effects:
            continue
        heldout_gain = max(
            candidate.heldout_prediction_delta,
            candidate.heldout_composition_delta,
        )
        derived.append(
            StructuralPrimitive(
                id=f"derived:{candidate.id}",
                relation_type="candidate_transition",
                role_signature=f"target:{candidate.typed_role_variables.get('target', '')}",
                input_conditions={f"process:{action}"},
                output_states=effects,
                evidence_event_ids=set(candidate.supporting_event_ids),
                support=len(candidate.supporting_event_ids),
                validation_score=min(1.0, 0.5 + heldout_gain),
                reuse_score=candidate.reconstruction_gain,
                compression_proxy=float(candidate.description_length_delta),
                adoption_score=min(
                    1.0,
                    0.5 + heldout_gain + (0.25 * candidate.reconstruction_gain),
                ),
                adopted=True,
            )
        )
    return derived


def _is_supported_alternative(primitive: StructuralPrimitive) -> bool:
    """Keep repeated, replayable minority outcomes available to branch search."""
    return primitive.support >= 2 and primitive.replay_count >= 2 and primitive.replay_score >= 0.8


def next_actions(state: RisaState, action: str, context: set[str]) -> list[tuple[str, float]]:
    edges = []
    for edge in state.graph.outgoing(f"process:{action}"):
        if edge.relation_type != "precedes" or not edge.target.startswith("process:"):
            continue
        if context and edge.context_tags and not context.intersection(edge.context_tags):
            continue
        evidence_score = min(1.0, edge.evidence_count / 3.0)
        edges.append((edge.target.removeprefix("process:"), max(0.2, evidence_score)))
    return edges


def _primitive_score(primitive: StructuralPrimitive, context: set[str]) -> float:
    context_score = 1.0 if not context else _context_overlap(primitive.context_tags, context)
    return max(0.1, primitive.adoption_score * context_score)


def _context_compatible(primitive_context: set[str], query_context: set[str]) -> bool:
    return not query_context or not primitive_context or bool(primitive_context.intersection(query_context))


def _context_overlap(primitive_context: set[str], query_context: set[str]) -> float:
    if not primitive_context:
        return 0.5
    return len(primitive_context.intersection(query_context)) / len(query_context)
