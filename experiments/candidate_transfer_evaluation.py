"""Evaluate whether an unnamed candidate adds value beyond typed role evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import time
from typing import Any

from risa.core.models import Event, PredictionQuery
from risa.core.state import RisaState
from risa.engine.candidate_discovery import (
    evaluate_unnamed_candidate,
    rebuild_candidate_inference_index,
)
from risa.engine.predictor import predict_next_effect
from risa.engine.readout_compaction import compact_adopted_candidate_readouts
from risa.engine.runtime import TrainingOptions, train_events


def load_manifest(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data["development_episodes_per_seed"] < 1 or data["final_episodes_per_seed"] < 1:
        raise ValueError("development and final episode counts must be positive")
    if data["bootstrap_samples"] < 1:
        raise ValueError("bootstrap_samples must be positive")
    return data


def run_candidate_transfer(manifest: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    lifecycle_rows: list[dict[str, Any]] = []
    for seed in manifest["seeds"]:
        state = _training_state(int(seed))
        candidate = next(iter(state.unnamed_concept_candidates.values()))
        development = _cases(
            int(seed), "development", int(manifest["development_episodes_per_seed"])
        )
        final = _cases(
            int(seed), "final", int(manifest["final_episodes_per_seed"])
        )

        development_metrics = _compare_candidate(state, candidate.id, development)
        evaluate_unnamed_candidate(
            state,
            candidate.id,
            partition="development",
            evaluation_event_ids=[case[0] for case in development],
            prediction_delta=development_metrics["delta"],
            composition_delta=0.0,
            prediction_delta_ci_lower=_paired_bootstrap_interval(
                development_metrics["candidate_successes"],
                development_metrics["no_candidate_successes"],
                int(manifest["bootstrap_samples"]),
                int(seed),
            )[0],
            composition_delta_ci_lower=0.0,
            false_generalization_delta=development_metrics[
                "false_generalization_delta"
            ],
            minimum_gain=float(manifest["minimum_gain"]),
        )
        lifecycle_rows.append(
            {
                "seed": seed,
                "candidate_id": candidate.id,
                "after_development": candidate.lifecycle_status,
                "support_ids": list(candidate.supporting_event_ids),
                "development_ids": [case[0] for case in development],
                "final_ids": [case[0] for case in final],
            }
        )
        for partition, cases in (("development", development), ("final", final)):
            metrics = _compare_candidate(state, candidate.id, cases)
            lower, upper = _paired_bootstrap_interval(
                metrics["candidate_successes"],
                metrics["no_candidate_successes"],
                int(manifest["bootstrap_samples"]),
                int(seed) + (1 if partition == "final" else 0),
            )
            rows.append(
                {
                    "seed": seed,
                    "partition": partition,
                    "episodes": len(cases),
                    "candidate_success_rate": _mean(metrics["candidate_successes"]),
                    "no_candidate_success_rate": _mean(
                        metrics["no_candidate_successes"]
                    ),
                    "paired_delta": metrics["delta"],
                    "paired_delta_95ci": [lower, upper],
                    "false_generalization_delta": metrics[
                        "false_generalization_delta"
                    ],
                    "compressed_readout_candidate_success_rate": metrics[
                        "compressed_candidate_rate"
                    ],
                    "compressed_readout_no_candidate_success_rate": metrics[
                        "compressed_no_candidate_rate"
                    ],
                    "compaction_applied": metrics["compaction_applied"],
                    "role_readout_bytes_before": metrics["role_readout_bytes_before"],
                    "role_readout_bytes_after": metrics["role_readout_bytes_after"],
                    "total_state_bytes_before": metrics["total_state_bytes_before"],
                    "total_state_bytes_after": metrics["total_state_bytes_after"],
                    "full_candidate_state_bytes": metrics[
                        "full_candidate_state_bytes"
                    ],
                    "reconstructed_candidate_state_bytes": metrics[
                        "reconstructed_candidate_state_bytes"
                    ],
                    "verbose_event_state_bytes": metrics[
                        "verbose_event_state_bytes"
                    ],
                    "compact_event_state_bytes": metrics[
                        "compact_event_state_bytes"
                    ],
                    "uncompressed_reconstructable_state_bytes": metrics[
                        "uncompressed_reconstructable_state_bytes"
                    ],
                    "verbose_derived_state_bytes": metrics[
                        "verbose_derived_state_bytes"
                    ],
                    "compact_derived_state_bytes": metrics[
                        "compact_derived_state_bytes"
                    ],
                    "prediction_p95_ms_before": metrics["prediction_p95_ms_before"],
                    "prediction_p95_ms_after": metrics["prediction_p95_ms_after"],
                    "regression_queries_checked": metrics[
                        "regression_queries_checked"
                    ],
                }
            )

    manifest_digest = hashlib.sha256(
        json.dumps(manifest, sort_keys=True).encode("utf-8")
    ).hexdigest()
    aggregate = _aggregate(rows)
    final_efficiency = next(
        row for row in aggregate if row["partition"] == "final"
    )
    return {
        "benchmark_version": manifest["benchmark_version"],
        "manifest_sha256": manifest_digest,
        "manifest": manifest,
        "leakage_audit": _audit(lifecycle_rows),
        "rows": rows,
        "aggregate": aggregate,
        "lifecycle": lifecycle_rows,
        "decision": (
            "rejected_redundant_single_transition_candidate"
            if all(row["after_development"] == "rejected" for row in lifecycle_rows)
            else "candidate_gate_requires_review"
        ),
        "compaction_decision": (
            "rejected_persisted_total_state_growth"
            if final_efficiency["mean_total_state_bytes_after"]
            >= final_efficiency["mean_total_state_bytes_before"]
            else "retained_for_further_efficiency_validation"
        ),
    }


def _training_state(seed: int) -> RisaState:
    state = RisaState()
    events: list[Event] = []
    timestamp = 1
    for target, source in (("heater", "sensor-a"), ("radiator", "sensor-b")):
        for repeat in range(3):
            events.append(
                Event(
                    id=f"support:{seed}:{target}:{repeat}",
                    timestamp=timestamp,
                    actor=f"trainer-{repeat}",
                    action="inspect",
                    target=target,
                    target_roles=["heating_device"],
                    observed_effects=["warm"],
                    episode_id=f"support:{seed}:{target}:{repeat}",
                    source=source,
                )
            )
            timestamp += 1
    for repeat in range(2):
        events.append(
            Event(
                id=f"counterexample:{seed}:{repeat}",
                timestamp=timestamp,
                actor=f"trainer-x-{repeat}",
                action="inspect",
                target="faulty-boiler",
                target_roles=["heating_device"],
                observed_effects=["cold"],
                episode_id=f"counterexample:{seed}:{repeat}",
                source="sensor-c",
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


def _cases(seed: int, partition: str, count: int) -> list[tuple[str, str, tuple[str, ...]]]:
    cases = []
    for index in range(count):
        if index % 4 == 3:
            cases.append(
                (f"{partition}:{seed}:{index}", f"unknown-cooler-{index}", ("cooling_device",))
            )
        else:
            cases.append(
                (f"{partition}:{seed}:{index}", f"unseen-heater-{index}", ("heating_device",))
            )
    return cases


def _compare_candidate(
    state: RisaState,
    candidate_id: str,
    cases: list[tuple[str, str, tuple[str, ...]]],
) -> dict[str, Any]:
    counterfactual = RisaState.from_dict(state.to_dict())
    counterfactual.unnamed_concept_candidates[candidate_id].lifecycle_status = "adopted"
    rebuild_candidate_inference_index(counterfactual)
    candidate_successes: list[int] = []
    no_candidate_successes: list[int] = []
    candidate_false = 0
    no_candidate_false = 0
    for _, target, roles in cases:
        expected = ("warm",) if "heating_device" in roles else ()
        with_candidate = _predict(counterfactual, target, roles, True)
        without_candidate = _predict(counterfactual, target, roles, False)
        candidate_successes.append(int(with_candidate == expected))
        no_candidate_successes.append(int(without_candidate == expected))
        if not expected:
            candidate_false += int(bool(with_candidate))
            no_candidate_false += int(bool(without_candidate))

    compressed = RisaState.from_dict(counterfactual.to_dict())
    compaction_queries = [
        PredictionQuery(
            actor="heldout-actor",
            action="inspect",
            target=target,
            target_roles=list(roles),
        )
        for _, target, roles in cases
    ]
    full_candidate_state_bytes = _full_candidate_state_bytes(compressed)
    total_bytes_before = _serialized_state_bytes(compressed)
    verbose_event_state_bytes = _verbose_event_state_bytes(compressed)
    uncompressed_state_bytes = _uncompressed_reconstructable_state_bytes(compressed)
    verbose_derived_state_bytes = _verbose_derived_state_bytes(compressed)
    p95_ms_before = _prediction_p95_ms(compressed, compaction_queries)
    compaction = compact_adopted_candidate_readouts(compressed, compaction_queries)
    total_bytes_after = _serialized_state_bytes(compressed)
    p95_ms_after = _prediction_p95_ms(compressed, compaction_queries)
    compressed_candidate = []
    compressed_no_candidate = []
    for _, target, roles in cases:
        expected = ("warm",) if "heating_device" in roles else ()
        compressed_candidate.append(
            int(_predict(compressed, target, roles, True) == expected)
        )
        compressed_no_candidate.append(
            int(_predict(compressed, target, roles, False) == expected)
        )
    negative_count = sum(1 for _, _, roles in cases if "heating_device" not in roles)
    return {
        "candidate_successes": candidate_successes,
        "no_candidate_successes": no_candidate_successes,
        "delta": round(_mean(candidate_successes) - _mean(no_candidate_successes), 6),
        "false_generalization_delta": round(
            (candidate_false - no_candidate_false) / max(negative_count, 1), 6
        ),
        "compressed_candidate_rate": _mean(compressed_candidate),
        "compressed_no_candidate_rate": _mean(compressed_no_candidate),
        "compaction_applied": compaction.applied,
        "role_readout_bytes_before": compaction.readout_bytes_before,
        "role_readout_bytes_after": compaction.readout_bytes_after,
        "total_state_bytes_before": total_bytes_before,
        "total_state_bytes_after": total_bytes_after,
        "full_candidate_state_bytes": full_candidate_state_bytes,
        "reconstructed_candidate_state_bytes": total_bytes_before,
        "verbose_event_state_bytes": verbose_event_state_bytes,
        "compact_event_state_bytes": total_bytes_before,
        "uncompressed_reconstructable_state_bytes": uncompressed_state_bytes,
        "verbose_derived_state_bytes": verbose_derived_state_bytes,
        "compact_derived_state_bytes": total_bytes_before,
        "prediction_p95_ms_before": p95_ms_before,
        "prediction_p95_ms_after": p95_ms_after,
        "regression_queries_checked": compaction.checked_queries,
    }


def _predict(
    state: RisaState,
    target: str,
    roles: tuple[str, ...],
    enable_candidate: bool,
) -> tuple[str, ...]:
    result = predict_next_effect(
        state,
        PredictionQuery(
            actor="heldout-actor",
            action="inspect",
            target=target,
            target_roles=list(roles),
            enable_candidate_concepts=enable_candidate,
        ),
    )
    return tuple(sorted(result.predicted_effects))


def _paired_bootstrap_interval(
    candidate: list[int],
    baseline: list[int],
    samples: int,
    seed: int,
) -> tuple[float, float]:
    if not candidate or len(candidate) != len(baseline):
        return 0.0, 0.0
    rng = random.Random(seed)
    differences = []
    for _ in range(samples):
        indices = [rng.randrange(len(candidate)) for _ in candidate]
        differences.append(
            sum(candidate[index] - baseline[index] for index in indices) / len(indices)
        )
    differences.sort()
    lower = differences[int(0.025 * (samples - 1))]
    upper = differences[int(0.975 * (samples - 1))]
    return round(lower, 6), round(upper, 6)


def _audit(lifecycle_rows: list[dict[str, Any]]) -> dict[str, int]:
    support = {item for row in lifecycle_rows for item in row["support_ids"]}
    development = {item for row in lifecycle_rows for item in row["development_ids"]}
    final = {item for row in lifecycle_rows for item in row["final_ids"]}
    return {
        "support_development_overlap": len(support.intersection(development)),
        "support_final_overlap": len(support.intersection(final)),
        "development_final_overlap": len(development.intersection(final)),
    }


def _aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aggregate = []
    for partition in ("development", "final"):
        selected = [row for row in rows if row["partition"] == partition]
        aggregate.append(
            {
                "partition": partition,
                "seeds": len(selected),
                "episodes": sum(row["episodes"] for row in selected),
                "candidate_success_rate": round(
                    sum(row["candidate_success_rate"] * row["episodes"] for row in selected)
                    / sum(row["episodes"] for row in selected),
                    6,
                ),
                "no_candidate_success_rate": round(
                    sum(row["no_candidate_success_rate"] * row["episodes"] for row in selected)
                    / sum(row["episodes"] for row in selected),
                    6,
                ),
                "paired_delta": round(
                    sum(row["paired_delta"] for row in selected) / len(selected), 6
                ),
                "false_generalization_delta": round(
                    sum(row["false_generalization_delta"] for row in selected)
                    / len(selected),
                    6,
                ),
                "compressed_readout_candidate_success_rate": round(
                    sum(row["compressed_readout_candidate_success_rate"] for row in selected)
                    / len(selected),
                    6,
                ),
                "compressed_readout_no_candidate_success_rate": round(
                    sum(row["compressed_readout_no_candidate_success_rate"] for row in selected)
                    / len(selected),
                    6,
                ),
                "compaction_applied_for_all_seeds": all(
                    row["compaction_applied"] for row in selected
                ),
                "mean_role_readout_bytes_before": round(
                    sum(row["role_readout_bytes_before"] for row in selected)
                    / len(selected)
                ),
                "mean_role_readout_bytes_after": round(
                    sum(row["role_readout_bytes_after"] for row in selected)
                    / len(selected)
                ),
                "mean_total_state_bytes_before": round(
                    sum(row["total_state_bytes_before"] for row in selected)
                    / len(selected)
                ),
                "mean_total_state_bytes_after": round(
                    sum(row["total_state_bytes_after"] for row in selected)
                    / len(selected)
                ),
                "mean_full_candidate_state_bytes": round(
                    sum(row["full_candidate_state_bytes"] for row in selected)
                    / len(selected)
                ),
                "mean_reconstructed_candidate_state_bytes": round(
                    sum(
                        row["reconstructed_candidate_state_bytes"]
                        for row in selected
                    )
                    / len(selected)
                ),
                "mean_verbose_event_state_bytes": round(
                    sum(row["verbose_event_state_bytes"] for row in selected)
                    / len(selected)
                ),
                "mean_compact_event_state_bytes": round(
                    sum(row["compact_event_state_bytes"] for row in selected)
                    / len(selected)
                ),
                "mean_uncompressed_reconstructable_state_bytes": round(
                    sum(
                        row["uncompressed_reconstructable_state_bytes"]
                        for row in selected
                    )
                    / len(selected)
                ),
                "mean_verbose_derived_state_bytes": round(
                    sum(row["verbose_derived_state_bytes"] for row in selected)
                    / len(selected)
                ),
                "mean_compact_derived_state_bytes": round(
                    sum(row["compact_derived_state_bytes"] for row in selected)
                    / len(selected)
                ),
                "mean_prediction_p95_ms_before": round(
                    sum(row["prediction_p95_ms_before"] for row in selected)
                    / len(selected),
                    6,
                ),
                "mean_prediction_p95_ms_after": round(
                    sum(row["prediction_p95_ms_after"] for row in selected)
                    / len(selected),
                    6,
                ),
                "regression_queries_checked": sum(
                    row["regression_queries_checked"] for row in selected
                ),
            }
        )
    return aggregate


def _mean(values: list[int]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def _serialized_state_bytes(state: RisaState) -> int:
    return len(
        json.dumps(
            state.to_dict(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )


def _full_candidate_state_bytes(state: RisaState) -> int:
    payload = state.to_dict()
    payload.pop("candidate_evaluations", None)
    payload["unnamed_concept_candidates"] = {
        key: candidate.to_dict()
        for key, candidate in state.unnamed_concept_candidates.items()
    }
    return len(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _verbose_event_state_bytes(state: RisaState) -> int:
    payload = state.to_dict()
    payload["events"] = {
        key: event.to_dict() for key, event in state.events_by_id.items()
    }
    return len(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _uncompressed_reconstructable_state_bytes(state: RisaState) -> int:
    payload = state.to_dict()
    payload.pop("candidate_evaluations", None)
    payload["events"] = {
        key: event.to_dict() for key, event in state.events_by_id.items()
    }
    payload["unnamed_concept_candidates"] = {
        key: candidate.to_dict()
        for key, candidate in state.unnamed_concept_candidates.items()
    }
    _restore_verbose_derived_records(payload, state)
    return len(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _verbose_derived_state_bytes(state: RisaState) -> int:
    payload = state.to_dict()
    _restore_verbose_derived_records(payload, state)
    return len(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _restore_verbose_derived_records(
    payload: dict[str, Any],
    state: RisaState,
) -> None:
    payload["patterns"] = {
        key: pattern.to_dict() for key, pattern in state.patterns.items()
    }
    payload["structural_patterns"] = {
        key: pattern.to_dict()
        for key, pattern in state.structural_patterns.items()
    }
    payload["structural_primitives"] = {
        key: primitive.to_dict()
        for key, primitive in state.structural_primitives.items()
    }


def _prediction_p95_ms(
    state: RisaState,
    queries: list[PredictionQuery],
    repetitions: int = 5,
) -> float:
    if not queries:
        return 0.0
    predict_next_effect(state, queries[0])
    samples: list[float] = []
    for _ in range(repetitions):
        for query in queries:
            started = time.perf_counter_ns()
            predict_next_effect(state, query)
            samples.append((time.perf_counter_ns() - started) / 1_000_000)
    samples.sort()
    index = max(0, int(0.95 * len(samples) + 0.999999) - 1)
    return round(samples[index], 6)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", default="experiments/g2_candidate_manifest.json"
    )
    parser.add_argument(
        "--output", default="docs/g2-candidate-transfer-results.json"
    )
    args = parser.parse_args()
    result = run_candidate_transfer(load_manifest(args.manifest))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": args.output, "rows": len(result["rows"])}, indent=2))


if __name__ == "__main__":
    main()
