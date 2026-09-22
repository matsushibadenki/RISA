"""Development-only A→B→A split opportunity; candidate lifecycle is held off."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random

from risa.core.models import Event, PredictionQuery
from risa.core.state import RisaState
from risa.engine.runtime import TrainingOptions, train_events
from risa.evaluation.drift_metrics import retention_adaptation_audit, snapshot_mechanisms
from risa.evaluation.drift_runner import (
    DriftProbe, probe_return_identifiability, probe_success, run_drift_phase,
)
from risa.evaluation.replay_diagnostics import contextual_replay_errors
from risa.evaluation.readout_attribution import attribute_prediction_readout
from risa.evaluation.grounded_role_baseline import (
    GroundedRoleCountBaseline, run_grounded_role_aba,
)
from risa.evaluation.split_variant_validation import audit_split_variants_on_probes


def _latent_effect(phase: str, tag: str, contextual_drift: bool) -> str:
    return "cold" if phase == "B" and (not contextual_drift or tag == "indoor") else "warm"


def _context_tags(tag: str, phase: str, phase_context_cue: bool) -> list[str]:
    return [tag, "regime:B" if phase == "B" else "regime:A"] if phase_context_cue else [tag]


def _events(
    seed: int, phase: str, count: int, contextual_drift: bool = False,
    observation_noise_fraction: float = 0.0, phase_context_cue: bool = False,
) -> list[Event]:
    if count < 2 or count % 2:
        raise ValueError("phase observation count must be positive and even")
    if not 0 <= observation_noise_fraction < 0.5:
        raise ValueError("observation noise fraction must be in [0, 0.5)")
    tags = ["indoor", "outdoor"] * (count // 2)
    random.Random(f"{seed}:{phase}").shuffle(tags)
    noisy_indices: set[int] = set()
    if phase != "A1":
        for tag in ("indoor", "outdoor"):
            indices = [index for index, value in enumerate(tags) if value == tag]
            noisy_count = observation_noise_fraction * len(indices)
            if not noisy_count.is_integer():
                raise ValueError("noise fraction must yield an exact count per context")
            random.Random(f"{seed}:{phase}:{tag}:noise").shuffle(indices)
            noisy_indices.update(indices[:int(noisy_count)])
    start = {"A1": 1, "B": 100, "A2": 200}[phase]
    return [Event(
        id=f"{phase}:{seed}:{index}", timestamp=start + index,
        actor=f"actor:{seed}", action="inspect", target=f"device:{seed}",
        target_roles=["device"], context_tags=_context_tags(tag, phase, phase_context_cue),
        observed_effects=[
            ("warm" if _latent_effect(phase, tag, contextual_drift) == "cold" else "cold")
            if index in noisy_indices else _latent_effect(phase, tag, contextual_drift)
        ],
        episode_id=f"{phase}:episode:{seed}:{index}",
        source=f"{phase}:source:{seed}:{index}",
    ) for index, tag in enumerate(tags)]


def _probes(
    seed: int, phase: str, contextual_drift: bool = False,
    phase_context_cue: bool = False,
) -> list[DriftProbe]:
    return [DriftProbe(
        id=f"probe:{phase}:{seed}:{index}",
        query=PredictionQuery(
            actor=f"actor:{seed}", action="inspect", target=f"device:{seed}",
            target_roles=["device"], context_tags=_context_tags(tag, phase, phase_context_cue),
        ),
        expected_effects=(_latent_effect(phase, tag, contextual_drift),),
    ) for index, tag in enumerate(("indoor", "outdoor", "indoor", "outdoor"))]


def _transfer_probes(
    seed: int, phase: str, contextual_drift: bool, phase_context_cue: bool = False,
) -> list[DriftProbe]:
    return [DriftProbe(
        id=f"transfer:{phase}:{seed}:{index}",
        query=PredictionQuery(
            actor=f"unseen-actor:{seed}:{index}", action="inspect",
            target=f"unseen-device:{seed}:{index}", target_roles=["device"],
            context_tags=_context_tags(tag, phase, phase_context_cue),
        ),
        expected_effects=(_latent_effect(phase, tag, contextual_drift),),
    ) for index, tag in enumerate(("indoor", "outdoor", "indoor", "outdoor"))]


def _split_validation_probes(
    seed: int, contextual_drift: bool, phase_context_cue: bool,
    labels_per_context: int,
) -> list[DriftProbe]:
    if labels_per_context < 0:
        raise ValueError("split validation labels per context must be non-negative")
    return [DriftProbe(
        id=f"validation:B:{seed}:{tag}:{index}",
        query=PredictionQuery(
            actor=f"validation-actor:{seed}:{tag}:{index}", action="inspect",
            target=f"validation-device:{seed}:{tag}:{index}", target_roles=["device"],
            context_tags=_context_tags(tag, "B", phase_context_cue),
        ),
        expected_effects=(_latent_effect("B", tag, contextual_drift),),
    ) for tag in ("indoor", "outdoor") for index in range(labels_per_context)]


def _online_readout(state: RisaState, index: int, event: Event) -> dict[str, object]:
    probe = DriftProbe(
        event.id,
        PredictionQuery(
            actor=event.actor, action=event.action, target=event.target,
            context_tags=list(event.context_tags),
            actor_roles=list(event.actor_roles), target_roles=list(event.target_roles),
            entity_bindings=dict(event.entity_bindings),
            entity_relations=list(event.entity_relations),
        ),
        tuple(event.observed_effects),
    )
    return attribute_prediction_readout(state, [probe])


def _b_split_variant_audit(state: RisaState, contextual_drift: bool) -> dict[str, object]:
    """Classify B-scope split variants against the fixture's latent rule."""
    rows = []
    for primitive in state.structural_primitives.values():
        if "::context:" not in primitive.id:
            continue
        tags = set(primitive.context_tags)
        if "regime:a" in tags:
            continue
        location = next((tag for tag in ("indoor", "outdoor") if tag in tags), None)
        if location is None:
            continue
        expected = _latent_effect("B", location, contextual_drift)
        rows.append({
            "primitive_id": primitive.id,
            "context_tags": sorted(tags),
            "produced_states": sorted(primitive.produced_states),
            "support": primitive.support,
            "adopted": primitive.adopted,
            "matches_B_latent_rule": primitive.produced_states == {expected},
        })
    rows.sort(key=lambda row: row["primitive_id"])
    return {
        "B_scope_variants": len(rows),
        "adopted_off_rule_variants": sum(
            row["adopted"] and not row["matches_B_latent_rule"] for row in rows
        ),
        "rows": rows,
    }


