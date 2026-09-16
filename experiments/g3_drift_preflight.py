"""Development-only G3.2 opportunity audit; never an adoption result."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random

from risa.core.models import Event, PredictionQuery
from risa.core.state import RisaState
from risa.engine.candidate_lifecycle import capture_context_conditions
from risa.engine.runtime import TrainingOptions, train_events
from risa.evaluation.drift_metrics import snapshot_mechanisms
from risa.evaluation.drift_runner import DriftProbe, run_aba


ARMS = {
    "full": (True, True, True),
    "split_only": (True, False, False),
    "merge_only": (False, True, False),
    "no_split": (False, True, True),
    "no_merge": (True, False, True),
    "no_dormancy": (True, True, False),
    "none": (False, False, False),
}


def run_preflight(manifest: dict) -> dict:
    if set(manifest["arms"]) != set(ARMS):
        raise ValueError("preflight requires all seven fixed arms")
    rows = []
    for seed in manifest["seeds"]:
        a1 = _events(seed, "A1", 6)
        reference = train_events(
            RisaState(), a1,
            TrainingOptions(enable_replay=False, enable_metabolism=False),
        )
        frozen = capture_context_conditions(reference)
        if not frozen:
            raise ValueError("fixture did not create A1 specialization scopes")
        b = _events(seed, "B", int(manifest["phase_observations"]))
        a2 = _events(seed, "A2", int(manifest["phase_observations"]))
        a_probes = _probes(seed, "A", int(manifest["probes_per_phase"]))
        b_probes = _probes(seed, "B", int(manifest["probes_per_phase"]))
        for arm in manifest["arms"]:
            split, merge, dormancy = ARMS[arm]
            options = TrainingOptions(
                enable_metabolism=False,
                enable_replay=True,
                enable_context_split=split,
                enable_candidate_specialization=split,
                enable_candidate_merge=merge,
                frozen_context_conditions=frozen if not split else None,
                replay_max_events=int(manifest["replay_max_events"]),
            )
            # Each arm receives the same A1 Events; only discovery policy varies.
            state = train_events(
                RisaState(), a1,
                TrainingOptions(
                    enable_metabolism=False, enable_replay=False,
                    enable_context_split=split,
                    enable_candidate_specialization=split,
                    enable_candidate_merge=merge,
                    frozen_context_conditions=frozen if not split else None,
                ),
            )
            a1_mechanisms = snapshot_mechanisms(state)
            result = run_aba(
                state, b, a2, a_probes, b_probes, options,
                replay_interval=int(manifest["replay_interval"]),
                recovery_window=int(manifest["recovery_window"]),
            )
            final_mechanisms = snapshot_mechanisms(state)
            rows.append({
                "seed": seed,
                "arm": arm,
                "split_enabled": split,
                "merge_enabled": merge,
                "dormancy_enabled": dormancy,
                "a1_merged_proposals": len(a1_mechanisms.merged_proposals),
                "final_merged_proposals": len(final_mechanisms.merged_proposals),
                "final_adopted_merges": len(final_mechanisms.adopted_merges),
                "final_dormant_candidates": len(final_mechanisms.dormant_candidates),
                "a1_accuracy": result["a1_accuracy"],
                "retention_after_return": result["retention_after_return"],
                "B_recovery_events": result["B"]["recovery_events"],
                "A2_recovery_events": result["A2"]["recovery_events"],
                "B_adaptation_touch_ratio": result["B"]["adaptation"]["adaptation_touch_ratio"],
                "A2_adaptation_touch_ratio": result["A2"]["adaptation"]["adaptation_touch_ratio"],
                "B_replay_cost_per_recovery": result["B"]["replay_cost_per_recovery"],
                "A2_replay_cost_per_recovery": result["A2"]["replay_cost_per_recovery"],
                "B_mechanisms": result["B"]["mechanisms"],
                "A2_mechanisms": result["A2"]["mechanisms"],
            })
    informative = all(
        any(row["final_adopted_merges"] > 0 for row in rows if row["arm"] == arm)
        for arm in ("full", "merge_only")
    ) and any(row["final_dormant_candidates"] > 0 for row in rows)
    return {
        "benchmark_version": manifest["benchmark_version"],
        "manifest_sha256": hashlib.sha256(
            json.dumps(manifest, sort_keys=True).encode()
        ).hexdigest(),
        "status": "development_preflight_only",
        "mechanism_opportunity_gate": "pass" if informative else "fail",
        "rows": rows,
    }


def _events(seed: int, phase: str, count: int) -> list[Event]:
    if count % 3:
        raise ValueError("phase observation count must be divisible by three")
    contexts = ["indoor", "sheltered", "outdoor"] * (count // 3)
    if phase != "A1":
        random.Random(f"{seed}:{phase}").shuffle(contexts)
    start = {"A1": 1, "B": 100, "A2": 200}[phase]
    events = []
    for index, context in enumerate(contexts):
        a_effect = "cold" if context == "outdoor" else "warm"
        effect = ("warm" if a_effect == "cold" else "cold") if phase == "B" else a_effect
        events.append(Event(
            id=f"{phase}:{seed}:{index}", timestamp=start + index,
            actor=f"actor:{phase}:{index}", action="inspect",
            target=f"device:{phase}:{index}", target_roles=["device"],
            context_tags=[context], observed_effects=[effect],
            episode_id=f"episode:{phase}:{seed}:{index}",
            source=f"sensor:{phase}:{index}",
        ))
    return events


def _probes(seed: int, phase: str, count: int) -> list[DriftProbe]:
    if count % 3:
        raise ValueError("probe count must be divisible by three")
    contexts = ["indoor", "sheltered", "outdoor"] * (count // 3)
    random.Random(f"{seed}:probe:{phase}").shuffle(contexts)
    probes = []
    for index, context in enumerate(contexts):
        a_effect = "cold" if context == "outdoor" else "warm"
        effect = ("warm" if a_effect == "cold" else "cold") if phase == "B" else a_effect
        probes.append(DriftProbe(
            id=f"probe:{phase}:{seed}:{index}",
            query=PredictionQuery(
                actor=f"probe-actor:{index}", action="inspect",
                target=f"probe-device:{index}", target_roles=["device"],
                context_tags=[context],
            ),
            expected_effects=(effect,),
        ))
    return probes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="experiments/g3_drift_preflight_manifest.json")
    parser.add_argument("--output", default="docs/g3-drift-preflight-results.json")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    result = run_preflight(manifest)
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": args.output, "rows": len(result["rows"]),
                      "opportunity_gate": result["mechanism_opportunity_gate"]}))


if __name__ == "__main__":
    main()
