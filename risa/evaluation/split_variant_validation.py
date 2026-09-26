"""Read-only held-out label audit for context-split Primitive variants."""

from __future__ import annotations

from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label
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
