"""Probe-backed candidate lifecycle evaluation for controlled experiments."""

from __future__ import annotations

from dataclasses import dataclass
import random

from risa.core.state import RisaState
from risa.engine.candidate_discovery import (
    _candidate_context_matches,
    evaluate_derived_candidate,
    evaluate_unnamed_candidate,
)


@dataclass(frozen=True)
class ApplicabilityProbe:
    id: str
    episode_id: str
    source: str
    context_tags: tuple[str, ...]
    expected_applicable: bool


def evaluate_candidate_on_probes(
    state: RisaState,
    candidate_id: str,
    probes: list[ApplicabilityProbe],
    *,
    partition: str,
    development_probes: list[ApplicabilityProbe] | None = None,
    baseline_outputs: list[bool] | None = None,
    bootstrap_samples: int = 1000,
    seed: int = 0,
    minimum_gain: float = 0.05,
    enable_ancestor_dormancy: bool = True,
) -> dict[str, object]:
    """Evaluate applicability with independent labels; return the label budget and decision.

    The default baseline abstains. A non-abstaining baseline must be supplied as one
    prediction per probe, fixed before scoring this candidate.
    """
    if partition not in {"development", "final"}:
        raise ValueError("partition must be 'development' or 'final'")
    if not probes or bootstrap_samples < 100:
        raise ValueError("nonempty probes and at least 100 bootstrap samples are required")
    ids = [probe.id for probe in probes]
    if len(set(ids)) != len(ids) or set(ids) & set(state.events_by_id):
        raise ValueError("probe IDs must be unique and absent from learned Events")
    if len({probe.episode_id for probe in probes}) < 2 or len({probe.source for probe in probes}) < 2:
        raise ValueError("probes need independent episodes and sources")
    if baseline_outputs is None:
        baseline_outputs = [False] * len(probes)
    if len(baseline_outputs) != len(probes):
        raise ValueError("baseline output count differs from probe count")
    candidate = state.unnamed_concept_candidates[candidate_id]
    if partition == "final":
        if development_probes is None or {
            probe.id for probe in development_probes
        } != set(candidate.development_evaluation_event_ids):
            raise ValueError("final evaluation requires the recorded development probe panel")
        if ({probe.id for probe in probes} & {probe.id for probe in development_probes}
                or {probe.episode_id for probe in probes}
                & {probe.episode_id for probe in development_probes}
                or {probe.source for probe in probes}
                & {probe.source for probe in development_probes}):
            raise ValueError("final probes must be disjoint from development probes")
    lineage = [candidate_id]
    protected_events = set()
    while lineage:
        current = state.unnamed_concept_candidates[lineage.pop()]
        protected_events.update(current.supporting_event_ids)
        lineage.extend(current.parent_candidate_ids)
    evidence = [state.events_by_id[item] for item in protected_events if item in state.events_by_id]
    if ({probe.episode_id for probe in probes} & {event.episode_id for event in evidence}
            or {probe.source for probe in probes} & {event.source for event in evidence}):
        raise ValueError("probe episodes and sources must be disjoint from candidate ancestry")
    candidate_output = [
        _candidate_context_matches(candidate, probe.context_tags) for probe in probes
    ]
    expected = [probe.expected_applicable for probe in probes]
    candidate_correct = [int(value == truth) for value, truth in zip(candidate_output, expected)]
    baseline_correct = [int(value == truth) for value, truth in zip(baseline_outputs, expected)]
    baseline_delta, baseline_lower = _paired_gain(
        candidate_correct, baseline_correct, bootstrap_samples, seed
    )
    negatives = [index for index, truth in enumerate(expected) if not truth]
    false_delta = (
        sum(int(candidate_output[index]) - int(baseline_outputs[index]) for index in negatives)
        / len(negatives) if negatives else 0.0
    )
    common = dict(
        partition=partition,
        evaluation_event_ids=ids,
        prediction_delta=baseline_delta,
        composition_delta=0.0,
        prediction_delta_ci_lower=baseline_lower,
        composition_delta_ci_lower=0.0,
        false_generalization_delta=false_delta,
        minimum_gain=minimum_gain,
    )
    parent_delta = parent_lower = None
    if candidate.derivation_generation:
        parents = [state.unnamed_concept_candidates[item] for item in candidate.parent_candidate_ids]
        if not parents:
            raise ValueError("derived candidate has no parents")
        parent_rows = [
            [int(_candidate_context_matches(parent, probe.context_tags) == truth)
             for probe, truth in zip(probes, expected)]
            for parent in parents
        ]
        strongest_index = max(range(len(parents)), key=lambda index: sum(parent_rows[index]))
        strongest = parent_rows[strongest_index]
        parent_delta, parent_lower = _paired_gain(
            candidate_correct, strongest, bootstrap_samples, seed + 1
        )
        # Derived false generalization is controlled against its strongest parent.
        parent_false = sum(
            int(_candidate_context_matches(parents[strongest_index], probes[index].context_tags))
            for index in negatives
        )
        false_delta = (
            (sum(int(candidate_output[index]) for index in negatives) - parent_false)
            / len(negatives) if negatives else 0.0
        )
        common["false_generalization_delta"] = false_delta
        evaluated = evaluate_derived_candidate(
            state, candidate_id, **common,
            parent_prediction_delta=parent_delta,
            parent_composition_delta=0.0,
            parent_prediction_delta_ci_lower=parent_lower,
            parent_composition_delta_ci_lower=0.0,
            enable_ancestor_dormancy=enable_ancestor_dormancy,
        )
    else:
        evaluated = evaluate_unnamed_candidate(state, candidate_id, **common)
    return {
        "candidate_id": candidate_id,
        "partition": partition,
        "status": evaluated.lifecycle_status,
        "supervised_labels": len(probes),
        "candidate_accuracy": sum(candidate_correct) / len(probes),
        "baseline_accuracy": sum(baseline_correct) / len(probes),
        "baseline_delta": baseline_delta,
        "baseline_ci_lower": baseline_lower,
        "parent_delta": parent_delta,
        "parent_ci_lower": parent_lower,
        "false_generalization_delta": false_delta,
    }


def _paired_gain(
    left: list[int], right: list[int], samples: int, seed: int
) -> tuple[float, float]:
    differences = [a - b for a, b in zip(left, right)]
    rng = random.Random(seed)
    estimates = sorted(
        sum(differences[rng.randrange(len(differences))] for _ in differences)
        / len(differences)
        for _ in range(samples)
    )
    return sum(differences) / len(differences), estimates[int(samples * 0.025)]
