from __future__ import annotations

from risa.core.models import PredictionQuery, PredictionResult
from risa.core.state import RisaState
from risa.engine.candidate_discovery import matching_adopted_candidates
from risa.engine.graph_builder import normalize_label
from risa.engine.role_induction import (
    effective_event_target_roles,
    effective_query_target_roles,
)
from risa.engine.evidence import matching_evidence_event_ids
from risa.engine.validator import competition_penalty, validation_support


def predict_next_effect(state: RisaState, query: PredictionQuery) -> PredictionResult:
    actor = normalize_label(query.actor)
    action = normalize_label(query.action)
    target = normalize_label(query.target) if query.target else ""
    target_roles = effective_query_target_roles(
        target=query.target,
        supplied_roles=query.target_roles,
        entity_bindings=query.entity_bindings,
        entity_relations=query.entity_relations,
        enable_role_induction=query.enable_role_induction,
    )
    adopted_candidates = (
        matching_adopted_candidates(
            state, action, target_roles, query.context_tags
        )
        if query.enable_candidate_concepts
        else []
    )
    actor_id = f"entity:{actor}"
    action_id = f"process:{action}"
    actor_scores = state.actor_action_effect_counts.get(actor, {}).get(action, {})
    action_scores = state.action_effect_counts.get(action, {})
    action_has_structural_evidence = any(
        f"process:{action}" in primitive.input_conditions
        for primitive in state.structural_primitives.values()
    )
    if not action_scores and not action_has_structural_evidence and not adopted_candidates:
        return PredictionResult(
            predicted_effects=[],
            score=0.0,
            explanation=f"Abstained because action '{action}' has no observed applicability evidence.",
            claim_status="abstained",
        )
    context_key = "|".join(sorted(normalize_label(tag) for tag in query.context_tags)) or "__no_context__"
    actor_context_scores = (
        state.actor_action_context_effect_counts.get(actor, {}).get(action, {}).get(context_key, {})
    )
    action_context_scores = state.action_context_effect_counts.get(action, {}).get(context_key, {})
    actor_target_scores = (
        state.actor_action_target_context_effect_counts.get(
            _target_evidence_key(actor, action, target, context_key), {}
        )
        if target
        else {}
    )
    target_scores = (
        state.action_target_context_effect_counts.get(
            _target_evidence_key("*", action, target, context_key), {}
        )
        if target
        else {}
    )
    target_role_scores: dict[str, int] = {}
    for role in target_roles:
        role_scores = state.action_target_role_context_effect_counts.get(
            _target_evidence_key("role", action, role, context_key), {}
        )
        for effect, count in role_scores.items():
            target_role_scores[effect] = target_role_scores.get(effect, 0) + count
    if (
        target
        and not actor_target_scores
        and not target_scores
        and not target_role_scores
        and not adopted_candidates
    ):
        return PredictionResult(
            predicted_effects=[],
            score=0.0,
            explanation=(
                f"Abstained because target '{target}' has no observed applicability "
                f"evidence for action '{action}'."
            ),
            claim_status="abstained",
        )
    structural_pattern = _matching_structural_pattern(state, context_key)
    validation_score = validation_support(state, actor, action, context_key)
    recent_grounded_outcome = (
        _recent_grounded_outcome(
            state,
            action=action,
            target=target,
            target_roles=target_roles,
            context_key=context_key,
        )
        if query.enable_change_adaptation
        else []
    )

    candidate_effects = _collect_local_candidates(state, actor, action, context_key)
    if target:
        candidate_effects = sorted(
            set(actor_target_scores)
            | set(target_scores)
            | set(target_role_scores)
            | {
                normalize_label(str(effect))
                for candidate in adopted_candidates
                for effect in candidate.structural_schema.get("effects", [])
            }
        )
    if not candidate_effects:
        return PredictionResult(
            predicted_effects=[],
            score=0.0,
            explanation="No matching pattern found.",
            claim_status="abstained",
        )

    best_effect = ""
    best_score = -1.0
    for effect in candidate_effects:
        direct_total = sum(actor_scores.values())
        action_total = sum(action_scores.values())
        actor_context_total = sum(actor_context_scores.values())
        action_context_total = sum(action_context_scores.values())
        actor_target_total = sum(actor_target_scores.values())
        target_total = sum(target_scores.values())
        target_role_total = sum(target_role_scores.values())
        direct_match_score = (actor_scores.get(effect, 0) / direct_total) if direct_total else 0.0
        action_pattern_score = (action_scores.get(effect, 0) / action_total) if action_total else 0.0
        actor_context_score = (actor_context_scores.get(effect, 0) / actor_context_total) if actor_context_total else 0.0
        action_context_score = (action_context_scores.get(effect, 0) / action_context_total) if action_context_total else 0.0
        actor_target_score = (actor_target_scores.get(effect, 0) / actor_target_total) if actor_target_total else 0.0
        target_score = (target_scores.get(effect, 0) / target_total) if target_total else 0.0
        target_role_score = (
            target_role_scores.get(effect, 0) / target_role_total
            if target_role_total
            else 0.0
        )
        recent_change_support = 1.0 if effect in recent_grounded_outcome else 0.0
        candidate_concept_support = max(
            (
                min(
                    1.0,
                    0.5
                    + (0.25 * candidate.reconstruction_gain)
                    + max(
                        candidate.heldout_prediction_delta,
                        candidate.heldout_composition_delta,
                    ),
                )
                for candidate in adopted_candidates
                if effect
                in {
                    normalize_label(str(item))
                    for item in candidate.structural_schema.get("effects", [])
                }
            ),
            default=0.0,
        )

        concept_support = 0.0
        concept_id = f"concept:shared_{action}_{effect}"
        if concept_id in state.concept_members:
            members = state.concept_members[concept_id]
            if actor in members:
                concept_support = 1.0
            elif members:
                concept_support = 0.6

        structural_support = 0.0
        if structural_pattern is not None and effect in structural_pattern.effects:
            structural_support = min(
                1.0,
                (structural_pattern.support / 5.0) * max(0.4, structural_pattern.validation_score),
            )

        coactivation_support = _coactivation_support(
            state,
            actor_id=actor_id,
            action_id=action_id,
            effect_id=f"state:{effect}",
        )
        reproducibility_support = _reproducibility_support(state, action_id, f"state:{effect}")
        primitive_support = _primitive_support(state, action, effect, context_key)
        inhibition_penalty = competition_penalty(state, action, context_key, effect)

        score = (
            (0.21 * direct_match_score)
            + (0.21 * action_pattern_score)
            + (0.20 * actor_context_score)
            + (0.15 * action_context_score)
            + (0.11 * concept_support)
            + (0.11 * structural_support)
            + (0.04 * coactivation_support)
            + (0.06 * reproducibility_support)
            + (0.05 * primitive_support)
            + (0.05 * validation_score)
            + (0.20 * actor_target_score)
            + (0.15 * target_score)
            + (0.20 * target_role_score)
            + (0.30 * candidate_concept_support)
            + (0.50 * recent_change_support)
            - (0.10 * inhibition_penalty)
        )
        if score > best_score:
            best_score = score
            best_effect = effect

    best_effect_id = f"state:{best_effect}"
    target_grounded_outcome = _target_grounded_outcome(
        state,
        actor=actor,
        action=action,
        target=target,
        target_roles=target_roles,
        context_key=context_key,
        selected_effect=best_effect,
    )
    matching_outcomes = _matching_primitives(state, action, best_effect)
    best_outcome = max(
        matching_outcomes,
        key=lambda primitive: (primitive.adoption_score, primitive.support, primitive.id),
        default=None,
    )
    best_candidate = max(
        (
            candidate
            for candidate in adopted_candidates
            if best_effect
            in {
                normalize_label(str(item))
                for item in candidate.structural_schema.get("effects", [])
            }
        ),
        key=lambda candidate: (
            max(candidate.heldout_prediction_delta, candidate.heldout_composition_delta),
            candidate.reconstruction_gain,
            candidate.description_length_delta,
            candidate.id,
        ),
        default=None,
    )
    if recent_grounded_outcome and best_effect in recent_grounded_outcome:
        predicted_effects = recent_grounded_outcome
    elif target_grounded_outcome:
        predicted_effects = target_grounded_outcome
    elif best_candidate is not None:
        predicted_effects = sorted(
            normalize_label(str(effect))
            for effect in best_candidate.structural_schema.get("effects", [])
        )
    elif best_outcome is not None:
        predicted_effects = sorted(best_outcome.produced_states)
    else:
        predicted_effects = [best_effect]
    supporting_paths: list[list[str]] = []
    if _find_edge(state, actor_id, action_id, "participates_in") is not None:
        supporting_paths.append(
            [actor_id, "participates_in", action_id, "derived_prediction", best_effect_id]
        )
    concept_id = f"concept:shared_{action}_{best_effect}"
    if concept_id in state.concept_members:
        supporting_paths.append([actor_id, concept_id, best_effect_id])
    if structural_pattern is not None and best_effect in structural_pattern.effects:
        supporting_paths.append([structural_pattern.id, f"context:{context_key}", best_effect_id])
    if _has_coactivation_edge(state, actor_id, action_id):
        supporting_paths.append([actor_id, "co_activates_with", action_id])
    if _has_coactivation_edge(state, action_id, best_effect_id):
        supporting_paths.append([action_id, "co_activates_with", best_effect_id])
    if _reproducibility_support(state, action_id, best_effect_id) > 0.0:
        supporting_paths.append([action_id, "reproducibly_affects", best_effect_id])
    for primitive in _matching_primitives(state, action, best_effect, adopted_only=True):
        supporting_paths.append([primitive.id, "composes_to", best_effect_id])
    if best_candidate is not None:
        matched_role = normalize_label(
            str(best_candidate.structural_schema.get("target_role", ""))
        )
        supporting_paths.append(
            [
                best_candidate.id,
                f"role:{matched_role}",
                "derives_for",
                f"entity:{target}",
                best_effect_id,
            ]
        )
    inhibition_penalty = competition_penalty(state, action, context_key, best_effect)
    if inhibition_penalty > 0.0:
        supporting_paths.append([f"context:{context_key}", "competition_inhibits", best_effect_id])
    for effect in candidate_effects:
        if effect == best_effect:
            continue
        alternative_penalty = competition_penalty(state, action, context_key, effect)
        if alternative_penalty > 0.0:
            supporting_paths.append([f"context:{context_key}", "competition_inhibits", f"state:{effect}"])
    supporting_paths.extend(
        _event_supporting_paths(
            state,
            actor,
            action,
            best_effect,
            context_key,
            target,
            target_roles,
        )
    )

    evidence_event_ids = matching_evidence_event_ids(
        state,
        action=action,
        context_key=context_key,
        effect=best_effect,
        target=target,
        target_roles=target_roles,
    )
    if best_candidate is not None:
        evidence_event_ids = sorted(
            set(evidence_event_ids).union(best_candidate.supporting_event_ids)
        )
    explanation = (
        f"Derived {predicted_effects} from action '{action}' using observed evidence, locally activated "
        "action, context, structural primitives, concept, co-activation, reproducibility plasticity, "
        "prediction-validation history, and competition inhibition."
    )

    return PredictionResult(
        predicted_effects=predicted_effects,
        score=round(best_score, 4),
        supporting_paths=supporting_paths,
        evidence_event_ids=sorted(evidence_event_ids),
        explanation=explanation,
        claim_status="derived" if evidence_event_ids else "hypothetical",
        applicability_basis=(
            [
                f"actor:{actor}",
                f"action:{action}",
                f"target:{target}",
                *[f"target_role:{role}" for role in target_roles],
                *([best_candidate.id] if best_candidate is not None else []),
                *(["recent_change_run:3"] if recent_grounded_outcome else []),
                f"context:{context_key}",
            ]
            if target
            else [f"action:{action}", f"context:{context_key}"]
        ),
    )


