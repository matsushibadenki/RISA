"""Evaluate bounded conjunction search with correlated context proxies."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
from typing import Any

from risa.core.models import Event, UnnamedConceptCandidate
from risa.core.state import RisaState
from risa.engine.candidate_discovery import (
    _candidate_context_matches,
    evaluate_derived_candidate,
    rebuild_candidate_inference_index,
    select_derived_candidates_for_final,
)
from risa.engine.runtime import TrainingOptions, train_events


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in (
        "development_episodes_per_seed",
        "final_episodes_per_seed",
        "bootstrap_samples",
        "proxy_count",
    ):
        if int(manifest[key]) < 1:
            raise ValueError(f"{key} must be positive")
    return manifest


def run_context_conjunction_evaluation(manifest: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    lifecycle: list[dict[str, Any]] = []
    for raw_seed in manifest["seeds"]:
        seed = int(raw_seed)
        state, broad, candidates, stable = _training_state(
            seed, int(manifest["proxy_count"])
        )
        development = _cases(
            seed,
            "development",
            int(manifest["development_episodes_per_seed"]),
            int(manifest["proxy_count"]),
        )
        final = _cases(
            seed,
            "final",
            int(manifest["final_episodes_per_seed"]),
            int(manifest["proxy_count"]),
        )
        development_rows = []
        for index, candidate in enumerate(candidates):
            metrics = _compare(candidate, broad, development)
            baseline_interval = _paired_bootstrap_interval(
                metrics["candidate_successes"],
                metrics["baseline_successes"],
                int(manifest["bootstrap_samples"]),
                seed + index,
            )
            parent_interval = _paired_bootstrap_interval(
                metrics["candidate_successes"],
                metrics["parent_successes"],
                int(manifest["bootstrap_samples"]),
                seed + 100 + index,
            )
            evaluate_derived_candidate(
                state,
                candidate.id,
                partition="development",
                evaluation_event_ids=[str(case["id"]) for case in development],
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
            development_rows.append(
                {
                    "candidate_id": candidate.id,
                    "condition": candidate.structural_schema["required_context_tags"],
                    "success_rate": _mean(metrics["candidate_successes"]),
                    "parent_delta": metrics["parent_delta"],
                    "parent_delta_95ci": list(parent_interval),
                }
            )
        selected = select_derived_candidates_for_final(
            state, [candidate.id for candidate in candidates]
        )
        selected_candidate = selected[0]
        final_metrics = _compare(selected_candidate, broad, final)
        final_baseline_interval = _paired_bootstrap_interval(
            final_metrics["candidate_successes"],
            final_metrics["baseline_successes"],
            int(manifest["bootstrap_samples"]),
            seed + 1000,
        )
        final_parent_interval = _paired_bootstrap_interval(
            final_metrics["candidate_successes"],
            final_metrics["parent_successes"],
            int(manifest["bootstrap_samples"]),
            seed + 2000,
        )
        evaluate_derived_candidate(
            state,
            selected_candidate.id,
            partition="final",
            evaluation_event_ids=[str(case["id"]) for case in final],
            prediction_delta=final_metrics["baseline_delta"],
            composition_delta=0.0,
            prediction_delta_ci_lower=final_baseline_interval[0],
            composition_delta_ci_lower=0.0,
            false_generalization_delta=final_metrics["false_generalization_delta"],
            parent_prediction_delta=final_metrics["parent_delta"],
            parent_composition_delta=0.0,
            parent_prediction_delta_ci_lower=final_parent_interval[0],
            parent_composition_delta_ci_lower=0.0,
            minimum_gain=float(manifest["minimum_gain"]),
        )
        rows.append(
            {
                "seed": seed,
                "partition": "final",
                "episodes": len(final),
                "generated_candidates": len(candidates),
                "explored_hypotheses": stable.proposal_hypothesis_count,
                "selected_condition": selected_candidate.structural_schema[
                    "required_context_tags"
                ],
                "candidate_success_rate": _mean(final_metrics["candidate_successes"]),
                "parent_success_rate": _mean(final_metrics["parent_successes"]),
                "paired_delta": final_metrics["parent_delta"],
                "paired_delta_95ci": list(final_parent_interval),
                "candidate_false_generalization_rate": final_metrics[
                    "candidate_false_rate"
                ],
                "parent_false_generalization_rate": final_metrics[
                    "parent_false_rate"
                ],
            }
        )
        lifecycle.append(
            {
                "seed": seed,
                "support_ids": list(broad.supporting_event_ids),
                "development_ids": [str(case["id"]) for case in development],
                "final_ids": [str(case["id"]) for case in final],
                "development_candidates": development_rows,
                "selected_candidate_id": selected_candidate.id,
                "stable_candidate_id": stable.id,
                "selected_stable_condition": selected_candidate.id == stable.id,
                "after_final": selected_candidate.lifecycle_status,
                "broad_ancestor_dormant": broad.dormant,
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
            "adopt_bounded_conjunction_selection"
            if all(
                row["selected_stable_condition"]
                and row["after_final"] == "adopted"
                and row["broad_ancestor_dormant"]
                for row in lifecycle
            )
            else "reject"
        ),
    }


def _training_state(
    seed: int, proxy_count: int
) -> tuple[
    RisaState,
    UnnamedConceptCandidate,
    list[UnnamedConceptCandidate],
    UnnamedConceptCandidate,
]:
    state = RisaState()
    proxies = [f"proxy_{index}" for index in range(proxy_count)]
    events: list[Event] = []
    timestamp = 1
    for index in range(48):
        events.append(
            _event(seed, timestamp, "warm", ["powered", "indoor", *proxies])
        )
        timestamp += 1
    for _ in range(24):
        events.append(
            _event(seed, timestamp, "cold", ["powered", "outdoor", *proxies])
        )
        timestamp += 1
        events.append(
            _event(seed, timestamp, "cold", ["unpowered", "indoor"])
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
    broad = next(
        candidate
        for candidate in state.unnamed_concept_candidates.values()
        if candidate.derivation_generation == 0
        and candidate.structural_schema.get("effects") == ["warm"]
    )
    candidates = sorted(
        (
            candidate
            for candidate in state.unnamed_concept_candidates.values()
            if candidate.parent_candidate_ids == [broad.id]
            and candidate.derivation_type == "specialized"
        ),
        key=lambda candidate: candidate.id,
    )
    stable = next(
        candidate
        for candidate in candidates
        if candidate.structural_schema.get("required_context_tags")
        == ["indoor", "powered"]
    )
    broad.lifecycle_status = "adopted"
    rebuild_candidate_inference_index(state)
    return state, broad, candidates, stable


def _event(seed: int, timestamp: int, effect: str, tags: list[str]) -> Event:
    return Event(
        id=f"support:{seed}:{timestamp}",
        timestamp=timestamp,
        actor=f"trainer-{timestamp}",
        action="inspect",
        target=f"device-{timestamp}",
        target_roles=["device"],
        context_tags=tags,
        observed_effects=[effect],
        episode_id=f"support:{seed}:{timestamp}",
        source=f"sensor-{timestamp}",
    )


def _cases(
    seed: int, partition: str, count: int, proxy_count: int
) -> list[dict[str, object]]:
    rng = random.Random(f"{seed}:{partition}")
    cases = []
    for index in range(count):
        expected = index % 2 == 0
        if expected:
            tags = ["powered", "indoor"]
            proxy_probability = 0.8
        elif index % 4 == 1:
            tags = ["powered", "outdoor"]
            proxy_probability = 0.8
        else:
            tags = ["unpowered", "indoor"]
            proxy_probability = 0.2
        tags.extend(
            f"proxy_{proxy}"
            for proxy in range(proxy_count)
            if rng.random() < proxy_probability
        )
        cases.append(
            {
                "id": f"{partition}:{seed}:{index}",
                "context_tags": tags,
                "expected": expected,
            }
        )
    rng.shuffle(cases)
    return cases


def _compare(
    candidate: UnnamedConceptCandidate,
    parent: UnnamedConceptCandidate,
    cases: list[dict[str, object]],
) -> dict[str, Any]:
    candidate_successes: list[int] = []
    parent_successes: list[int] = []
    baseline_successes: list[int] = []
    candidate_false = parent_false = negatives = 0
    for case in cases:
        tags = [str(tag) for tag in case["context_tags"]]
        expected = bool(case["expected"])
        candidate_output = _candidate_context_matches(candidate, tags)
        parent_output = _candidate_context_matches(parent, tags)
        candidate_successes.append(int(candidate_output == expected))
        parent_successes.append(int(parent_output == expected))
        baseline_successes.append(int(False == expected))
        if not expected:
            negatives += 1
            candidate_false += int(candidate_output)
            parent_false += int(parent_output)
    return {
        "candidate_successes": candidate_successes,
        "parent_successes": parent_successes,
        "baseline_successes": baseline_successes,
        "parent_delta": _mean(candidate_successes) - _mean(parent_successes),
        "baseline_delta": _mean(candidate_successes) - _mean(baseline_successes),
        "candidate_false_rate": candidate_false / negatives,
        "parent_false_rate": parent_false / negatives,
        "false_generalization_delta": (candidate_false - parent_false) / negatives,
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
    return (
        deltas[int(samples * 0.025)],
        deltas[min(samples - 1, int(samples * 0.975))],
    )


def _mean(values: list[int]) -> float:
    return sum(values) / len(values)


def _audit(lifecycle: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "support_development_overlap": 0,
        "support_final_overlap": 0,
        "development_final_overlap": 0,
    }
    for row in lifecycle:
        support = set(row["support_ids"])
        development = set(row["development_ids"])
        final = set(row["final_ids"])
        counts["support_development_overlap"] += len(support & development)
        counts["support_final_overlap"] += len(support & final)
        counts["development_final_overlap"] += len(development & final)
    return counts


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        key: sum(float(row[key]) for row in rows) / len(rows)
        for key in (
            "generated_candidates",
            "explored_hypotheses",
            "candidate_success_rate",
            "parent_success_rate",
            "paired_delta",
            "candidate_false_generalization_rate",
            "parent_false_generalization_rate",
        )
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", default="experiments/g2_context_conjunction_manifest.json"
    )
    parser.add_argument(
        "--output", default="docs/g2-context-conjunction-results.json"
    )
    args = parser.parse_args()
    result = run_context_conjunction_evaluation(load_manifest(args.manifest))
    Path(args.output).write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["aggregate"], indent=2))


if __name__ == "__main__":
    main()
