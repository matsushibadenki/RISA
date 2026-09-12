"""Evaluate automatic context derivation against its parent on held-out cases."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
from typing import Any

from risa.core.models import Event
from risa.core.state import RisaState
from risa.engine.candidate_discovery import (
    _candidate_context_matches,
    evaluate_derived_candidate,
    rebuild_candidate_inference_index,
)
from risa.engine.runtime import TrainingOptions, train_events


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("development_episodes_per_seed", "final_episodes_per_seed", "bootstrap_samples"):
        if int(manifest[key]) < 1:
            raise ValueError(f"{key} must be positive")
    return manifest


def run_derived_candidate_evaluation(manifest: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    lifecycle: list[dict[str, Any]] = []
    for raw_seed in manifest["seeds"]:
        seed = int(raw_seed)
        state, broad_ancestor_id, parent_id, derived_id = _training_state(seed)
        partitions = {
            "development": _cases(seed, "development", int(manifest["development_episodes_per_seed"])),
            "final": _cases(seed, "final", int(manifest["final_episodes_per_seed"])),
        }
        record = {"seed": seed, "candidate_id": derived_id, "parent_id": parent_id}
        for offset, (partition, cases) in enumerate(partitions.items()):
            metrics = _compare(
                state, broad_ancestor_id, parent_id, derived_id, cases
            )
            baseline_interval = _paired_bootstrap_interval(
                metrics["derived_successes"], metrics["baseline_successes"],
                int(manifest["bootstrap_samples"]), seed + offset,
            )
            parent_interval = _paired_bootstrap_interval(
                metrics["derived_successes"], metrics["parent_successes"],
                int(manifest["bootstrap_samples"]), seed + 100 + offset,
            )
            evaluate_derived_candidate(
                state,
                derived_id,
                partition=partition,
                evaluation_event_ids=[str(case["id"]) for case in cases],
                prediction_delta=metrics["baseline_delta"],
                composition_delta=0.0,
                prediction_delta_ci_lower=baseline_interval[0],
                composition_delta_ci_lower=0.0,
                false_generalization_delta=metrics["false_generalization_delta"],
                parent_prediction_delta=metrics["parent_delta"],
                parent_composition_delta=0.0,
                parent_prediction_delta_ci_lower=parent_interval[0],
                parent_composition_delta_ci_lower=0.0,
                minimum_gain=float(manifest["minimum_gain"]),
            )
            record[f"after_{partition}"] = state.unnamed_concept_candidates[derived_id].lifecycle_status
            rows.append({
                "seed": seed,
                "partition": partition,
                "episodes": len(cases),
                "derived_success_rate": _mean(metrics["derived_successes"]),
                "parent_success_rate": _mean(metrics["parent_successes"]),
                "baseline_success_rate": _mean(metrics["baseline_successes"]),
                "broad_ancestor_success_rate": _mean(
                    metrics["broad_ancestor_successes"]
                ),
                "derived_vs_parent_delta": metrics["parent_delta"],
                "derived_vs_parent_95ci": list(parent_interval),
                "derived_false_generalization_rate": metrics["derived_false_rate"],
                "parent_false_generalization_rate": metrics["parent_false_rate"],
                "broad_ancestor_false_generalization_rate": metrics[
                    "broad_ancestor_false_rate"
                ],
            })
        record["broad_ancestor_dormant_after_final"] = state.unnamed_concept_candidates[
            broad_ancestor_id
        ].dormant
        lifecycle.append(record)
    return {
        "benchmark_version": manifest["benchmark_version"],
        "manifest_sha256": hashlib.sha256(
            json.dumps(manifest, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "manifest": manifest,
        "rows": rows,
        "aggregate": _aggregate(rows),
        "lifecycle": lifecycle,
        "decision": "adopt" if all(row["after_final"] == "adopted" for row in lifecycle) else "reject",
    }


def _training_state(seed: int) -> tuple[RisaState, str, str, str]:
    state = RisaState()
    observations = (
        ("indoor-a", "indoor", "warm"),
        ("indoor-b", "indoor", "warm"),
        ("sheltered-a", "sheltered", "warm"),
        ("sheltered-b", "sheltered", "warm"),
        ("outdoor-a", "outdoor", "cold"),
        ("outdoor-b", "outdoor", "cold"),
    )
    train_events(state, [
        Event(
            id=f"support:{seed}:{name}", timestamp=index,
            actor=f"trainer-{index}", action="inspect", target=f"device-{index}",
            target_roles=["heating_device"], context_tags=[context],
            observed_effects=[effect], episode_id=f"support:{seed}:{index}",
            source=f"sensor-{index}",
        )
        for index, (name, context, effect) in enumerate(observations, 1)
    ], options=TrainingOptions(
        enable_metabolism=False, enable_replay=False,
        enable_adaptation=False, enable_coactivation=False,
    ))
    broad_ancestor = next(
        candidate for candidate in state.unnamed_concept_candidates.values()
        if candidate.derivation_generation == 0
        and candidate.structural_schema.get("effects") == ["warm"]
    )
    merged = next(
        candidate for candidate in state.unnamed_concept_candidates.values()
        if candidate.derivation_type == "merged"
        and len(candidate.parent_candidate_ids) == 2
    )
    parent = state.unnamed_concept_candidates[merged.parent_candidate_ids[0]]
    broad_ancestor.lifecycle_status = "adopted"
    rebuild_candidate_inference_index(state)
    return state, broad_ancestor.id, parent.id, merged.id


def _cases(seed: int, partition: str, count: int) -> list[dict[str, object]]:
    variants = (("indoor", True), ("sheltered", True), ("outdoor", False), ("exposed", False))
    rng = random.Random(f"{seed}:{partition}")
    order = [variants[index % len(variants)] for index in range(count)]
    rng.shuffle(order)
    return [
        {"id": f"{partition}:{seed}:{index}", "context": context, "expected": expected}
        for index, (context, expected) in enumerate(order)
    ]


def _compare(
    state: RisaState,
    broad_ancestor_id: str,
    parent_id: str,
    derived_id: str,
    cases: list[dict[str, object]],
) -> dict[str, Any]:
    broad_ancestor = state.unnamed_concept_candidates[broad_ancestor_id]
    parent = state.unnamed_concept_candidates[parent_id]
    derived = state.unnamed_concept_candidates[derived_id]
    derived_successes: list[int] = []
    parent_successes: list[int] = []
    broad_ancestor_successes: list[int] = []
    baseline_successes: list[int] = []
    derived_false = parent_false = broad_ancestor_false = negatives = 0
    for case in cases:
        context = [str(case["context"])]
        expected = bool(case["expected"])
        derived_output = _candidate_context_matches(derived, context)
        parent_output = _candidate_context_matches(parent, context)
        broad_ancestor_output = _candidate_context_matches(broad_ancestor, context)
        baseline_output = False
        derived_successes.append(int(derived_output == expected))
        parent_successes.append(int(parent_output == expected))
        broad_ancestor_successes.append(int(broad_ancestor_output == expected))
        baseline_successes.append(int(baseline_output == expected))
        if not expected:
            negatives += 1
            derived_false += int(derived_output)
            parent_false += int(parent_output)
            broad_ancestor_false += int(broad_ancestor_output)
    return {
        "derived_successes": derived_successes,
        "parent_successes": parent_successes,
        "broad_ancestor_successes": broad_ancestor_successes,
        "baseline_successes": baseline_successes,
        "parent_delta": _mean(derived_successes) - _mean(parent_successes),
        "baseline_delta": _mean(derived_successes) - _mean(baseline_successes),
        "derived_false_rate": derived_false / negatives,
        "parent_false_rate": parent_false / negatives,
        "broad_ancestor_false_rate": broad_ancestor_false / negatives,
        "false_generalization_delta": (derived_false - parent_false) / negatives,
    }


def _paired_bootstrap_interval(
    left: list[int], right: list[int], samples: int, seed: int
) -> tuple[float, float]:
    rng = random.Random(seed)
    deltas = []
    for _ in range(samples):
        indexes = [rng.randrange(len(left)) for _ in left]
        deltas.append(sum(left[i] - right[i] for i in indexes) / len(indexes))
    deltas.sort()
    return deltas[int(samples * 0.025)], deltas[min(samples - 1, int(samples * 0.975))]


def _mean(values: list[int]) -> float:
    return sum(values) / len(values)


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    final = [row for row in rows if row["partition"] == "final"]
    return {
        key: sum(float(row[key]) for row in final) / len(final)
        for key in (
            "derived_success_rate", "parent_success_rate", "baseline_success_rate",
            "broad_ancestor_success_rate", "derived_vs_parent_delta",
            "derived_false_generalization_rate", "parent_false_generalization_rate",
            "broad_ancestor_false_generalization_rate",
        )
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="experiments/g2_derived_candidate_manifest.json")
    parser.add_argument("--output", default="docs/g2-derived-candidate-results.json")
    args = parser.parse_args()
    result = run_derived_candidate_evaluation(load_manifest(args.manifest))
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["aggregate"], indent=2))


if __name__ == "__main__":
    main()
