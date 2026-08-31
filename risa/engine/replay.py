from __future__ import annotations

from risa.core.models import (
    PredictionQuery,
    ReplaySummary,
    StructuralAdaptationCandidate,
    StructuralPrimitive,
)
from risa.core.state import RisaState
from risa.engine.composer import forecast_next_effects
from risa.engine.graph_builder import normalize_label
from risa.engine.learner import refresh_primitive_adoption
from risa.engine.predictor import predict_next_effect
from risa.engine.state_variables import apply_variable_deltas


def replay_structural_memory(state: RisaState) -> ReplaySummary:
    """Re-evaluate stored evidence using the current induced world model."""
    summary = ReplaySummary()

    for event in sorted(state.events_by_id.values(), key=lambda item: (item.timestamp, item.id)):
        primitive_ids = state.event_primitive_ids.get(event.id, [])
        if not primitive_ids or not event.observed_effects:
            continue

        prediction = predict_next_effect(
            state,
            PredictionQuery(
                actor=event.actor,
                action=event.action,
                target=event.target,
                context_tags=event.context_tags,
            ),
        )
        predicted = {normalize_label(effect) for effect in prediction.predicted_effects}
        observed = {normalize_label(effect) for effect in event.observed_effects}
        success = bool(predicted & observed)

        summary.replayed_events += 1
        if success:
            summary.successful_events += 1
        else:
            summary.failed_events += 1

        for primitive_id in primitive_ids:
            primitive = state.structural_primitives.get(primitive_id)
            if primitive is None:
                continue
            primitive.replay_count += 1
            if success:
                primitive.replay_success_count += 1
            primitive.replay_score = primitive.replay_success_count / primitive.replay_count
            refresh_primitive_adoption(primitive)

    _replay_deployment_trajectory(state, summary)
    _refresh_adaptation_candidates(state)
    return summary


def _replay_deployment_trajectory(state: RisaState, summary: ReplaySummary) -> None:
    """Roll forward from model-generated states instead of restoring observed states."""
    active_states_by_actor: dict[str, set[str]] = {}
    active_variables_by_actor: dict[str, dict[str, float]] = {}

    for event in sorted(state.events_by_id.values(), key=lambda item: (item.timestamp, item.id)):
        primitive_ids = state.event_primitive_ids.get(event.id, [])
        if not primitive_ids or not event.observed_effects:
            continue

        actor = normalize_label(event.actor)
        active_states = active_states_by_actor.setdefault(actor, set())
        active_variables = active_variables_by_actor.setdefault(actor, {})
        candidates = forecast_next_effects(
            state,
            action=event.action,
            current_states=sorted(active_states),
            current_variables=active_variables,
            context_tags=event.context_tags,
        )
        predicted = {normalize_label(candidate.target_effect) for candidate in candidates}
        observed = {normalize_label(effect) for effect in event.observed_effects}
        success = bool(predicted & observed)

        perturbation_success: bool | None = None
        if active_states:
            perturbed_states = _drop_deterministic_state(active_states, event.id)
            perturbed_candidates = forecast_next_effects(
                state,
                action=event.action,
                current_states=sorted(perturbed_states),
                current_variables=active_variables,
                context_tags=event.context_tags,
            )
            perturbed_predicted = {
                normalize_label(candidate.target_effect) for candidate in perturbed_candidates
            }
            perturbation_success = bool(perturbed_predicted & observed)
            summary.perturbed_events += 1
            if perturbation_success:
                summary.perturbation_survived_events += 1
            else:
                summary.perturbation_failed_events += 1

        summary.deployment_replayed_events += 1
        if success:
            summary.deployment_successful_events += 1
        else:
            summary.deployment_failed_events += 1

        # Only model-generated transitions advance the rollout state.
        consumed = {
            normalize_label(state_name)
            for candidate in candidates
            for state_name in candidate.removed_states
        }
        active_states.difference_update(consumed)
        active_states.update(predicted)
        if candidates:
            updated_variables = apply_variable_deltas(
                state.state_variable_specs,
                active_variables,
                candidates[0].variable_deltas,
            )
            if updated_variables is not None:
                active_variables_by_actor[actor] = updated_variables

        for primitive_id in primitive_ids:
            primitive = state.structural_primitives.get(primitive_id)
            if primitive is None:
                continue
            primitive.deployment_replay_count += 1
            if success:
                primitive.deployment_replay_success_count += 1
            primitive.deployment_replay_score = (
                primitive.deployment_replay_success_count / primitive.deployment_replay_count
            )
            if perturbation_success is not None:
                primitive.perturbation_replay_count += 1
                if perturbation_success:
                    primitive.perturbation_replay_success_count += 1
                primitive.perturbation_replay_score = (
                    primitive.perturbation_replay_success_count
                    / primitive.perturbation_replay_count
                )
            refresh_primitive_adoption(primitive)


def _drop_deterministic_state(active_states: set[str], event_id: str) -> set[str]:
    ordered_states = sorted(active_states)
    drop_index = sum(ord(character) for character in event_id) % len(ordered_states)
    return set(ordered_states[:drop_index] + ordered_states[drop_index + 1 :])


def _refresh_adaptation_candidates(state: RisaState) -> None:
    candidates: dict[str, StructuralAdaptationCandidate] = {}
    for primitive in state.structural_primitives.values():
        candidate = _adaptation_candidate_for(primitive)
        if candidate is not None:
            candidates[primitive.id] = candidate
    state.structural_adaptation_candidates = candidates


def _adaptation_candidate_for(
    primitive: StructuralPrimitive,
) -> StructuralAdaptationCandidate | None:
    evidence = {
        "replay_count": primitive.replay_count,
        "replay_score": round(primitive.replay_score, 4),
        "deployment_replay_count": primitive.deployment_replay_count,
        "deployment_replay_score": round(primitive.deployment_replay_score, 4),
        "perturbation_replay_count": primitive.perturbation_replay_count,
        "perturbation_replay_score": round(primitive.perturbation_replay_score, 4),
    }

    if primitive.replay_count >= 2 and primitive.replay_score < 0.6:
        return StructuralAdaptationCandidate(
            primitive_id=primitive.id,
            reason="clean_replay_instability",
            proposed_operation="SPLIT_CONTEXT",
            pressure=round(1.0 - primitive.replay_score, 4),
            evidence=evidence,
        )
    if (
        primitive.deployment_replay_count >= 2
        and primitive.replay_score >= 0.6
        and primitive.deployment_replay_score < 0.6
    ):
        return StructuralAdaptationCandidate(
            primitive_id=primitive.id,
            reason="deployment_trajectory_drift",
            proposed_operation="REPAIR_TRANSITION",
            pressure=round(1.0 - primitive.deployment_replay_score, 4),
            evidence=evidence,
        )
    if (
        primitive.perturbation_replay_count >= 2
        and primitive.deployment_replay_score >= 0.6
        and primitive.perturbation_replay_score < 0.5
    ):
        return StructuralAdaptationCandidate(
            primitive_id=primitive.id,
            reason="single_state_dependency",
            proposed_operation="ADD_REDUNDANT_PATH",
            pressure=round(1.0 - primitive.perturbation_replay_score, 4),
            evidence=evidence,
        )
    return None
