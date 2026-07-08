from __future__ import annotations

from risa.core.models import PredictionQuery, PredictionResult
from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label


def predict_next_effect(state: RisaState, query: PredictionQuery) -> PredictionResult:
    actor = normalize_label(query.actor)
    action = normalize_label(query.action)
    actor_scores = state.actor_action_effect_counts.get(actor, {}).get(action, {})
    action_scores = state.action_effect_counts.get(action, {})
    context_key = "|".join(sorted(normalize_label(tag) for tag in query.context_tags)) or "__no_context__"
    actor_context_scores = (
        state.actor_action_context_effect_counts.get(actor, {}).get(action, {}).get(context_key, {})
    )
    action_context_scores = state.action_context_effect_counts.get(action, {}).get(context_key, {})

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

        score = (
            (0.25 * direct_match_score)
            + (0.25 * action_pattern_score)
            + (0.20 * actor_context_score)
            + (0.15 * action_context_score)
            + (0.15 * concept_support)
        )
        if score > best_score:
            best_score = score
            best_effect = effect

    supporting_paths = [[f"entity:{actor}", f"process:{action}", f"state:{best_effect}"]]
    concept_id = f"concept:shared_{action}_{best_effect}"
    if concept_id in state.concept_members:
        supporting_paths.append([f"entity:{actor}", concept_id, f"state:{best_effect}"])
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
        f"Predicted {best_effect} from action '{action}' using locally activated action, context, and concept patterns."
    )

    return PredictionResult(
        predicted_effects=[best_effect],
        score=round(best_score, 4),
        supporting_paths=supporting_paths,
        evidence_event_ids=sorted(evidence_event_ids),
        explanation=explanation,
    )


def _collect_local_candidates(state: RisaState, actor: str, action: str, context_key: str) -> list[str]:
    keys = [
        f"actor_action:{actor}:{action}",
        f"actor:{actor}",
        f"action:{action}",
        f"context:{context_key}",
    ]
    values: set[str] = set()
    for key in keys:
        values.update(state.activation_index.get(key, []))
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