def _collect_local_candidates(state: RisaState, actor: str, action: str, context_key: str) -> list[str]:
    actor_id = f"entity:{actor}"
    action_id = f"process:{action}"
    keys = [
        f"actor_action:{actor}:{action}",
        f"actor:{actor}",
        f"action:{action}",
        f"context:{context_key}",
    ]
    values: set[str] = set()
    for key in keys:
        values.update(state.activation_index.get(key, []))

    radius = _coactivation_radius(state, actor_id, action_id)
    if radius >= 1:
        values.update(_coactivation_candidate_effects(state, actor_id, max_depth=1))
        values.update(_coactivation_candidate_effects(state, action_id, max_depth=1))
    if radius >= 2:
        values.update(_coactivation_candidate_effects(state, actor_id, max_depth=2))
        values.update(_coactivation_candidate_effects(state, action_id, max_depth=2))
    structural_pattern = _matching_structural_pattern(state, context_key)
    if structural_pattern is not None:
        values.update(structural_pattern.effects)
    values.update(
        effect
        for primitive in _matching_primitives(state, action, adopted_only=True)
        for effect in primitive.produced_states
    )

    return sorted(effect for effect in values if _effect_is_not_dormant(state, effect))


def _event_supporting_paths(
    state: RisaState,
    actor: str,
    action: str,
    effect: str,
    context_key: str,
    target: str,
    target_roles: list[str],
) -> list[list[str]]:
    paths: list[list[str]] = []
    event_ids = matching_evidence_event_ids(
        state,
        action=action,
        context_key=context_key,
        effect=effect,
        target=target,
        target_roles=target_roles,
    )
    for event_id_value in event_ids:
        event = state.events_by_id[event_id_value]
        if normalize_label(event.actor) != actor and normalize_label(event.action) != action:
            continue
        if effect not in [normalize_label(item) for item in event.observed_effects]:
            continue
        event_roles = set(effective_event_target_roles(event))
        target_matches = normalize_label(event.target or "") == target
        role_matches = bool(set(target_roles).intersection(event_roles))
        if target and not target_matches and not role_matches:
            continue
        event_context = "|".join(sorted(normalize_label(tag) for tag in event.context_tags)) or "__no_context__"
        if context_key != "__no_context__" and event_context != context_key:
            continue
        event_id = f"event:{normalize_label(event.id)}"
        path = [f"entity:{normalize_label(event.actor)}"]
        if target and not target_matches and role_matches:
            matched_role = sorted(set(target_roles).intersection(event_roles))[0]
            path.extend(
                [
                    f"entity:{target}",
                    f"role:{matched_role}",
                    "binds_as",
                    f"entity:{normalize_label(event.target or '')}",
                ]
            )
        path.append(event_id)
        if event.target:
            path.append(f"entity:{normalize_label(event.target)}")
        path.append(f"state:{effect}")
        paths.append(path)
        for edge in state.graph.incoming(event_id):
            if edge.relation_type == "event_precedes":
                temporal_path = [edge.source, "event_precedes", event_id]
                if event.target:
                    temporal_path.append(f"entity:{normalize_label(event.target)}")
                temporal_path.append(f"state:{effect}")
                paths.append(temporal_path)
    return paths[:3]


