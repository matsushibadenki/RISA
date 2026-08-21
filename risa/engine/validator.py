from __future__ import annotations

from risa.core.models import Event, PredictionQuery
from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label
from risa.engine.metabolism import apply_competition_inhibition, apply_prediction_outcome_plasticity


def validate_event_prediction(state: RisaState, event: Event) -> None:
    from risa.engine.predictor import predict_next_effect

    query = PredictionQuery(
        actor=event.actor,
        action=event.action,
        target=event.target,
        context_tags=event.context_tags,
    )
    result = predict_next_effect(state, query)
    if not result.predicted_effects:
        return

    predicted_effect = normalize_label(result.predicted_effects[0])
    observed_effects = {normalize_label(effect) for effect in event.observed_effects}
    matched = predicted_effect in observed_effects

    actor = normalize_label(event.actor)
    action = normalize_label(event.action)
    context_key = "|".join(sorted(normalize_label(tag) for tag in event.context_tags)) or "__no_context__"

    _update_validation_bucket(
        state,
        key=f"actor_action_context:{actor}:{action}:{context_key}",
        matched=matched,
    )
    _update_validation_bucket(
        state,
        key=f"action_context:{action}:{context_key}",
        matched=matched,
    )
    _update_validation_bucket(
        state,
        key=f"actor_action_context_effect:{actor}:{action}:{context_key}:{predicted_effect}",
        matched=matched,
    )
    _update_validation_bucket(
        state,
        key=f"action_context_effect:{action}:{context_key}:{predicted_effect}",
        matched=matched,
    )
    apply_prediction_outcome_plasticity(
        state,
        action_id=f"process:{action}",
        predicted_effect_id=f"state:{predicted_effect}",
        matched=matched,
        timestamp=event.timestamp,
    )
    if not matched:
        action_id = f"process:{action}"
        losing_effect_id = f"state:{predicted_effect}"
        winning_effect_ids = [f"state:{effect}" for effect in sorted(observed_effects)]
        for observed_effect in sorted(observed_effects):
            _update_competition_bucket(
                state,
                key=f"action_context_competition:{action}:{context_key}:{predicted_effect}",
                winner=observed_effect,
            )
        apply_competition_inhibition(
            state,
            action_id=action_id,
            losing_effect_id=losing_effect_id,
            winning_effect_ids=winning_effect_ids,
            timestamp=event.timestamp,
        )


def validation_support(state: RisaState, actor: str, action: str, context_key: str) -> float:
    actor_bucket = state.prediction_validation_stats.get(
        f"actor_action_context:{actor}:{action}:{context_key}",
        {}
    )
    action_bucket = state.prediction_validation_stats.get(
        f"action_context:{action}:{context_key}",
        {}
    )

    actor_score = _bucket_score(actor_bucket)
    action_score = _bucket_score(action_bucket)

    if actor_score is None and action_score is None:
        return 0.5
    if actor_score is None:
        return action_score
    if action_score is None:
        return actor_score
    return (0.65 * actor_score) + (0.35 * action_score)


def validation_effect_support(
    state: RisaState,
    actor: str,
    action: str,
    context_key: str,
    effect: str,
) -> float:
    actor_bucket = state.prediction_validation_stats.get(
        f"actor_action_context_effect:{actor}:{action}:{context_key}:{effect}",
        {}
    )
    action_bucket = state.prediction_validation_stats.get(
        f"action_context_effect:{action}:{context_key}:{effect}",
        {}
    )

    actor_score = _bucket_score(actor_bucket)
    action_score = _bucket_score(action_bucket)

    if actor_score is None and action_score is None:
        return validation_support(state, actor, action, context_key)
    if actor_score is None:
        return action_score
    if action_score is None:
        return actor_score
    return (0.7 * actor_score) + (0.3 * action_score)


def competition_penalty(
    state: RisaState,
    action: str,
    context_key: str,
    effect: str,
) -> float:
    bucket = state.prediction_competition_stats.get(
        f"action_context_competition:{action}:{context_key}:{effect}",
        {}
    )
    total_losses = sum(bucket.values())
    if total_losses <= 0:
        return 0.0
    return min(1.0, total_losses / 5.0)


def _update_validation_bucket(
    state: RisaState,
    key: str,
    matched: bool,
) -> None:
    bucket = state.prediction_validation_stats.setdefault(
        key,
        {"total": 0, "correct": 0, "incorrect": 0},
    )
    bucket["total"] += 1
    if matched:
        bucket["correct"] += 1
    else:
        bucket["incorrect"] += 1


def _update_competition_bucket(
    state: RisaState,
    key: str,
    winner: str,
) -> None:
    bucket = state.prediction_competition_stats.setdefault(key, {})
    bucket[winner] = bucket.get(winner, 0) + 1


def _bucket_score(bucket: dict[str, int]) -> float | None:
    total = bucket.get("total", 0)
    if total <= 0:
        return None
    return bucket.get("correct", 0) / total
