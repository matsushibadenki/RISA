"""G3.2 online predict-score-observe runner for a supplied fixed world fixture."""

from __future__ import annotations

from dataclasses import dataclass, replace

from risa.core.models import Event, PredictionQuery, ReplaySummary
from risa.core.state import RisaState
from risa.engine.predictor import predict_next_effect
from risa.engine.runtime import TrainingOptions, train_events
from risa.evaluation.drift_metrics import (
    adaptation_touch_counts,
    mechanism_delta,
    recovery_events,
    replay_cost,
    snapshot_mechanisms,
    snapshot_structures,
)


@dataclass(frozen=True)
class DriftProbe:
    id: str
    query: PredictionQuery
    expected_effects: tuple[str, ...]


def probe_success(state: RisaState, probes: list[DriftProbe]) -> float:
    if not probes:
        raise ValueError("at least one independent probe is required")
    successes = sum(
        tuple(sorted(predict_next_effect(state, probe.query).predicted_effects))
        == tuple(sorted(probe.expected_effects))
        for probe in probes
    )
    return successes / len(probes)


def run_drift_phase(
    state: RisaState,
    observations: list[Event],
    probes: list[DriftProbe],
    options: TrainingOptions,
    *,
    reference_accuracy: float,
    replay_interval: int = 20,
    recovery_window: int = 5,
    replay_offset: int = 0,
) -> dict[str, object]:
    """Probe without learning, then learn each observation after scoring it."""
    if replay_interval < 1:
        raise ValueError("replay_interval must be positive")
    if replay_offset < 0:
        raise ValueError("replay_offset must be non-negative")
    if len({probe.id for probe in probes}) != len(probes):
        raise ValueError("duplicate probe IDs")
    if {probe.id for probe in probes} & {event.id for event in observations}:
        raise ValueError("probe IDs overlap online observations")
    if {probe.id for probe in probes} & set(state.events_by_id):
        raise ValueError("probe IDs overlap learned Events")
    before_structures = snapshot_structures(state)
    before_mechanisms = snapshot_mechanisms(state)
    entry_accuracy = probe_success(state, probes)
    trajectory = [(0, entry_accuracy)]
    online_successes: list[int] = []
    summaries: list[ReplaySummary] = []
    replay_call_event_counts: list[int] = []
    for index, event in enumerate(observations, 1):
        prediction = predict_next_effect(
            state,
            PredictionQuery(
                actor=event.actor,
                action=event.action,
                target=event.target,
                context_tags=list(event.context_tags),
                actor_roles=list(event.actor_roles),
                target_roles=list(event.target_roles),
                entity_bindings=dict(event.entity_bindings),
                entity_relations=list(event.entity_relations),
            ),
        )
        online_successes.append(
            int(tuple(sorted(prediction.predicted_effects))
                == tuple(sorted(event.observed_effects)))
        )
        update_options = replace(
            options,
            enable_replay=(
                options.enable_replay
                and (replay_offset + index) % replay_interval == 0
            ),
            replay_summaries=summaries,
        )
        train_events(state, [event], options=update_options)
        if len(summaries) > len(replay_call_event_counts):
            replay_call_event_counts.append(index)
        trajectory.append((index, probe_success(state, probes)))
    recovered_at = recovery_events(
        trajectory, reference_accuracy, window=recovery_window
    )
    replay_through_recovery = [
        summary for event_count, summary in zip(replay_call_event_counts, summaries)
        if recovered_at is None or event_count <= recovered_at
    ]
    return {
        "entry_accuracy": entry_accuracy,
        "exit_accuracy": trajectory[-1][1],
        "online_pre_update_success": sum(online_successes) / len(online_successes)
        if online_successes else None,
        "observed_events": len(observations),
        "recovery_events": recovered_at,
        "recovery_censored": recovered_at is None,
        "adaptation": adaptation_touch_counts(
            before_structures, snapshot_structures(state)
        ),
        "replay": replay_cost(summaries),
        "replay_cost_per_recovery": replay_cost(replay_through_recovery),
        "mechanisms": mechanism_delta(
            before_mechanisms, snapshot_mechanisms(state)
        ),
        "probe_accuracy_by_observed_events": trajectory,
    }


def run_aba(
    state: RisaState,
    b_observations: list[Event],
    a2_observations: list[Event],
    a_probes: list[DriftProbe],
    b_probes: list[DriftProbe],
    options: TrainingOptions,
    *,
    b_reference_accuracy: float = 1.0,
    replay_interval: int = 20,
    recovery_window: int = 5,
) -> dict[str, object]:
    """Run B then A return from a trained A1 state with no probe learning."""
    if {probe.id for probe in a_probes} & {probe.id for probe in b_probes}:
        raise ValueError("A and B probe IDs must be disjoint")
    observed_ids = [event.id for event in b_observations + a2_observations]
    if len(set(observed_ids)) != len(observed_ids):
        raise ValueError("online observation IDs must be unique")
    a1_accuracy = probe_success(state, a_probes)
    b = run_drift_phase(
        state, b_observations, b_probes, options,
        reference_accuracy=b_reference_accuracy,
        replay_interval=replay_interval, recovery_window=recovery_window,
    )
    a2_entry_accuracy = probe_success(state, a_probes)
    a2 = run_drift_phase(
        state, a2_observations, a_probes, options,
        reference_accuracy=a1_accuracy,
        replay_interval=replay_interval, recovery_window=recovery_window,
        replay_offset=len(b_observations),
    )
    return {
        "a1_accuracy": a1_accuracy,
        "retention_after_return": (
            a2_entry_accuracy / a1_accuracy if a1_accuracy else None
        ),
        "a2_entry_accuracy": a2_entry_accuracy,
        "B": b,
        "A2": a2,
    }
