from __future__ import annotations

from risa.core.models import (
    Event,
    PredictionQuery,
    ReplaySummary,
    StructuralAdaptationCandidate,
    StructuralPrimitive,
)
from risa.core.state import RisaState
from risa.engine.composer import forecast_next_effects
from risa.engine.event_order import replay_event_window
from risa.engine.graph_builder import normalize_label
from risa.engine.learner import refresh_primitive_adoption
from risa.engine.predictor import predict_next_effect


def replay_structural_memory(
    state: RisaState,
    max_events: int | None = None,
    *,
    enable_contextual_split_proposal: bool = False,
) -> ReplaySummary:
    """Re-evaluate stored evidence using the current induced world model."""
    summary = ReplaySummary()
    ordered_events, selection_work = replay_event_window(state, max_events)
    summary.selection_events_examined = selection_work
    contextual_errors: dict[str, dict[str, list[int]]] = {}

    for event in ordered_events:
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
                actor_roles=event.actor_roles,
                target_roles=event.target_roles,
                entity_bindings=event.entity_bindings,
                entity_relations=event.entity_relations,
            ),
        )
        predicted = {normalize_label(effect) for effect in prediction.predicted_effects}
        observed = {normalize_label(effect) for effect in event.observed_effects}
        success = predicted == observed

        summary.replayed_events += 1
        if success:
            summary.successful_events += 1
        else:
            summary.failed_events += 1

        contextual_seen: set[str] = set()
        for primitive_id in primitive_ids:
            primitive = state.structural_primitives.get(primitive_id)
            if primitive is None:
                continue
            if enable_contextual_split_proposal and primitive_id not in contextual_seen:
                contextual_seen.add(primitive_id)
                context = "|".join(sorted(
                    normalize_label(tag) for tag in event.context_tags
                )) or "__no_context__"
                counts = contextual_errors.setdefault(primitive_id, {}).setdefault(
                    context, [0, 0]
                )
                counts[0] += 1
                counts[1] += int(not success)
            primitive.replay_count += 1
            if success:
                primitive.replay_success_count += 1
            primitive.replay_score = primitive.replay_success_count / primitive.replay_count
            refresh_primitive_adoption(primitive)

    _replay_deployment_trajectory(state, summary, events=ordered_events)
    _refresh_adaptation_candidates(
        state,
        contextual_errors if enable_contextual_split_proposal else None,
    )
    return summary


def _replay_deployment_trajectory(
    state: RisaState,
    summary: ReplaySummary,
    events: list[Event] | None = None,
) -> None:
    """Roll forward from model-generated states instead of restoring observed states."""
    trajectories_by_actor_episode: dict[
        tuple[str, str], list[tuple[set[str], dict[str, float]]]
    ] = {}

    ordered_events = (
        events
        if events is not None
        else sorted(state.events_by_id.values(), key=lambda item: (item.timestamp, item.id))
    )
    for event in ordered_events:
        primitive_ids = state.event_primitive_ids.get(event.id, [])
        if not primitive_ids or not event.observed_effects:
            continue

        actor = normalize_label(event.actor)
        actor_episode = (event.episode_id or "__default__", actor)
        trajectories = trajectories_by_actor_episode.setdefault(actor_episode, [(set(), {})])
        candidate_branches: list[tuple[set[str], dict[str, float], set[str]]] = []
        perturbation_outcomes: list[set[str]] = []
        had_perturbable_state = False
        for active_states, active_variables in trajectories:
            candidates = forecast_next_effects(
                state,
                action=event.action,
                current_states=sorted(active_states),
                current_variables=active_variables,
                context_tags=event.context_tags,
            )
            for candidate in candidates:
                next_states = (
                    active_states - set(candidate.removed_states)
                ) | set(candidate.added_states)
                candidate_branches.append(
                    (
                        next_states,
                        dict(candidate.resulting_variables),
                        {normalize_label(effect) for effect in candidate.added_states},
                    )
                )

            if active_states:
                had_perturbable_state = True
                perturbed_states = _drop_deterministic_state(active_states, event.id)
                perturbed_candidates = forecast_next_effects(
                    state,
                    action=event.action,
                    current_states=sorted(perturbed_states),
                    current_variables=active_variables,
                    context_tags=event.context_tags,
                )
                perturbation_outcomes.extend(
                    {normalize_label(effect) for effect in candidate.added_states}
                    for candidate in perturbed_candidates
                )

        observed = {normalize_label(effect) for effect in event.observed_effects}
        success = any(outcome == observed for _, _, outcome in candidate_branches)

        perturbation_success: bool | None = None
        if had_perturbable_state:
            perturbation_success = observed in perturbation_outcomes
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

        # Alternative outcomes remain independent possible worlds.
        if candidate_branches:
            unique: dict[tuple[tuple[str, ...], tuple[tuple[str, float], ...]], tuple[set[str], dict[str, float]]] = {}
            for next_states, next_variables, _ in candidate_branches:
                key = (tuple(sorted(next_states)), tuple(sorted(next_variables.items())))
                unique[key] = (next_states, next_variables)
            trajectories_by_actor_episode[actor_episode] = [
                unique[key] for key in sorted(unique)[:8]
            ]

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


def _refresh_adaptation_candidates(
    state: RisaState,
    contextual_errors: dict[str, dict[str, list[int]]] | None = None,
) -> None:
    candidates: dict[str, StructuralAdaptationCandidate] = {}
    for primitive in state.structural_primitives.values():
        candidate = _adaptation_candidate_for(primitive)
        if candidate is None and contextual_errors is not None and not primitive.superseded_by:
            candidate = _contextual_split_candidate(
                primitive, contextual_errors.get(primitive.id, {})
            )
        if candidate is not None:
            candidates[primitive.id] = candidate
    state.structural_adaptation_candidates = candidates


def _contextual_split_candidate(
    primitive: StructuralPrimitive,
    contexts: dict[str, list[int]],
) -> StructuralAdaptationCandidate | None:
    """Experimental contrast: require local errors and a stable peer context."""
    eligible = {
        context: (total, wrong)
        for context, (total, wrong) in contexts.items()
        if total >= 2
    }
    unstable = [
        (context, total, wrong)
        for context, (total, wrong) in eligible.items()
        if wrong >= 2 and wrong / total >= 0.75
    ]
    stable = [
        (context, total, wrong)
        for context, (total, wrong) in eligible.items()
        if wrong / total <= 0.25
    ]
    contrasts = [
        (bad_context, bad_total, bad_wrong, good_context, good_total, good_wrong)
        for bad_context, bad_total, bad_wrong in unstable
        for good_context, good_total, good_wrong in stable
        if bad_context != good_context
        and bad_wrong / bad_total - good_wrong / good_total >= 0.5
    ]
    if not contrasts:
        return None
    bad_context, bad_total, bad_wrong, good_context, good_total, good_wrong = min(contrasts)
    return StructuralAdaptationCandidate(
        primitive_id=primitive.id,
        reason="contextual_clean_replay_instability_experimental",
        proposed_operation="SPLIT_CONTEXT",
        pressure=round(bad_wrong / bad_total - good_wrong / good_total, 4),
        evidence={
            "unstable_context_events": bad_total,
            "unstable_context_errors": bad_wrong,
            "stable_context_events": good_total,
            "stable_context_errors": good_wrong,
        },
    )


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
