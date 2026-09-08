"""Compare a learned temporal candidate with the existing primitive/edge path."""

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
    evaluate_unnamed_candidate,
    rebuild_candidate_inference_index,
)
from risa.engine.composer import compose_to_effect
from risa.engine.runtime import TrainingOptions, train_events


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if manifest["development_episodes_per_seed"] < 1:
        raise ValueError("development_episodes_per_seed must be positive")
    if manifest["final_episodes_per_seed"] < 1:
        raise ValueError("final_episodes_per_seed must be positive")
    if manifest["bootstrap_samples"] < 1:
        raise ValueError("bootstrap_samples must be positive")
    return manifest


def run_temporal_candidate_evaluation(manifest: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    lifecycle: list[dict[str, Any]] = []
    actor_target_binding = bool(manifest.get("actor_target_role_binding", False))
    for seed_value in manifest["seeds"]:
        seed = int(seed_value)
        state = _training_state(seed, actor_target_binding)
        candidate = next(
            item
            for item in state.unnamed_concept_candidates.values()
            if item.structural_schema.get("kind") == "temporal_sequence"
        )
        development = _cases(
            seed,
            "development",
            manifest["development_episodes_per_seed"],
            actor_target_binding,
        )
        final = _cases(
            seed,
            "final",
            manifest["final_episodes_per_seed"],
            actor_target_binding,
        )
        development_metrics = _compare(state, candidate.id, development)
        development_interval = _paired_bootstrap_interval(
            development_metrics["candidate_successes"],
            development_metrics["baseline_successes"],
            manifest["bootstrap_samples"],
            seed,
        )
        evaluate_unnamed_candidate(
            state,
            candidate.id,
            partition="development",
            evaluation_event_ids=[case["id"] for case in development],
            prediction_delta=0.0,
            composition_delta=development_metrics["delta"],
            prediction_delta_ci_lower=0.0,
            composition_delta_ci_lower=development_interval[0],
            false_generalization_delta=development_metrics["false_generalization_delta"],
            minimum_gain=float(manifest["minimum_gain"]),
        )
        lifecycle.append(
            {
                "seed": seed,
                "candidate_id": candidate.id,
                "after_development": candidate.lifecycle_status,
                "after_final": candidate.lifecycle_status,
                "support_ids": list(candidate.supporting_event_ids),
                "development_ids": [case["id"] for case in development],
                "final_ids": [case["id"] for case in final],
            }
        )
        for partition, cases in (("development", development), ("final", final)):
            metrics = _compare(state, candidate.id, cases)
            interval = _paired_bootstrap_interval(
                metrics["candidate_successes"],
                metrics["baseline_successes"],
                manifest["bootstrap_samples"],
                seed + (1 if partition == "final" else 0),
            )
            rows.append(
                {
                    "seed": seed,
                    "partition": partition,
                    "episodes": len(cases),
                    "candidate_success_rate": _mean(metrics["candidate_successes"]),
                    "existing_path_success_rate": _mean(metrics["baseline_successes"]),
                    "paired_delta": metrics["delta"],
                    "paired_delta_95ci": list(interval),
                    "candidate_false_generalization_rate": metrics["candidate_false_rate"],
                    "existing_path_false_generalization_rate": metrics["baseline_false_rate"],
                    "false_generalization_delta": metrics["false_generalization_delta"],
                }
            )

        if candidate.lifecycle_status == "provisional":
            final_metrics = _compare(state, candidate.id, final)
            final_interval = _paired_bootstrap_interval(
                final_metrics["candidate_successes"],
                final_metrics["baseline_successes"],
                manifest["bootstrap_samples"],
                seed + 1,
            )
            evaluate_unnamed_candidate(
                state,
                candidate.id,
                partition="final",
                evaluation_event_ids=[case["id"] for case in final],
                prediction_delta=0.0,
                composition_delta=final_metrics["delta"],
                prediction_delta_ci_lower=0.0,
                composition_delta_ci_lower=final_interval[0],
                false_generalization_delta=final_metrics[
                    "false_generalization_delta"
                ],
                minimum_gain=float(manifest["minimum_gain"]),
            )
        lifecycle[-1]["after_final"] = candidate.lifecycle_status

    digest = hashlib.sha256(
        json.dumps(manifest, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "benchmark_version": manifest["benchmark_version"],
        "manifest_sha256": digest,
        "manifest": manifest,
        "leakage_audit": _audit(lifecycle),
        "rows": rows,
        "aggregate": _aggregate(rows),
        "lifecycle": lifecycle,
        "decision": _decision(lifecycle),
    }


def _training_state(seed: int, actor_target_binding: bool = False) -> RisaState:
    state = RisaState()
    events: list[Event] = []
    timestamp = 1
    for target, source in (("battery-a", "sensor-a"), ("battery-b", "sensor-b")):
        episode = f"support:{seed}:{target}"
        events.extend(
            [
                Event(
                    id=f"{episode}:charge",
                    timestamp=timestamp,
                    actor=f"trainer-{target}",
                    action="charge",
                    target=target,
                    actor_roles=["controller"] if actor_target_binding else [],
                    target_roles=["powered_device"],
                    preconditions=["connected"],
                    numeric_preconditions={"energy": 2.0},
                    state_variable_deltas={"energy": -1.0},
                    observed_effects=["charged"],
                    episode_id=episode,
                    source=source,
                ),
                Event(
                    id=f"{episode}:activate",
                    timestamp=timestamp + 1,
                    actor=f"trainer-{target}",
                    action="activate",
                    target=target,
                    actor_roles=["controller"] if actor_target_binding else [],
                    target_roles=["powered_device"],
                    preconditions=["charged"],
                    consumed_states=["charged"],
                    numeric_preconditions={"energy": 1.0},
                    state_variable_deltas={"energy": -1.0},
                    observed_states_before=["charged"],
                    before_state_observed=True,
                    observed_effects=["online"],
                    episode_id=episode,
                    source=source,
                ),
            ]
        )
        timestamp += 2
    train_events(
        state,
        events,
        options=TrainingOptions(
            enable_metabolism=False,
            enable_replay=False,
            enable_adaptation=False,
            enable_coactivation=False,
        ),
    )
    return state


def _cases(
    seed: int,
    partition: str,
    count: int,
    actor_target_binding: bool = False,
) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    if actor_target_binding:
        variants = (
            (["controller"], ["powered_device"], ["connected"], {"energy": 2.0}, "controller-new", "device-new", True),
            (["observer"], ["powered_device"], ["connected"], {"energy": 2.0}, "observer-new", "device-new", False),
            (["controller"], ["heating_device"], ["connected"], {"energy": 2.0}, "controller-new", "heater-new", False),
            (["controller"], ["powered_device"], ["connected"], {"energy": 2.0}, "self-device", "self-device", False),
            (["controller"], ["powered_device"], [], {"energy": 2.0}, "controller-new", "device-new", False),
        )
    else:
        variants = (
            ([], ["powered_device"], ["connected"], {"energy": 2.0}, "operator", "device", True),
            ([], ["powered_device"], [], {"energy": 2.0}, "operator", "device", False),
            ([], ["powered_device"], ["connected"], {"energy": 1.0}, "operator", "device", False),
            ([], ["heating_device"], ["connected"], {"energy": 2.0}, "operator", "device", False),
        )
    for index in range(int(count)):
        actor_roles, target_roles, states, variables, actor, target, expected = variants[
            index % len(variants)
        ]
        cases.append(
            {
                "id": f"{partition}:{seed}:{index}",
                "actor_roles": actor_roles,
                "target_roles": target_roles,
                "states": states,
                "variables": variables,
                "actor": actor,
                "target": target,
                "expected": expected,
            }
        )
    return cases


def _compare(
    state: RisaState, candidate_id: str, cases: list[dict[str, object]]
) -> dict[str, Any]:
    counterfactual = RisaState.from_dict(state.to_dict())
    counterfactual.unnamed_concept_candidates[candidate_id].lifecycle_status = "adopted"
    rebuild_candidate_inference_index(counterfactual)
    candidate_successes: list[int] = []
    baseline_successes: list[int] = []
    candidate_false = 0
    baseline_false = 0
    negatives = 0
    for case in cases:
        expected = bool(case["expected"])
        candidate_output = _compose(counterfactual, case, True)
        baseline_output = _compose(counterfactual, case, False)
        candidate_successes.append(int(candidate_output == expected))
        baseline_successes.append(int(baseline_output == expected))
        if not expected:
            negatives += 1
            candidate_false += int(candidate_output)
            baseline_false += int(baseline_output)
    candidate_false_rate = candidate_false / max(negatives, 1)
    baseline_false_rate = baseline_false / max(negatives, 1)
    return {
        "candidate_successes": candidate_successes,
        "baseline_successes": baseline_successes,
        "delta": round(_mean(candidate_successes) - _mean(baseline_successes), 6),
        "candidate_false_rate": round(candidate_false_rate, 6),
        "baseline_false_rate": round(baseline_false_rate, 6),
        "false_generalization_delta": round(
            candidate_false_rate - baseline_false_rate, 6
        ),
    }


def _compose(state: RisaState, case: dict[str, object], enabled: bool) -> bool:
    result = compose_to_effect(
        state,
        "charge",
        "online",
        actor_roles=list(case["actor_roles"]),
        target_roles=list(case["target_roles"]),
        actor=str(case["actor"]),
        target=str(case["target"]),
        start_states=list(case["states"]),
        start_variables=dict(case["variables"]),
        max_steps=2,
        enable_candidate_concepts=enabled,
    )
    return bool(result.primitive_ids)


def _paired_bootstrap_interval(
    candidate: list[int], baseline: list[int], samples: int, seed: int
) -> tuple[float, float]:
    rng = random.Random(seed)
    differences = []
    for _ in range(samples):
        indexes = [rng.randrange(len(candidate)) for _ in candidate]
        differences.append(
            sum(candidate[index] - baseline[index] for index in indexes) / len(indexes)
        )
    differences.sort()
    return (
        round(differences[int(0.025 * (samples - 1))], 6),
        round(differences[int(0.975 * (samples - 1))], 6),
    )


def _mean(values: list[int]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def _audit(lifecycle: list[dict[str, Any]]) -> dict[str, int]:
    support = {item for row in lifecycle for item in row["support_ids"]}
    development = {item for row in lifecycle for item in row["development_ids"]}
    final = {item for row in lifecycle for item in row["final_ids"]}
    return {
        "support_development_overlap": len(support.intersection(development)),
        "support_final_overlap": len(support.intersection(final)),
        "development_final_overlap": len(development.intersection(final)),
    }


def _aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for partition in ("development", "final"):
        selected = [row for row in rows if row["partition"] == partition]
        episodes = sum(row["episodes"] for row in selected)
        result.append(
            {
                "partition": partition,
                "seeds": len(selected),
                "episodes": episodes,
                "candidate_success_rate": round(
                    sum(row["candidate_success_rate"] * row["episodes"] for row in selected)
                    / episodes,
                    6,
                ),
                "existing_path_success_rate": round(
                    sum(row["existing_path_success_rate"] * row["episodes"] for row in selected)
                    / episodes,
                    6,
                ),
                "paired_delta": round(
                    sum(row["paired_delta"] for row in selected) / len(selected), 6
                ),
                "candidate_false_generalization_rate": round(
                    sum(row["candidate_false_generalization_rate"] for row in selected)
                    / len(selected),
                    6,
                ),
                "existing_path_false_generalization_rate": round(
                    sum(row["existing_path_false_generalization_rate"] for row in selected)
                    / len(selected),
                    6,
                ),
            }
        )
    return result


def _decision(lifecycle: list[dict[str, Any]]) -> str:
    if all(item["after_final"] == "adopted" for item in lifecycle):
        return "adopted_role_scoped_temporal_candidate"
    if all(item["after_development"] == "rejected" for item in lifecycle):
        return "rejected_redundant_temporal_candidate"
    return "candidate_gate_requires_review"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", default="experiments/g2_temporal_candidate_manifest.json"
    )
    parser.add_argument("--output", default="docs/g2-temporal-candidate-results.json")
    arguments = parser.parse_args()
    results = run_temporal_candidate_evaluation(load_manifest(arguments.manifest))
    Path(arguments.output).write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(results["aggregate"], indent=2))
    print(results["decision"])


if __name__ == "__main__":
    main()