def _effect_is_not_dormant(state: RisaState, effect: str) -> bool:
    node = state.graph.get_node(f"state:{effect}")
    return node is None or not node.dormant


def _coactivation_support(
    state: RisaState,
    actor_id: str,
    action_id: str,
    effect_id: str,
) -> float:
    actor_action = _edge_strength(state, actor_id, action_id, "co_activates_with")
    action_effect = _edge_strength(state, action_id, effect_id, "co_activates_with")
    actor_effect = _edge_strength(state, actor_id, effect_id, "co_activates_with")
    return min(1.0, actor_action + action_effect + (0.5 * actor_effect))


def _reproducibility_support(state: RisaState, action_id: str, effect_id: str) -> float:
    edge = state.graph.edges_by_key.get((action_id, effect_id, "affects"))
    if edge is None:
        return 0.0

    evidence_factor = min(1.0, edge.evidence_count / 5.0)
    stable_strength = (0.7 * edge.reliability) + (0.3 * evidence_factor)
    return min(1.0, stable_strength * (1.0 - (0.5 * edge.plasticity)))


def _primitive_support(state: RisaState, action: str, effect: str, context_key: str) -> float:
    primitives = _matching_primitives(state, action, effect, adopted_only=True)
    if not primitives:
        return 0.0

    best_score = 0.0
    for primitive in primitives:
        support = min(1.0, primitive.support / 5.0)
        if context_key == "__no_context__":
            context_match = 0.7
        elif not primitive.context_tags:
            context_match = 0.5
        else:
            context_match = len(set(context_key.split("|")) & primitive.context_tags) / len(
                set(context_key.split("|"))
            )
        best_score = max(best_score, support * max(0.4, primitive.validation_score) * context_match)
    return best_score


