"""Evaluate schema-v4 persistence over full G2 training states and probes."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time
from typing import Any

from experiments.candidate_transfer_evaluation import (
    _uncompressed_reconstructable_state_bytes,
)
from risa.core.state import RisaState
from risa.engine.composer import compose_to_effect
from risa.engine.simulator import simulate_branches
from risa.evaluation.benchmark import (
    RisaEvaluationModel,
    _plan,
    generate_benchmark,
    load_manifest,
)


def run_persistence_evaluation(config: dict[str, Any]) -> dict[str, Any]:
    source_manifest = load_manifest(config["source_manifest"])
    rows = []
    for raw_seed in config["seeds"]:
        seed = int(raw_seed)
        generated = generate_benchmark(seed, source_manifest)
        model = RisaEvaluationModel(
            "risa",
            source_manifest.online_replay_budget,
            source_manifest.online_replay_interval,
            enable_g2_features=True,
        )
        model.observe_many(generated.training_events)
        state = model.state
        payload = state.to_dict()
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        compact_bytes = len(encoded.encode("utf-8"))
        verbose_bytes = _uncompressed_reconstructable_state_bytes(state)

        prediction_cases = generated.static_cases
        planning_cases = [case for case in prediction_cases if case.goal_states]
        before_predictions = [model.predict(case) for case in prediction_cases]
        before_plans = [_plan(model, case) for case in planning_cases]
        before_composition = _composition_probe(state)
        before_simulation = _simulation_probe(state)

        load_samples = []
        restored = state
        for _ in range(int(config["load_repetitions"])):
            started = time.perf_counter_ns()
            restored = RisaState.from_dict(json.loads(encoded))
            load_samples.append((time.perf_counter_ns() - started) / 1_000_000)
        restored_model = RisaEvaluationModel(
            "risa",
            source_manifest.online_replay_budget,
            source_manifest.online_replay_interval,
            enable_g2_features=True,
        )
        restored_model.state = restored
        after_predictions = [restored_model.predict(case) for case in prediction_cases]
        after_plans = [_plan(restored_model, case) for case in planning_cases]
        load_samples.sort()
        rows.append(
            {
                "seed": seed,
                "events": len(state.events_by_id),
                "prediction_queries": len(prediction_cases),
                "planning_queries": len(planning_cases),
                "verbose_equivalent_bytes": verbose_bytes,
                "schema_v4_bytes": compact_bytes,
                "saved_bytes": verbose_bytes - compact_bytes,
                "saved_fraction": round((verbose_bytes - compact_bytes) / verbose_bytes, 6),
                "load_p95_ms": _p95(load_samples),
                "prediction_mismatches": sum(
                    left != right for left, right in zip(before_predictions, after_predictions)
                ),
                "planning_mismatches": sum(
                    left != right for left, right in zip(before_plans, after_plans)
                ),
                "composition_match": before_composition == _composition_probe(restored),
                "simulation_match": before_simulation == _simulation_probe(restored),
            }
        )
    total_verbose = sum(row["verbose_equivalent_bytes"] for row in rows)
    total_compact = sum(row["schema_v4_bytes"] for row in rows)
    all_equivalent = all(
        row["prediction_mismatches"] == 0
        and row["planning_mismatches"] == 0
        and row["composition_match"]
        and row["simulation_match"]
        for row in rows
    )
    digest = hashlib.sha256(
        json.dumps(config, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "benchmark_version": config["benchmark_version"],
        "manifest_sha256": digest,
        "manifest": config,
        "rows": rows,
        "aggregate": {
            "seeds": len(rows),
            "events": sum(row["events"] for row in rows),
            "prediction_queries": sum(row["prediction_queries"] for row in rows),
            "planning_queries": sum(row["planning_queries"] for row in rows),
            "mean_verbose_equivalent_bytes": round(total_verbose / len(rows)),
            "mean_schema_v4_bytes": round(total_compact / len(rows)),
            "saved_fraction": round((total_verbose - total_compact) / total_verbose, 6),
            "mean_load_p95_ms": round(sum(row["load_p95_ms"] for row in rows) / len(rows), 6),
            "prediction_mismatches": sum(row["prediction_mismatches"] for row in rows),
            "planning_mismatches": sum(row["planning_mismatches"] for row in rows),
            "composition_matches": sum(row["composition_match"] for row in rows),
            "simulation_matches": sum(row["simulation_match"] for row in rows),
        },
        "decision": "accepted_schema_v4_persistence" if all_equivalent and total_compact < total_verbose else "persistence_gate_failed",
    }


def _composition_probe(state: RisaState) -> tuple[object, ...]:
    result = compose_to_effect(state, "collect_key", "inside", max_steps=3)
    return tuple(result.primitive_ids), tuple(result.added_states), tuple(result.removed_states)


def _simulation_probe(state: RisaState) -> list[dict[str, object]]:
    return [asdict(branch) for branch in simulate_branches(state, "activate", max_steps=1)]


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(values[max(0, int(0.95 * len(values) + 0.999999) - 1)], 6)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="experiments/g2_persistence_manifest.json")
    parser.add_argument("--output", default="docs/g2-persistence-results.json")
    args = parser.parse_args()
    config = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    result = run_persistence_evaluation(config)
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": args.output, "decision": result["decision"]}))


if __name__ == "__main__":
    main()
