"""G3.2 online predict-score-observe runner for a supplied fixed world fixture."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

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


@dataclass(frozen=True)
class ValidationStepResult:
    """Supervised labels consumed by one online adoption/validation step."""

    label_ids: tuple[str, ...] = ()
    adoption_decisions: int = 0


ValidationStep = Callable[[RisaState, int, Event, int | None], ValidationStepResult]


def _assert_scoring_probes_unseen(state: RisaState, protected_ids: set[str]) -> None:
    if protected_ids & set(state.events_by_id):
        raise ValueError("scoring probes entered learned Events")
    for candidate in state.unnamed_concept_candidates.values():
        used = set(candidate.evaluation_event_ids)
        used.update(candidate.development_evaluation_event_ids)
        used.update(candidate.final_evaluation_event_ids)
        if protected_ids & used:
            raise ValueError("scoring probes entered candidate validation")


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
    validation_step: ValidationStep | None = None,
    validation_label_budget: int | None = None,
    protected_probe_ids: set[str] | None = None,
    previous_validation_label_ids: set[str] | None = None,
) -> dict[str, object]:
    """Probe without learning, then learn each observation after scoring it."""
    if replay_interval < 1:
        raise ValueError("replay_interval must be positive")
    if replay_offset < 0:
        raise ValueError("replay_offset must be non-negative")
    if validation_label_budget is not None and validation_label_budget < 0:
        raise ValueError("validation_label_budget must be non-negative")
    if len({probe.id for probe in probes}) != len(probes):
        raise ValueError("duplicate probe IDs")
    if {probe.id for probe in probes} & {event.id for event in observations}:
        raise ValueError("probe IDs overlap online observations")
    if {probe.id for probe in probes} & set(state.events_by_id):
        raise ValueError("probe IDs overlap learned Events")
    protected = {probe.id for probe in probes} | (protected_probe_ids or set())
    if protected & {event.id for event in observations}:
        raise ValueError("protected probe IDs overlap online observations")
    _assert_scoring_probes_unseen(state, protected)
    before_structures = snapshot_structures(state)
    before_mechanisms = snapshot_mechanisms(state)
    entry_accuracy = probe_success(state, probes)
    trajectory = [(0, entry_accuracy)]
    online_successes: list[int] = []
    summaries: list[ReplaySummary] = []
    replay_call_event_counts: list[int] = []
    mechanism_trace: list[dict[str, int]] = []
    validation_trace: list[dict[str, int]] = []
    consumed_label_ids: set[str] = set()
    previous_labels = previous_validation_label_ids or set()
    validation_decisions = 0
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
        if validation_step is not None:
            remaining = (
                None if validation_label_budget is None
                else validation_label_budget - len(consumed_label_ids)
            )
            validation = validation_step(state, index, event, remaining)
            if not isinstance(validation, ValidationStepResult):
                raise TypeError("validation_step must return ValidationStepResult")
            label_ids = validation.label_ids
            if (len(label_ids) != len(set(label_ids))
                    or set(label_ids) & (consumed_label_ids | previous_labels)):
                raise ValueError("validation label IDs must be unique across the phase")
            if set(label_ids) & protected:
                raise ValueError("scoring probes cannot be validation labels")
            if validation.adoption_decisions < 0:
                raise ValueError("adoption_decisions must be non-negative")
            if remaining is not None and len(label_ids) > remaining:
                raise ValueError("validation label budget exceeded")
            consumed_label_ids.update(label_ids)
            validation_decisions += validation.adoption_decisions
            validation_trace.append({
                "observed_events": index,
                "labels_consumed": len(label_ids),
                "adoption_decisions": validation.adoption_decisions,
            })
        _assert_scoring_probes_unseen(state, protected)
        mechanism_state = snapshot_mechanisms(state)
        mechanism_trace.append({
            "observed_events": index,
            "executed_context_splits": len(mechanism_state.executed_context_splits),
            "merged_proposals": len(mechanism_state.merged_proposals),
            "adopted_merges": len(mechanism_state.adopted_merges),
            "dormant_candidates": len(mechanism_state.dormant_candidates),
        })
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
    labels_through_recovery = sum(
        row["labels_consumed"] for row in validation_trace
        if recovered_at is None or row["observed_events"] <= recovered_at
    )
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
        "validation_labels_total": len(consumed_label_ids),
        "validation_label_ids": sorted(consumed_label_ids),
        "validation_labels_per_recovery": labels_through_recovery,
        "validation_adoption_decisions": validation_decisions,
        "validation_trace": validation_trace,
        "mechanisms": mechanism_delta(
            before_mechanisms, snapshot_mechanisms(state)
        ),
        "mechanism_trace": mechanism_trace,
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
    validation_step: ValidationStep | None = None,
    validation_label_budget: int | None = None,
) -> dict[str, object]:
    """Run B then A return from a trained A1 state with no probe learning."""
    if {probe.id for probe in a_probes} & {probe.id for probe in b_probes}:
        raise ValueError("A and B probe IDs must be disjoint")
    observed_ids = [event.id for event in b_observations + a2_observations]
    if len(set(observed_ids)) != len(observed_ids):
        raise ValueError("online observation IDs must be unique")
    if validation_label_budget is not None and validation_label_budget < 0:
        raise ValueError("validation_label_budget must be non-negative")
    protected = {probe.id for probe in a_probes + b_probes}
    if protected & set(observed_ids):
        raise ValueError("scoring probe IDs overlap online observations")
    _assert_scoring_probes_unseen(state, protected)
    a1_accuracy = probe_success(state, a_probes)
    b = run_drift_phase(
        state, b_observations, b_probes, options,
        reference_accuracy=b_reference_accuracy,
        replay_interval=replay_interval, recovery_window=recovery_window,
        validation_step=validation_step,
        validation_label_budget=validation_label_budget,
        protected_probe_ids=protected,
    )
    a2_entry_accuracy = probe_success(state, a_probes)
    a2 = run_drift_phase(
        state, a2_observations, a_probes, options,
        reference_accuracy=a1_accuracy,
        replay_interval=replay_interval, recovery_window=recovery_window,
        replay_offset=len(b_observations),
        validation_step=validation_step,
        validation_label_budget=(
            None if validation_label_budget is None
            else validation_label_budget - b["validation_labels_total"]
        ),
        protected_probe_ids=protected,
        previous_validation_label_ids=set(b["validation_label_ids"]),
    )
    return {
        "a1_accuracy": a1_accuracy,
        "retention_after_return": (
            a2_entry_accuracy / a1_accuracy if a1_accuracy else None
        ),
        "a2_entry_accuracy": a2_entry_accuracy,
        "B": b,
        "A2": a2,
        "validation_labels_total": (
            b["validation_labels_total"] + a2["validation_labels_total"]
        ),
    }
