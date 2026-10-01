"""Read-only held-out label audit for context-split Primitive variants."""

from __future__ import annotations

import copy

from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label
from risa.engine.predictor import predict_next_effect
from risa.evaluation.drift_runner import DriftProbe


def audit_split_variants_on_probes(
    state: RisaState, probes: list[DriftProbe], *, scoring_probe_ids: set[str] | None = None,
) -> dict[str, object]:
    """Evaluate exact-context variants without updating adoption or learning state."""
    ids = [probe.id for probe in probes]
    if len(ids) != len(set(ids)):
        raise ValueError("validation probe IDs must be unique")
    forbidden = set(state.events_by_id) | (scoring_probe_ids or set())
    for candidate in state.unnamed_concept_candidates.values():
        forbidden.update(candidate.evaluation_event_ids)
        forbidden.update(candidate.development_evaluation_event_ids)
        forbidden.update(candidate.final_evaluation_event_ids)
    if set(ids) & forbidden:
        raise ValueError("validation probes overlap learning or scoring evidence")

    rows = []
    consumed_ids: set[str] = set()
    for primitive in sorted(state.structural_primitives.values(), key=lambda item: item.id):
        if "::context:" not in primitive.id:
            continue
        actions = {
            condition.removeprefix("process:")
            for condition in primitive.input_conditions
            if condition.startswith("process:")
        }
        matching = [
            probe for probe in probes
            if normalize_label(probe.query.action) in actions
            and {normalize_label(tag) for tag in probe.query.context_tags}
            == primitive.context_tags
        ]
        if not matching:
            continue
        consumed_ids.update(probe.id for probe in matching)
        outcome = tuple(sorted(primitive.produced_states))
        correct = sum(
            outcome == tuple(sorted(normalize_label(effect) for effect in probe.expected_effects))
            for probe in matching
        )
        rows.append({
            "primitive_id": primitive.id,
            "context_tags": sorted(primitive.context_tags),
            "produced_states": list(outcome),
            "adopted": primitive.adopted,
            "training_support": primitive.support,
            "heldout_labels": len(matching),
            "heldout_correct": correct,
            "heldout_accuracy": correct / len(matching),
        })
    return {
        "available_labels": len(probes),
        "consumed_labels": len(consumed_ids),
        "variant_evaluations": len(rows),
        "adopted_variants_failing_heldout": sum(
            row["adopted"] and row["heldout_correct"] < row["heldout_labels"]
            for row in rows
        ),
        "adopted_variants_passing_heldout": sum(
            row["adopted"] and row["heldout_correct"] == row["heldout_labels"]
            for row in rows
        ),
        "rows": rows,
    }


def counterfactual_validation_gate_effect(
    state: RisaState,
    validation_probes: list[DriftProbe],
    scoring_probes: list[DriftProbe],
) -> dict[str, object]:
    """Measure predictions after rejecting held-out failures on a disposable state copy."""
    if not scoring_probes or len({probe.id for probe in scoring_probes}) != len(scoring_probes):
        raise ValueError("nonempty scoring probes with unique IDs are required")
    if {probe.id for probe in validation_probes} & {probe.id for probe in scoring_probes}:
        raise ValueError("validation and scoring probes must be disjoint")
    audit = audit_split_variants_on_probes(
        state, validation_probes,
        scoring_probe_ids={probe.id for probe in scoring_probes},
    )
    rejected = sorted(
        row["primitive_id"] for row in audit["rows"]
        if row["adopted"] and row["heldout_correct"] < row["heldout_labels"]
    )
    gated = copy.deepcopy(state)
    for primitive_id in rejected:
        gated.structural_primitives[primitive_id].adopted = False

    before = [predict_next_effect(state, probe.query) for probe in scoring_probes]
    after = [predict_next_effect(gated, probe.query) for probe in scoring_probes]
    expected = [tuple(sorted(probe.expected_effects)) for probe in scoring_probes]
    return {
        "validation": audit,
        "rejected_variant_ids": rejected,
        "scoring_probe_count": len(scoring_probes),
        "predictions_changed": sum(
            tuple(sorted(left.predicted_effects)) != tuple(sorted(right.predicted_effects))
            for left, right in zip(before, after)
        ),
        "accuracy_before": sum(
            tuple(sorted(result.predicted_effects)) == target
            for result, target in zip(before, expected)
        ) / len(scoring_probes),
        "accuracy_after": sum(
            tuple(sorted(result.predicted_effects)) == target
            for result, target in zip(after, expected)
        ) / len(scoring_probes),
    }