def run_split_opportunity(manifest: dict) -> dict:
    rows = []
    baseline_rows = []
    count_baseline_rows = []
    contextual_drift = bool(manifest.get("contextual_drift", False))
    phase_context_cue = bool(manifest.get("phase_context_cue", False))
    noise_fraction = float(manifest.get("observation_noise_fraction", 0.0))
    split_validation_labels = int(manifest.get("split_validation_labels_per_context", 0))
    arms = [("split_on", True, False), ("split_off", False, False)]
    if manifest.get("include_contextual_proposal", False):
        arms.insert(1, ("contextual_split", True, True))
    for seed in manifest["seeds"]:
        a1 = _events(seed, "A1", int(manifest["a1_observations"]), contextual_drift,
                     phase_context_cue=phase_context_cue)
        b = _events(seed, "B", int(manifest["phase_observations"]), contextual_drift,
                    noise_fraction, phase_context_cue)
        a2 = _events(seed, "A2", int(manifest["phase_observations"]), contextual_drift,
                     noise_fraction, phase_context_cue)
        baseline_rows.append({"seed": seed, **run_grounded_role_aba(
            a1, b, a2,
            _probes(seed, "A", contextual_drift, phase_context_cue),
            _probes(seed, "B", contextual_drift, phase_context_cue),
            _transfer_probes(seed, "A", contextual_drift, phase_context_cue),
            _transfer_probes(seed, "B", contextual_drift, phase_context_cue),
            recovery_window=int(manifest["recovery_window"]),
        )})
        count_baseline_rows.append({"seed": seed, **run_grounded_role_aba(
            a1, b, a2,
            _probes(seed, "A", contextual_drift, phase_context_cue),
            _probes(seed, "B", contextual_drift, phase_context_cue),
            _transfer_probes(seed, "A", contextual_drift, phase_context_cue),
            _transfer_probes(seed, "B", contextual_drift, phase_context_cue),
            recovery_window=int(manifest["recovery_window"]),
            model_factory=GroundedRoleCountBaseline,
        )})
        for arm, split, contextual_proposal in arms:
            options = TrainingOptions(
                enable_metabolism=False,
                enable_context_split=split,
                enable_contextual_split_proposal=contextual_proposal,
                enable_candidate_specialization=False,
                enable_candidate_merge=False,
                replay_max_events=int(manifest["replay_max_events"]),
            )
            state = train_events(
                RisaState(), a1,
                TrainingOptions(
                    enable_metabolism=False, enable_replay=False,
                    enable_context_split=split,
                    enable_contextual_split_proposal=contextual_proposal,
                    enable_candidate_specialization=False,
                    enable_candidate_merge=False,
                ),
            )
            a_probes = _probes(seed, "A", contextual_drift, phase_context_cue)
            b_probes = _probes(seed, "B", contextual_drift, phase_context_cue)
            protected = {probe.id for probe in a_probes + b_probes}
            a1_accuracy = probe_success(state, a_probes)
            a1_transfer_on_a = attribute_prediction_readout(
                state, _transfer_probes(seed, "A", contextual_drift, phase_context_cue)
            )
            b_result = run_drift_phase(
                state, b, b_probes, options, reference_accuracy=1.0,
                replay_interval=int(manifest["replay_interval"]),
                recovery_window=int(manifest["recovery_window"]),
                protected_probe_ids=protected,
                pre_update_diagnostic=_online_readout,
            )
            b_replay_diagnostic = contextual_replay_errors(
                state, max_events=int(manifest["replay_max_events"])
            )
            b_split_variants = sorted(
                {tuple(sorted(primitive.context_tags))
                 for primitive in state.structural_primitives.values()
                 if "::context:" in primitive.id}
            )
            b_split_variant_audit = _b_split_variant_audit(state, contextual_drift)
            b_split_heldout_validation = audit_split_variants_on_probes(
                state,
                _split_validation_probes(
                    seed, contextual_drift, phase_context_cue, split_validation_labels
                ),
                scoring_probe_ids=protected,
            )
            b_readout_on_a = attribute_prediction_readout(state, a_probes)
            b_readout_on_b = attribute_prediction_readout(state, b_probes)
            b_transfer_on_a = attribute_prediction_readout(
                state, _transfer_probes(seed, "A", contextual_drift, phase_context_cue)
            )
            b_transfer_on_b = attribute_prediction_readout(
                state, _transfer_probes(seed, "B", contextual_drift, phase_context_cue)
            )
            a2_entry_accuracy = probe_success(state, a_probes)
            retention_audit = retention_adaptation_audit(
                a1_accuracy=a1_accuracy, b_exit_accuracy=b_result["exit_accuracy"],
                a2_entry_accuracy=a2_entry_accuracy,
            )
            a2_result = run_drift_phase(
                state, a2, a_probes, options, reference_accuracy=a1_accuracy,
                replay_interval=int(manifest["replay_interval"]),
                recovery_window=int(manifest["recovery_window"]),
                replay_offset=len(b), protected_probe_ids=protected,
                pre_update_diagnostic=_online_readout,
            )
            mechanisms = snapshot_mechanisms(state)
            a2_readout_on_a = attribute_prediction_readout(state, a_probes)
            a2_transfer_on_a = attribute_prediction_readout(
                state, _transfer_probes(seed, "A", contextual_drift, phase_context_cue)
            )
            rows.append({
                "seed": seed, "arm": arm,
                "contextual_drift": contextual_drift,
                "phase_context_cue": phase_context_cue,
                "observation_noise_fraction": noise_fraction,
                "B_noisy_observations": _noise_count(b, "B", contextual_drift),
                "A2_noisy_observations": _noise_count(a2, "A2", contextual_drift),
                "contextual_proposal_enabled": contextual_proposal,
                "a1_accuracy": a1_accuracy,
                **retention_audit,
                "return_identifiability": probe_return_identifiability(a_probes, b_probes),
                "B_recovery_events": b_result["recovery_events"],
                "A2_recovery_events": a2_result["recovery_events"],
                "B_adaptation_touch_ratio": b_result["adaptation"]["adaptation_touch_ratio"],
                "A2_adaptation_touch_ratio": a2_result["adaptation"]["adaptation_touch_ratio"],
                "B_replay_cost_per_recovery": b_result["replay_cost_per_recovery"],
                "A2_replay_cost_per_recovery": a2_result["replay_cost_per_recovery"],
                "B_probe_accuracy_by_observed_events": b_result["probe_accuracy_by_observed_events"],
                "A2_probe_accuracy_by_observed_events": a2_result["probe_accuracy_by_observed_events"],
                "B_mechanism_trace": b_result["mechanism_trace"],
                "A2_mechanism_trace": a2_result["mechanism_trace"],
                "B_contextual_replay_diagnostic": b_replay_diagnostic,
                "B_split_variant_contexts": [list(tags) for tags in b_split_variants],
                "B_split_variant_audit": b_split_variant_audit,
                "B_split_heldout_validation": b_split_heldout_validation,
                "B_readout_on_A_probes": b_readout_on_a,
                "B_readout_on_B_probes": b_readout_on_b,
                "A2_readout_on_A_probes": a2_readout_on_a,
                "A1_transfer_on_A_probes": a1_transfer_on_a,
                "B_transfer_on_A_probes": b_transfer_on_a,
                "B_transfer_on_B_probes": b_transfer_on_b,
                "A2_transfer_on_A_probes": a2_transfer_on_a,
                "B_pre_update_readout_trace": b_result["pre_update_diagnostic_trace"],
                "A2_pre_update_readout_trace": a2_result["pre_update_diagnostic_trace"],
                "final_executed_context_splits": len(mechanisms.executed_context_splits),
            })
    return {
        "benchmark_version": manifest["benchmark_version"],
        "manifest_sha256": hashlib.sha256(
            json.dumps(manifest, sort_keys=True).encode()
        ).hexdigest(),
        "status": "development_opportunity_only",
        "grounded_role_baseline_rows": baseline_rows,
        "grounded_role_count_baseline_rows": count_baseline_rows,
        "rows": rows,
    }


def _noise_count(events: list[Event], phase: str, contextual_drift: bool) -> int:
    return sum(
        event.observed_effects != [
            _latent_effect(phase, event.context_tags[0], contextual_drift)
        ]
        for event in events
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="experiments/g3_split_drift_opportunity_manifest.json")
    parser.add_argument("--output", default="docs/g3-split-drift-opportunity-results.json")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    result = run_split_opportunity(manifest)
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"rows": len(result["rows"]), "output": args.output}))


if __name__ == "__main__":
    main()
