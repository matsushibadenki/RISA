"""Evaluate arbitrary typed entity-relation candidates on held-out bindings."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.temporal_candidate_evaluation import (
    _mean,
    _paired_bootstrap_interval,
    load_manifest,
)
from risa.core.models import Event
from risa.core.state import RisaState
from risa.engine.candidate_discovery import (
    evaluate_unnamed_candidate,
    rebuild_candidate_inference_index,
)
from risa.engine.composer import compose_to_effect
from risa.engine.runtime import TrainingOptions, train_events


def run_generic_relation_evaluation(manifest: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    lifecycle: list[dict[str, Any]] = []
    for seed_value in manifest["seeds"]:
        seed = int(seed_value)
        state = _training_state(seed)
        candidate = next(
            item
            for item in state.unnamed_concept_candidates.values()
            if item.structural_schema.get("kind") == "relational_sequence"
        )
        development = _cases(seed, "development", manifest["development_episodes_per_seed"])
        final = _cases(seed, "final", manifest["final_episodes_per_seed"])
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
        for partition, cases in (("development", development), ("final", final)):
            metrics = _compare(state, candidate.id, cases)
            interval = _paired_bootstrap_interval(
                metrics["candidate_successes"],
                metrics["baseline_successes"],
                manifest["bootstrap_samples"],
                seed + (partition == "final"),
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
        lifecycle.append(
            {
                "seed": seed,
                "candidate_id": candidate.id,
                "after_final": candidate.lifecycle_status,
                "support_ids": list(candidate.supporting_event_ids),
                "development_ids": [case["id"] for case in development],
                "final_ids": [case["id"] for case in final],
            }
        )

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
        "decision": (
            "adopted_generic_relation_candidate"
            if all(item["after_final"] == "adopted" for item in lifecycle)
            else "generic_relation_gate_requires_review"
        ),
    }


def _training_state(seed: int) -> RisaState:
    state = RisaState()
    events: list[Event] = []
    timestamp = 1
    for suffix, source in (("a", "sensor-a"), ("b", "sensor-b")):
        episode = f"support:{seed}:{suffix}"
        bindings = {
            "operator": f"robot-{suffix}",
            "credential": f"key-{suffix}",
            "resource": f"door-{suffix}",
        }
        roles = {
            "operator": ["controller"],
            "credential": ["access_key"],
            "resource": ["lockable"],
        }
        relations = [
            {"source": "operator", "relation": "holds", "target": "credential"},
            {"source": "credential", "relation": "opens", "target": "resource"},
        ]
        events.extend(
            [
                Event(
                    f"{episode}:present", timestamp, f"robot-{suffix}", "present",
                    observed_effects=["authenticated"], episode_id=episode, source=source,
                    entity_bindings=dict(bindings),
                    entity_role_bindings={key: list(value) for key, value in roles.items()},
                    entity_relations=[dict(relation) for relation in relations],
                ),
                Event(
                    f"{episode}:unlock", timestamp + 1, f"robot-{suffix}", "unlock",
                    preconditions=["authenticated"], observed_states_before=["authenticated"],
                    before_state_observed=True, observed_effects=["opened"],
                    episode_id=episode, source=source, entity_bindings=dict(bindings),
                    entity_role_bindings={key: list(value) for key, value in roles.items()},
                    entity_relations=[dict(relation) for relation in relations],
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


def _cases(seed: int, partition: str, count: int) -> list[dict[str, object]]:
    base_roles = {
        "operator": ["controller"],
        "credential": ["access_key"],
        "resource": ["lockable"],
    }
    base_bindings = {
        "operator": "robot-new",
        "credential": "key-new",
        "resource": "door-new",
    }
    base_relations = [
        {"source": "operator", "relation": "holds", "target": "credential"},
        {"source": "credential", "relation": "opens", "target": "resource"},
    ]
    cases = []
    for index in range(int(count)):
        variant = index % 5
        roles = {key: list(value) for key, value in base_roles.items()}
        bindings = dict(base_bindings)
        relations = [dict(relation) for relation in base_relations]
        expected = variant == 0
        if variant == 1:
            roles["operator"] = ["observer"]
        elif variant == 2:
            relations = relations[:1]
        elif variant == 3:
            bindings["resource"] = bindings["credential"]
        elif variant == 4:
            relations[1]["relation"] = "closes"
        cases.append(
            {
                "id": f"{partition}:{seed}:{index}",
                "roles": roles,
                "bindings": bindings,
                "relations": relations,
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
        "present",
        "opened",
        max_steps=2,
        entity_bindings=dict(case["bindings"]),
        entity_role_bindings=dict(case["roles"]),
        entity_relations=list(case["relations"]),
        enable_candidate_concepts=enabled,
    )
    return bool(result.primitive_ids)


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
    aggregate = []
    for partition in ("development", "final"):
        selected = [row for row in rows if row["partition"] == partition]
        episodes = sum(row["episodes"] for row in selected)
        aggregate.append(
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
    return aggregate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", default="experiments/g2_generic_relation_manifest.json"
    )
    parser.add_argument("--output", default="docs/g2-generic-relation-results.json")
    arguments = parser.parse_args()
    result = run_generic_relation_evaluation(load_manifest(arguments.manifest))
    Path(arguments.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["aggregate"], indent=2))
    print(result["decision"])


if __name__ == "__main__":
    main()