def _matching_primitives(
    state: RisaState,
    action: str,
    effect: str | None = None,
    adopted_only: bool = False,
):
    input_condition = f"process:{action}"
    return [
        primitive
        for primitive in state.structural_primitives.values()
        if input_condition in primitive.input_conditions
        and (effect is None or effect in primitive.produced_states)
        and (not adopted_only or primitive.adopted)
    ]


def _edge_strength(
    state: RisaState,
    source: str,
    target: str,
    relation_type: str,
) -> float:
    edge = _find_edge(state, source, target, relation_type)
    if edge is None:
        return 0.0
    reliability = edge.reliability or 0.0
    evidence_factor = min(1.0, edge.evidence_count / 5.0)
    return min(1.0, (0.7 * reliability) + (0.3 * evidence_factor))


def _has_coactivation_edge(state: RisaState, source: str, target: str) -> bool:
    return _find_edge(state, source, target, "co_activates_with") is not None


def _coactivation_candidate_effects(state: RisaState, node_id: str, max_depth: int) -> set[str]:
    frontier = {node_id}
    visited = {node_id}
    effects: set[str] = set()

    for _ in range(max_depth):
        next_frontier: set[str] = set()
        for edge in state.graph.edges_by_key.values():
            if edge.relation_type != "co_activates_with":
                continue

            if edge.source in frontier and edge.target not in visited:
                next_frontier.add(edge.target)
            if edge.target in frontier and edge.source not in visited:
                next_frontier.add(edge.source)

        if not next_frontier:
            break

        for other in next_frontier:
            if other.startswith("state:"):
                effects.add(other.removeprefix("state:"))

        visited.update(next_frontier)
        frontier = next_frontier

    return effects


