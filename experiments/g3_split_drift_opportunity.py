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
from risa.evaluation.drift_metrics import snapshot_mechanisms
from risa.evaluation.drift_runner import DriftProbe, probe_success, run_drift_phase
from risa.evaluation.replay_diagnostics import contextual_replay_errors
from risa.evaluation.readout_attribution import attribute_prediction_readout


def _events(seed: int, phase: str, count: int, contextual_drift: bool = False) -> list[Event]:
    if count < 2 or count % 2:
        raise ValueError("phase observation count must be positive and even")
    tags = ["indoor", "outdoor"] * (count // 2)
    random.Random(f"{seed}:{phase}").shuffle(tags)
    start = {"A1": 1, "B": 100, "A2": 200}[phase]
    return [Event(
        id=f"{phase}:{seed}:{index}", timestamp=start + index,
        actor=f"actor:{seed}", action="inspect", target=f"device:{seed}",
        target_roles=["device"], context_tags=[tag],
        observed_effects=[
            "cold" if phase == "B" and (not contextual_drift or tag == "indoor")
            else "warm"
        ],
        episode_id=f"{phase}:episode:{seed}:{index}",
        source=f"{phase}:source:{seed}:{index}",
    ) for index, tag in enumerate(tags)]


def _probes(seed: int, phase: str, contextual_drift: bool = False) -> list[DriftProbe]:
    return [DriftProbe(
        id=f"probe:{phase}:{seed}:{index}",
        query=PredictionQuery(
            actor=f"actor:{seed}", action="inspect", target=f"device:{seed}",
            target_roles=["device"], context_tags=[tag],
        ),
        expected_effects=(
            "cold" if phase == "B" and (not contextual_drift or tag == "indoor")
            else "warm",
        ),
    ) for index, tag in enumerate(("indoor", "outdoor", "indoor", "outdoor"))]


def run_split_opportunity(manifest: dict) -> dict:
    rows = []
    contextual_drift = bool(manifest.get("contextual_drift", False))
    arms = [("split_on", True, False), ("split_off", False, False)]
    if manifest.get("include_contextual_proposal", False):
        arms.insert(1, ("contextual_split", True, True))
    for seed in manifest["seeds"]:
        a1 = _events(seed, "A1", int(manifest["a1_observations"]), contextual_drift)
        b = _events(seed, "B", int(manifest["phase_observations"]), contextual_drift)
        a2 = _events(seed, "A2", int(manifest["phase_observations"]), contextual_drift)
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
            a_probes = _probes(seed, "A", contextual_drift)
            b_probes = _probes(seed, "B", contextual_drift)
            protected = {probe.id for probe in a_probes + b_probes}
            a1_accuracy = probe_success(state, a_probes)
            b_result = run_drift_phase(
                state, b, b_probes, options, reference_accuracy=1.0,
                replay_interval=int(manifest["replay_interval"]),
                recovery_window=int(manifest["recovery_window"]),
                protected_probe_ids=protected,
            )
            b_replay_diagnostic = contextual_replay_errors(
                state, max_events=int(manifest["replay_max_events"])
            )
            b_split_variants = sorted(
                {tuple(sorted(primitive.context_tags))
                 for primitive in state.structural_primitives.values()
                 if "::context:" in primitive.id}
            )
            b_readout_on_a = attribute_prediction_readout(state, a_probes)
            b_readout_on_b = attribute_prediction_readout(state, b_probes)
            a2_entry_accuracy = probe_success(state, a_probes)
            a2_result = run_drift_phase(
                state, a2, a_probes, options, reference_accuracy=a1_accuracy,
                replay_interval=int(manifest["replay_interval"]),
                recovery_window=int(manifest["recovery_window"]),
                replay_offset=len(b), protected_probe_ids=protected,
            )
            mechanisms = snapshot_mechanisms(state)
            a2_readout_on_a = attribute_prediction_readout(state, a_probes)
            rows.append({
                "seed": seed, "arm": arm,
                "contextual_drift": contextual_drift,
                "contextual_proposal_enabled": contextual_proposal,
                "a1_accuracy": a1_accuracy,
                "retention_after_return": (
                    a2_entry_accuracy / a1_accuracy if a1_accuracy else None
                ),
                "B_recovery_events": b_result["recovery_events"],
                "A2_recovery_events": a2_result["recovery_events"],
                "B_adaptation_touch_ratio": b_result["adaptation"]["adaptation_touch_ratio"],
                "A2_adaptation_touch_ratio": a2_result["adaptation"]["adaptation_touch_ratio"],
                "B_replay_cost_per_recovery": b_result["replay_cost_per_recovery"],
                "A2_replay_cost_per_recovery": a2_result["replay_cost_per_recovery"],
                "B_mechanism_trace": b_result["mechanism_trace"],
                "A2_mechanism_trace": a2_result["mechanism_trace"],
                "B_contextual_replay_diagnostic": b_replay_diagnostic,
                "B_split_variant_contexts": [list(tags) for tags in b_split_variants],
                "B_readout_on_A_probes": b_readout_on_a,
                "B_readout_on_B_probes": b_readout_on_b,
                "A2_readout_on_A_probes": a2_readout_on_a,
                "final_executed_context_splits": len(mechanisms.executed_context_splits),
            })
    return {
        "benchmark_version": manifest["benchmark_version"],
        "manifest_sha256": hashlib.sha256(
            json.dumps(manifest, sort_keys=True).encode()
        ).hexdigest(),
        "status": "development_opportunity_only",
        "rows": rows,
    }


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
