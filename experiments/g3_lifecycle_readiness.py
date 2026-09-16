"""Development-only opportunity check for merge adoption and ancestor dormancy."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from experiments.g3_drift_preflight import _events
from risa.core.state import RisaState
from risa.engine.candidate_discovery import (
    matching_adopted_candidates,
    select_derived_candidates_for_final,
)
from risa.engine.runtime import TrainingOptions, train_events
from risa.evaluation.candidate_adoption import ApplicabilityProbe, evaluate_candidate_on_probes
from risa.evaluation.drift_metrics import snapshot_mechanisms


def _panel(seed: int, name: str, count: int) -> list[ApplicabilityProbe]:
    contexts = ("indoor", "sheltered", "outdoor", "exposed")
    return [
        ApplicabilityProbe(
            id=f"{name}:{seed}:{index}",
            episode_id=f"{name}:episode:{seed}:{index}",
            source=f"{name}:source:{seed}:{index % 2}",
            context_tags=(contexts[index % 4],),
            expected_applicable=contexts[index % 4] in {"indoor", "sheltered"},
        )
        for index in range(count)
    ]


def run_lifecycle_readiness(manifest: dict) -> dict:
    count = int(manifest["probes_per_partition"])
    if count < 4 or count % 4:
        raise ValueError("probes_per_partition must be a positive multiple of four")
    rows = []
    for seed in manifest["seeds"]:
        state = train_events(
            RisaState(), _events(seed, "A1", 6),
            TrainingOptions(enable_replay=False, enable_metabolism=False),
        )
        merged = next(
            candidate for candidate in state.unnamed_concept_candidates.values()
            if candidate.derivation_type == "merged"
        )
        parents = [state.unnamed_concept_candidates[item] for item in merged.parent_candidate_ids]
        for candidate in parents + [merged]:
            development = _panel(seed, f"{candidate.id}:development", count)
            final = _panel(seed, f"{candidate.id}:final", count)
            dev_result = evaluate_candidate_on_probes(
                state, candidate.id, development, partition="development",
                bootstrap_samples=int(manifest["bootstrap_samples"]), seed=seed,
            )
            if dev_result["status"] != "provisional":
                raise ValueError(f"development rejected {candidate.id}")
            select_derived_candidates_for_final(state, [candidate.id])
            if candidate.id == merged.id:
                for dormancy in (True, False):
                    arm_state = copy.deepcopy(state)
                    final_result = evaluate_candidate_on_probes(
                        arm_state, candidate.id, final, partition="final",
                        development_probes=development,
                        bootstrap_samples=int(manifest["bootstrap_samples"]), seed=seed + 1,
                        enable_ancestor_dormancy=dormancy,
                    )
                    mechanism = snapshot_mechanisms(arm_state)
                    rows.append({
                        "seed": seed,
                        "arm": "dormancy_on" if dormancy else "dormancy_off",
                        "merged_status": final_result["status"],
                        "adopted_parent_count_before_merge": len(parents),
                        "dormant_parent_count": sum(
                            arm_state.unnamed_concept_candidates[parent.id].dormant
                            for parent in parents
                        ),
                        "active_adopted_merges": len(mechanism.adopted_merges),
                        "indoor_matching_candidates": len(matching_adopted_candidates(
                            arm_state, "inspect", ["device"], ["indoor"]
                        )),
                        "supervised_labels_per_arm": count * 6,
                        "merge_final_gain_over_parent": final_result["parent_delta"],
                        "merge_final_parent_ci_lower": final_result["parent_ci_lower"],
                    })
                break
            final_result = evaluate_candidate_on_probes(
                state, candidate.id, final, partition="final",
                development_probes=development,
                bootstrap_samples=int(manifest["bootstrap_samples"]), seed=seed + 1,
            )
            if final_result["status"] != "adopted":
                raise ValueError(f"parent adoption failed for {candidate.id}")
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
    parser.add_argument("--manifest", default="experiments/g3_lifecycle_readiness_manifest.json")
    parser.add_argument("--output", default="docs/g3-lifecycle-readiness-results.json")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    result = run_lifecycle_readiness(manifest)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(result["rows"]), "output": args.output}))


if __name__ == "__main__":
    main()