def _coactivation_radius(state: RisaState, actor_id: str, action_id: str) -> int:
    strength = _edge_strength(state, actor_id, action_id, "co_activates_with")
    if strength >= 0.3:
        return 2
    if strength > 0.0:
        return 1
    return 0


def _matching_structural_pattern(state: RisaState, context_key: str):
    role_signature = "entity->process->state"
    return state.structural_patterns.get(f"structural:{role_signature}:{context_key}")


def _target_evidence_key(actor: str, action: str, target: str, context_key: str) -> str:
    return "\x1f".join((actor, action, target, context_key))


def _target_grounded_outcome(
    state: RisaState,
    actor: str,
    action: str,
    target: str,
    target_roles: list[str],
    context_key: str,
    selected_effect: str,
) -> list[str]:
    """Choose a complete observed outcome without crossing target boundaries."""
    if not target:
        return []

    matching_events = []
    event_ids = matching_evidence_event_ids(
        state,
        action=action,
        context_key=context_key,
        effect=selected_effect,
        target=target,
        target_roles=target_roles,
        exact_context=True,
    )
    for event_id in event_ids:
        event = state.events_by_id[event_id]
        event_effects = sorted({normalize_label(effect) for effect in event.observed_effects})
        event_context = (
            "|".join(sorted(normalize_label(tag) for tag in event.context_tags))
            or "__no_context__"
        )
        if (
            normalize_label(event.action) == action
            and (
                normalize_label(event.target or "") == target
                or bool(set(target_roles).intersection(effective_event_target_roles(event)))
            )
            and selected_effect in event_effects
            and event_context == context_key
        ):
            matching_events.append((normalize_label(event.actor), tuple(event_effects)))

    actor_events = [outcome for event_actor, outcome in matching_events if event_actor == actor]
    outcomes = actor_events or [outcome for _, outcome in matching_events]
    if not outcomes:
        return []

    counts: dict[tuple[str, ...], int] = {}
    for outcome in outcomes:
        counts[outcome] = counts.get(outcome, 0) + 1
    selected = sorted(counts, key=lambda outcome: (-counts[outcome], outcome))[0]
    return list(selected)


def _recent_grounded_outcome(
    state: RisaState,
    action: str,
    target: str,
    target_roles: list[str],
    context_key: str,
    minimum_run: int = 3,
) -> list[str]:
    if not target:
        return []
    exact: list[tuple[str, ...]] = []
    role_bound: list[tuple[str, ...]] = []
    query_roles = set(target_roles)
    event_ids = matching_evidence_event_ids(
        state,
        action=action,
        context_key=context_key,
        target=target,
        target_roles=target_roles,
        exact_context=True,
    )
    for event in sorted(
        (state.events_by_id[event_id] for event_id in event_ids),
        key=lambda item: (item.timestamp, item.id),
    ):
        event_context = (
            "|".join(sorted(normalize_label(tag) for tag in event.context_tags))
            or "__no_context__"
        )
        if normalize_label(event.action) != action or event_context != context_key:
            continue
        outcome = tuple(sorted({normalize_label(effect) for effect in event.observed_effects}))
        if normalize_label(event.target or "") == target:
            exact.append(outcome)
        elif query_roles.intersection(effective_event_target_roles(event)):
            role_bound.append(outcome)
    outcomes = exact or role_bound
    if len(outcomes) < minimum_run:
        return []
    recent = outcomes[-minimum_run:]
    return list(recent[0]) if len(set(recent)) == 1 else []


def _find_edge(
    state: RisaState,
    source: str,
    target: str,
    relation_type: str,
):
    return state.graph.edges_by_key.get((source, target, relation_type)) or state.graph.edges_by_key.get(
        (target, source, relation_type)
    )
