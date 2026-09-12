"""Compare structure-induced target roles with supplied roles and no roles."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
from typing import Any

from risa.core.models import Event, PredictionQuery, UnnamedConceptCandidate
from risa.core.state import RisaState
from risa.engine.candidate_discovery import (
    evaluate_unnamed_candidate,
    rebuild_candidate_inference_index,
)
from risa.engine.composer import forecast_next_effects
from risa.engine.predictor import predict_next_effect
from risa.engine.runtime import TrainingOptions, train_events


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in (
        "development_episodes_per_seed",
        "final_episodes_per_seed",
        "bootstrap_samples",
    ):
        if int(manifest[key]) < 1:
            raise ValueError(f"{key} must be positive")
    return manifest


def run_structural_role_evaluation(manifest: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    lifecycle: list[dict[str, Any]] = []
    for raw_seed in manifest["seeds"]:
        seed = int(raw_seed)
        induced_state = _training_state(seed, supplied_roles=False)
        supplied_state = _training_state(seed, supplied_roles=True)
        induced_candidates = _transition_candidates(induced_state)
        supplied_candidates = _transition_candidates(supplied_state)
        development = _cases(
            seed, "development", int(manifest["development_episodes_per_seed"])
        )
        final = _cases(seed, "final", int(manifest["final_episodes_per_seed"]))
        lifecycle_row: dict[str, Any] = {
            "seed": seed,
            "support_ids": sorted(induced_state.events_by_id),
            "development_ids": [str(case["id"]) for case in development],
            "final_ids": [str(case["id"]) for case in final],
            "induced_role_ids": sorted(
                candidate.typed_role_variables["target"]
                for candidate in induced_candidates
            ),
        }
        for partition_index, (partition, cases) in enumerate(
            (("development", development), ("final", final))
        ):
            metrics = _compare(
                induced_state,
                supplied_state,
                induced_candidates,
                supplied_candidates,
                cases,
            )
            induced_prediction_interval = _paired_bootstrap_interval(
                metrics["induced_prediction_successes"],
                metrics["no_role_prediction_successes"],
                int(manifest["bootstrap_samples"]),
                seed + partition_index,
            )
            supplied_prediction_interval = _paired_bootstrap_interval(
                metrics["supplied_prediction_successes"],
                metrics["no_role_prediction_successes"],
                int(manifest["bootstrap_samples"]),
                seed + 10 + partition_index,
            )
            induced_composition_interval = _paired_bootstrap_interval(
                metrics["induced_composition_successes"],
                metrics["no_role_composition_successes"],
                int(manifest["bootstrap_samples"]),
                seed + 100 + partition_index,
            )
            supplied_composition_interval = _paired_bootstrap_interval(
                metrics["supplied_composition_successes"],
                metrics["no_role_composition_successes"],
                int(manifest["bootstrap_samples"]),
                seed + 110 + partition_index,
            )
            for candidate in induced_candidates:
                evaluate_unnamed_candidate(
                    induced_state,
                    candidate.id,
                    partition=partition,
                    evaluation_event_ids=[str(case["id"]) for case in cases],
                    prediction_delta=metrics["prediction_delta"],
                    composition_delta=metrics["composition_delta"],
                    prediction_delta_ci_lower=induced_prediction_interval[0],
                    composition_delta_ci_lower=induced_composition_interval[0],
                    false_generalization_delta=metrics[
                        "false_generalization_delta"
                    ],
                    minimum_gain=float(manifest["minimum_gain"]),
                )
            for candidate in supplied_candidates:
                evaluate_unnamed_candidate(
                    supplied_state,
                    candidate.id,
                    partition=partition,
                    evaluation_event_ids=[
                        f"supplied:{case['id']}" for case in cases
                    ],
                    prediction_delta=metrics["supplied_prediction_delta"],
                    composition_delta=metrics["supplied_composition_delta"],
                    prediction_delta_ci_lower=supplied_prediction_interval[0],
                    composition_delta_ci_lower=supplied_composition_interval[0],
                    false_generalization_delta=metrics[
                        "false_generalization_delta"
                    ],
                    minimum_gain=float(manifest["minimum_gain"]),
                )
            rows.append(
                {
                    "seed": seed,
                    "partition": partition,
                    "episodes": len(cases),
                    "induced_prediction_success_rate": _mean(
                        metrics["induced_prediction_successes"]
                    ),
                    "supplied_prediction_success_rate": _mean(
                        metrics["supplied_prediction_successes"]
                    ),
                    "no_role_prediction_success_rate": _mean(
                        metrics["no_role_prediction_successes"]
                    ),
                    "induced_composition_success_rate": _mean(
                        metrics["induced_composition_successes"]
                    ),
                    "supplied_composition_success_rate": _mean(
                        metrics["supplied_composition_successes"]
                    ),
                    "no_role_composition_success_rate": _mean(
                        metrics["no_role_composition_successes"]
                    ),
                    "prediction_delta_vs_no_role": metrics["prediction_delta"],
                    "prediction_delta_95ci": list(induced_prediction_interval),
                    "supplied_prediction_delta_vs_no_role": metrics[
                        "supplied_prediction_delta"
                    ],
                    "supplied_prediction_delta_95ci": list(
                        supplied_prediction_interval
                    ),
                    "composition_delta_vs_no_role": metrics["composition_delta"],
                    "composition_delta_95ci": list(induced_composition_interval),
                    "supplied_composition_delta_vs_no_role": metrics[
                        "supplied_composition_delta"
                    ],
                    "supplied_composition_delta_95ci": list(
                        supplied_composition_interval
                    ),
                    "induced_mistyping_rate": metrics["induced_mistyping_rate"],
                    "supplied_mistyping_rate": metrics["supplied_mistyping_rate"],
                }
            )
        lifecycle_row["induced_after_final"] = sorted(
            candidate.lifecycle_status for candidate in induced_candidates
        )
        lifecycle_row["supplied_after_final"] = sorted(
            candidate.lifecycle_status for candidate in supplied_candidates
        )
        lifecycle_row["induced_state_bytes"] = _state_bytes(induced_state)
        lifecycle_row["supplied_state_bytes"] = _state_bytes(supplied_state)
        lifecycle.append(lifecycle_row)
    digest = hashlib.sha256(
        json.dumps(manifest, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "benchmark_version": manifest["benchmark_version"],
        "manifest_sha256": digest,
        "manifest": manifest,
        "leakage_audit": _audit(lifecycle),
        "rows": rows,
        "aggregate": _aggregate(rows, lifecycle),
        "lifecycle": lifecycle,
        "decision": (
            "adopt_structural_role_induction"
            if all(
                set(row["induced_after_final"]) == {"adopted"}
                for row in lifecycle
            )
            else "reject"
        ),
    }


def _training_state(seed: int, *, supplied_roles: bool) -> RisaState:
    state = RisaState()
    events = []
    timestamp = 1
    for effect, relation, role in (
        ("warm", "powered_by", "powered_device"),
        ("cold", "cooled_by", "cooled_device"),
    ):
        for index in range(8):
            target = f"{effect}-device-{seed}-{index}"
            events.append(
                Event(
                    id=f"support:{seed}:{effect}:{index}",
                    timestamp=timestamp,
                    actor=f"trainer-{index}",
                    action="inspect",
                    target=target,
                    target_roles=[role] if supplied_roles else [],
                    observed_effects=[effect],
                    episode_id=f"support:{seed}:{effect}:{index}",
                    source=f"sensor-{effect}-{index}",
                    entity_bindings={
                        "object": target,
                        "provider": f"provider-{effect}-{seed}-{index}",
                    },
                    entity_relations=[
                        {
                            "source": "object",
                            "relation": relation,
                            "target": "provider",
                        }
                    ],
                    entity_relations_observed=True,
                )
            )
            timestamp += 1
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


def _transition_candidates(state: RisaState) -> list[UnnamedConceptCandidate]:
    return sorted(
        (
            candidate
            for candidate in state.unnamed_concept_candidates.values()
            if candidate.derivation_generation == 0
            and candidate.structural_schema.get("kind", "single_transition")
            == "single_transition"
        ),
        key=lambda candidate: candidate.id,
    )


def _cases(seed: int, partition: str, count: int) -> list[dict[str, object]]:
    variants = (
        ("powered_by", "powered_device", "warm", "out"),
        ("cooled_by", "cooled_device", "cold", "out"),
        ("stored_in", "storage_device", None, "out"),
        ("powered_by", "reverse_device", None, "in"),
    )
    cases = []
    for index in range(count):
        relation, role, expected, direction = variants[index % len(variants)]
        target = f"heldout-device-{seed}-{partition}-{index}"
        provider = f"heldout-provider-{seed}-{partition}-{index}"
        bindings = {"item": target, "counterpart": provider}
        source, destination = (
            ("item", "counterpart")
            if direction == "out"
            else ("counterpart", "item")
        )
        cases.append(
            {
                "id": f"{partition}:{seed}:{index}",
                "target": target,
                "role": role,
                "expected": expected,
                "entity_bindings": bindings,
                "entity_relations": [
                    {
                        "source": source,
                        "relation": relation,
                        "target": destination,
                    }
                ],
            }
        )
    random.Random(f"{seed}:{partition}").shuffle(cases)
    return cases


def _compare(
    induced_state: RisaState,
    supplied_state: RisaState,
    induced_candidates: list[UnnamedConceptCandidate],
    supplied_candidates: list[UnnamedConceptCandidate],
    cases: list[dict[str, object]],
) -> dict[str, Any]:
    induced = _candidate_state(induced_state, induced_candidates)
    supplied = _candidate_state(supplied_state, supplied_candidates)
    no_role = _candidate_state(induced_state, induced_candidates)
    results: dict[str, list[int]] = {
        "induced_prediction_successes": [],
        "supplied_prediction_successes": [],
        "no_role_prediction_successes": [],
        "induced_composition_successes": [],
        "supplied_composition_successes": [],
        "no_role_composition_successes": [],
    }
    induced_false = supplied_false = no_role_false = negatives = 0
    for case in cases:
        expected = case["expected"]
        induced_prediction = _predict(induced, case, "induced")
        supplied_prediction = _predict(supplied, case, "supplied")
        no_role_prediction = _predict(no_role, case, "none")
        induced_composition = _forecast(induced, case, "induced")
        supplied_composition = _forecast(supplied, case, "supplied")
        no_role_composition = _forecast(no_role, case, "none")
        for key, output in (
            ("induced_prediction_successes", induced_prediction),
            ("supplied_prediction_successes", supplied_prediction),
            ("no_role_prediction_successes", no_role_prediction),
            ("induced_composition_successes", induced_composition),
            ("supplied_composition_successes", supplied_composition),
            ("no_role_composition_successes", no_role_composition),
        ):
            results[key].append(int(output == expected))
        if expected is None:
            negatives += 1
            induced_false += int(induced_prediction is not None)
            supplied_false += int(supplied_prediction is not None)
            no_role_false += int(no_role_prediction is not None)
    results.update(
        {
            "prediction_delta": _mean(results["induced_prediction_successes"])
            - _mean(results["no_role_prediction_successes"]),
            "composition_delta": _mean(results["induced_composition_successes"])
            - _mean(results["no_role_composition_successes"]),
            "supplied_prediction_delta": _mean(
                results["supplied_prediction_successes"]
            )
            - _mean(results["no_role_prediction_successes"]),
            "supplied_composition_delta": _mean(
                results["supplied_composition_successes"]
            )
            - _mean(results["no_role_composition_successes"]),
            "induced_mistyping_rate": induced_false / negatives,
            "supplied_mistyping_rate": supplied_false / negatives,
            "false_generalization_delta": (induced_false - no_role_false) / negatives,
        }
    )
    return results


def _candidate_state(
    source: RisaState, candidates: list[UnnamedConceptCandidate]
) -> RisaState:
    state = RisaState.from_dict(source.to_dict())
    for candidate in candidates:
        state.unnamed_concept_candidates[candidate.id].lifecycle_status = "adopted"
    state.action_target_role_context_effect_counts.clear()
    state.structural_primitives.clear()
    rebuild_candidate_inference_index(state)
    return state


def _predict(state: RisaState, case: dict[str, object], method: str) -> str | None:
    result = predict_next_effect(
        state,
        PredictionQuery(
            actor="heldout-robot",
            action="inspect",
            target=str(case["target"]),
            target_roles=[str(case["role"])] if method == "supplied" else [],
            entity_bindings=dict(case["entity_bindings"]),
            entity_relations=list(case["entity_relations"]),
            enable_role_induction=method == "induced",
        ),
    )
    return result.predicted_effects[0] if result.predicted_effects else None


def _forecast(state: RisaState, case: dict[str, object], method: str) -> str | None:
    results = forecast_next_effects(
        state,
        "inspect",
        target_roles=[str(case["role"])] if method == "supplied" else [],
        target=str(case["target"]),
        entity_bindings=dict(case["entity_bindings"]),
        entity_relations=list(case["entity_relations"]),
        enable_role_induction=method == "induced",
    )
    return results[0].added_states[0] if results else None


def _paired_bootstrap_interval(
    left: list[int], right: list[int], samples: int, seed: int
) -> tuple[float, float]:
    rng = random.Random(seed)
    deltas = []
    for _ in range(samples):
        indexes = [rng.randrange(len(left)) for _ in left]
        deltas.append(sum(left[i] - right[i] for i in indexes) / len(indexes))
    deltas.sort()
    return (
        deltas[int(samples * 0.025)],
        deltas[min(samples - 1, int(samples * 0.975))],
    )


def _mean(values: list[int]) -> float:
    return sum(values) / len(values)


def _state_bytes(state: RisaState) -> int:
    return len(json.dumps(state.to_dict(), sort_keys=True, separators=(",", ":")))


def _audit(lifecycle: list[dict[str, Any]]) -> dict[str, int]:
    totals = {
        "support_development_overlap": 0,
        "support_final_overlap": 0,
        "development_final_overlap": 0,
    }
    for row in lifecycle:
        support = set(row["support_ids"])
        development = set(row["development_ids"])
        final = set(row["final_ids"])
        totals["support_development_overlap"] += len(support & development)
        totals["support_final_overlap"] += len(support & final)
        totals["development_final_overlap"] += len(development & final)
    return totals


def _aggregate(
    rows: list[dict[str, Any]], lifecycle: list[dict[str, Any]]
) -> dict[str, float]:
    final = [row for row in rows if row["partition"] == "final"]
    aggregate = {
        key: sum(float(row[key]) for row in final) / len(final)
        for key in (
            "induced_prediction_success_rate",
            "supplied_prediction_success_rate",
            "no_role_prediction_success_rate",
            "induced_composition_success_rate",
            "supplied_composition_success_rate",
            "no_role_composition_success_rate",
            "prediction_delta_vs_no_role",
            "supplied_prediction_delta_vs_no_role",
            "composition_delta_vs_no_role",
            "supplied_composition_delta_vs_no_role",
            "induced_mistyping_rate",
            "supplied_mistyping_rate",
        )
    }
    aggregate["mean_induced_state_bytes"] = sum(
        row["induced_state_bytes"] for row in lifecycle
    ) / len(lifecycle)
    aggregate["mean_supplied_state_bytes"] = sum(
        row["supplied_state_bytes"] for row in lifecycle
    ) / len(lifecycle)
    return aggregate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", default="experiments/g2_structural_role_manifest.json"
    )
    parser.add_argument("--output", default="docs/g2-structural-role-results.json")
    args = parser.parse_args()
    result = run_structural_role_evaluation(load_manifest(args.manifest))
    Path(args.output).write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["aggregate"], indent=2))


if __name__ == "__main__":
    main()
