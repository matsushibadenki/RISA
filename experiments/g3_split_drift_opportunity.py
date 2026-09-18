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
from risa.evaluation.drift_runner import DriftProbe, run_aba


def _events(seed: int, phase: str, count: int) -> list[Event]:
    if count < 2 or count % 2:
        raise ValueError("phase observation count must be positive and even")
    tags = ["indoor", "outdoor"] * (count // 2)
    random.Random(f"{seed}:{phase}").shuffle(tags)
    effect = "cold" if phase == "B" else "warm"
    start = {"A1": 1, "B": 100, "A2": 200}[phase]
    return [Event(
        id=f"{phase}:{seed}:{index}", timestamp=start + index,
        actor=f"actor:{seed}", action="inspect", target=f"device:{seed}",
        target_roles=["device"], context_tags=[tag],
        observed_effects=[effect],
        episode_id=f"{phase}:episode:{seed}:{index}",
        source=f"{phase}:source:{seed}:{index}",
    ) for index, tag in enumerate(tags)]


def _probes(seed: int, phase: str) -> list[DriftProbe]:
    effect = "cold" if phase == "B" else "warm"
    return [DriftProbe(
        id=f"probe:{phase}:{seed}:{index}",
        query=PredictionQuery(
            actor=f"actor:{seed}", action="inspect", target=f"device:{seed}",
            target_roles=["device"], context_tags=[tag],
        ),
        expected_effects=(effect,),
    ) for index, tag in enumerate(("indoor", "outdoor", "indoor", "outdoor"))]


def run_split_opportunity(manifest: dict) -> dict:
    rows = []
    for seed in manifest["seeds"]:
        a1 = _events(seed, "A1", int(manifest["a1_observations"]))
        b = _events(seed, "B", int(manifest["phase_observations"]))
        a2 = _events(seed, "A2", int(manifest["phase_observations"]))
        for arm, split in (("split_on", True), ("split_off", False)):
            options = TrainingOptions(
                enable_metabolism=False,
                enable_context_split=split,
                enable_candidate_specialization=False,
                enable_candidate_merge=False,
                replay_max_events=int(manifest["replay_max_events"]),
            )
            state = train_events(
                RisaState(), a1,
                TrainingOptions(
                    enable_metabolism=False, enable_replay=False,
                    enable_context_split=split,
                    enable_candidate_specialization=False,
                    enable_candidate_merge=False,
                ),
            )
            outcome = run_aba(
                state, b, a2, _probes(seed, "A"), _probes(seed, "B"),
                options,
                replay_interval=int(manifest["replay_interval"]),
                recovery_window=int(manifest["recovery_window"]),
            )
            mechanisms = snapshot_mechanisms(state)
            rows.append({
                "seed": seed, "arm": arm,
                "a1_accuracy": outcome["a1_accuracy"],
                "retention_after_return": outcome["retention_after_return"],
                "B_recovery_events": outcome["B"]["recovery_events"],
                "A2_recovery_events": outcome["A2"]["recovery_events"],
                "B_adaptation_touch_ratio": outcome["B"]["adaptation"]["adaptation_touch_ratio"],
                "A2_adaptation_touch_ratio": outcome["A2"]["adaptation"]["adaptation_touch_ratio"],
                "B_replay_cost_per_recovery": outcome["B"]["replay_cost_per_recovery"],
                "A2_replay_cost_per_recovery": outcome["A2"]["replay_cost_per_recovery"],
                "B_mechanism_trace": outcome["B"]["mechanism_trace"],
                "A2_mechanism_trace": outcome["A2"]["mechanism_trace"],
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
