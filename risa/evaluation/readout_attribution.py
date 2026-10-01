"""Read-only counterfactual ablations of prediction readout components."""

from __future__ import annotations

import copy
from dataclasses import replace

from risa.core.state import RisaState
from risa.engine.candidate_discovery import rebuild_candidate_inference_index
from risa.engine.predictor import predict_next_effect
from risa.evaluation.drift_runner import DriftProbe


def attribute_prediction_readout(
    state: RisaState, probes: list[DriftProbe],
) -> dict[str, object]:
    """Compare fixed probes while removing one readout source at a time.

    This is a component intervention, not a Shapley or causal mediation score.
    The no-Primitive state is a disposable copy; original state is untouched.
    """
    if not probes or len({probe.id for probe in probes}) != len(probes):
        raise ValueError("nonempty probes with unique IDs are required")
    if {probe.id for probe in probes} & set(state.events_by_id):
        raise ValueError("scoring probes overlap learned Events")
    no_primitive = copy.deepcopy(state)
    no_primitive.structural_primitives.clear()
    variants = {
        "full": (state, False, False),
        "no_primitive": (no_primitive, False, False),
        "no_recent_outcome": (state, True, False),
        "no_candidate": (state, False, True),
        "no_primitive_no_recent": (no_primitive, True, False),
    }
    predictions = {}
    for name, (model, disable_recent, disable_candidate) in variants.items():
        predictions[name] = [
            predict_next_effect(model, replace(
                probe.query,
                enable_change_adaptation=(
                    probe.query.enable_change_adaptation and not disable_recent
                ),
                enable_candidate_concepts=(
                    probe.query.enable_candidate_concepts and not disable_candidate
                ),
            ))
            for probe in probes
        ]
    full = predictions["full"]
    rows = {}
    for name, results in predictions.items():
        correct = [
            sorted(result.predicted_effects) == sorted(probe.expected_effects)
            for result, probe in zip(results, probes)
        ]
        rows[name] = {
            "accuracy": sum(correct) / len(probes),
            "predictions_changed_vs_full": sum(
                sorted(result.predicted_effects) != sorted(reference.predicted_effects)
                for result, reference in zip(results, full)
            ),
            "mean_absolute_score_change_vs_full": round(
                sum(abs(result.score - reference.score)
                    for result, reference in zip(results, full)) / len(probes), 6
            ),
            "predicted_effects_by_probe": {
                probe.id: result.predicted_effects
                for probe, result in zip(probes, results)
            },
        }
    return {"probe_count": len(probes), "variants": rows}


def attribute_candidate_lifecycle_readout(
    state: RisaState, probes: list[DriftProbe],
) -> dict[str, object]:
    """Measure merge and dormancy readout effects on disposable states.

    ``without_adopted_merges`` removes adopted merged candidates while leaving
    their dormant ancestors untouched. ``reactivated_dormant_ancestors`` keeps
    the merge and reactivates only its dormant ancestors. Together these
    interventions distinguish dependence on the merged replacement from any
    prediction change caused by suppressing its replaced parents.
    """
    if not probes or len({probe.id for probe in probes}) != len(probes):
        raise ValueError("nonempty probes with unique IDs are required")
    if {probe.id for probe in probes} & set(state.events_by_id):
        raise ValueError("scoring probes overlap learned Events")

    adopted_merges = {
        candidate.id: candidate
        for candidate in state.unnamed_concept_candidates.values()
        if candidate.lifecycle_status == "adopted"
        and not candidate.dormant
        and candidate.derivation_type == "merged"
    }
    ancestor_ids = {
        parent_id
        for candidate in adopted_merges.values()
        for parent_id in candidate.parent_candidate_ids
        if parent_id in state.unnamed_concept_candidates
        and state.unnamed_concept_candidates[parent_id].dormant
    }

    without_merges = copy.deepcopy(state)
    for candidate_id in adopted_merges:
        without_merges.unnamed_concept_candidates[candidate_id].lifecycle_status = "proposed"
    rebuild_candidate_inference_index(without_merges)

    reactivated = copy.deepcopy(state)
    for candidate_id in ancestor_ids:
        reactivated.unnamed_concept_candidates[candidate_id].dormant = False
    rebuild_candidate_inference_index(reactivated)

    variants = {
        "full": state,
        "without_adopted_merges": without_merges,
        "reactivated_dormant_ancestors": reactivated,
    }
    predictions = {
        name: [predict_next_effect(model, probe.query) for probe in probes]
        for name, model in variants.items()
    }
    full = predictions["full"]
    rows = {}
    for name, results in predictions.items():
        correct = [
            sorted(result.predicted_effects) == sorted(probe.expected_effects)
            for result, probe in zip(results, probes)
        ]
        rows[name] = {
            "accuracy": sum(correct) / len(probes),
            "predictions_changed_vs_full": sum(
                sorted(result.predicted_effects) != sorted(reference.predicted_effects)
                for result, reference in zip(results, full)
            ),
            "mean_absolute_score_change_vs_full": round(
                sum(abs(result.score - reference.score)
                    for result, reference in zip(results, full)) / len(probes), 6
            ),
        }
    return {
        "probe_count": len(probes),
        "adopted_merge_count": len(adopted_merges),
        "dormant_ancestor_count": len(ancestor_ids),
        "variants": rows,
    }
