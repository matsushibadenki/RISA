from __future__ import annotations

from risa.core.models import PredictionQuery, PredictionResult
from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label
from risa.engine.validator import competition_penalty, validation_support


def predict_next_effect(state: RisaState, query: PredictionQuery) -> PredictionResult:
    actor = normalize_label(query.actor)
    action = normalize_label(query.action)
    actor_id = f"entity:{actor}"
    action_id = f"process:{action}"
    actor_scores = state.actor_action_effect_counts.get(actor, {}).get(action, {})
    action_scores = state.action_effect_counts.get(action, {})
    context_key = "|".join(sorted(normalize_label(tag) for tag in query.context_tags)) or "__no_context__"
    actor_context_scores = (
        state.actor_action_context_effect_counts.get(actor, {}).get(action, {}).get(context_key, {})
    )
    action_context_scores = state.action_context_effect_counts.get(action, {}).get(context_key, {})
    structural_pattern = _matching_structural_pattern(state, context_key)
    validation_score = validation_support(state, actor, action, context_key)

    candidate_effects = _collect_local_candidates(state, actor, action, context_key)
    if not candidate_effects:
        return PredictionResult(predicted_effects=[], score=0.0, explanation="No matching pattern found.")

    best_effect = ""
    best_score = -1.0
    for effect in candidate_effects:
        direct_total = sum(actor_scores.values())
        action_total = sum(action_scores.values())
        actor_context_total = sum(actor_context_scores.values())
        action_context_total = sum(action_context_scores.values())
        direct_match_score = (actor_scores.get(effect, 0) / direct_total) if direct_total else 0.0
        action_pattern_score = (action_scores.get(effect, 0) / action_total) if action_total else 0.0
        actor_context_score = (actor_context_scores.get(effect, 0) / actor_context_total) if actor_context_total else 0.0
        action_context_score = (action_context_scores.get(effect, 0) / action_context_total) if action_context_total else 0.0

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
            - (0.10 * inhibition_penalty)
        )
        if score > best_score:
            best_score = score
            best_effect = effect

    best_effect_id = f"state:{best_effect}"
    supporting_paths = [[actor_id, action_id, best_effect_id]]
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
    inhibition_penalty = competition_penalty(state, action, context_key, best_effect)
    if inhibition_penalty > 0.0:
        supporting_paths.append([f"context:{context_key}", "competition_inhibits", best_effect_id])
    for effect in candidate_effects:
        if effect == best_effect:
            continue
        alternative_penalty = competition_penalty(state, action, context_key, effect)
        if alternative_penalty > 0.0:
            supporting_paths.append([f"context:{context_key}", "competition_inhibits", f"state:{effect}"])
    supporting_paths.extend(_event_supporting_paths(state, actor, action, best_effect, context_key))

    evidence_event_ids = [
        event.id
        for event in state.events_by_id.values()
        if normalize_label(event.action) == action
        and best_effect in [normalize_label(effect) for effect in event.observed_effects]
        and (
            context_key == "__no_context__"
            or context_key == "|".join(sorted(normalize_label(tag) for tag in event.context_tags))
        )
    ]
    explanation = (
        f"Predicted {best_effect} from action '{action}' using locally activated action, context, structural primitives, concept, co-activation, reproducibility plasticity, prediction-validation history, and competition inhibition."
    )

    return PredictionResult(
        predicted_effects=[best_effect],
        score=round(best_score, 4),
        supporting_paths=supporting_paths,
        evidence_event_ids=sorted(evidence_event_ids),
        explanation=explanation,
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
        primitive.output_state for primitive in _matching_primitives(state, action, adopted_only=True)
    )

    return sorted(effect for effect in values if _effect_is_not_dormant(state, effect))


def _event_supporting_paths(
    state: RisaState,
    actor: str,
    action: str,
    effect: str,
    context_key: str,
) -> list[list[str]]:
    paths: list[list[str]] = []
    for event in state.events_by_id.values():
        if normalize_label(event.actor) != actor and normalize_label(event.action) != action:
            continue
        if effect not in [normalize_label(item) for item in event.observed_effects]:
            continue
        event_context = "|".join(sorted(normalize_label(tag) for tag in event.context_tags)) or "__no_context__"
        if context_key != "__no_context__" and event_context != context_key:
            continue
        paths.append([f"entity:{normalize_label(event.actor)}", f"event:{normalize_label(event.id)}", f"state:{effect}"])
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
        and (effect is None or primitive.output_state == effect)
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


def _find_edge(
    state: RisaState,
    source: str,
    target: str,
    relation_type: str,
):
    return state.graph.edges_by_key.get((source, target, relation_type)) or state.graph.edges_by_key.get(
        (target, source, relation_type)
    )
