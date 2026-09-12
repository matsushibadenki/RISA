"""Compare indexed prediction with an Event-scan reference at bounded scales."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
from statistics import median
from time import perf_counter, perf_counter_ns
from typing import Any

from risa.core.models import Event, PredictionQuery, StructuralPrimitive
from risa.core.state import RisaState
from risa.engine.event_order import (
    index_event_order,
    rebuild_event_order,
    replay_event_window,
)
from risa.engine.evidence import index_event_evidence
from risa.engine.prediction_access import predict_next_effect_with_access
from risa.engine.prediction_indexes import rebuild_prediction_indexes
from risa.engine.replay import replay_structural_memory


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if not manifest.get("event_scales") or any(
        int(scale) < 1 for scale in manifest["event_scales"]
    ):
        raise ValueError("event_scales must contain positive values")
    for key in (
        "queries_per_scale",
        "action_count",
        "actor_count",
        "context_count",
        "replay_budget",
    ):
        if int(manifest[key]) < 1:
            raise ValueError(f"{key} must be positive")
    return manifest


def run_scale_evaluation(manifest: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    stopped_scales: list[dict[str, Any]] = []
    for raw_seed in manifest["seeds"]:
        seed = int(raw_seed)
        for raw_scale in manifest["event_scales"]:
            scale = int(raw_scale)
            started = perf_counter()
            state = _scale_state(seed, scale, manifest)
            queries = _queries(seed, scale, manifest, state)
            for query, _ in queries[: int(manifest.get("warmup_queries", 0))]:
                predict_next_effect_with_access(state, query, mode="indexed")

            indexed_ns: list[int] = []
            scan_ns: list[int] = []
            indexed_work: list[int] = []
            scan_work: list[int] = []
            indexed_correct = 0
            scan_correct = 0
            mismatches = 0
            for query, expected in queries:
                indexed, indexed_stats = predict_next_effect_with_access(
                    state, query, mode="indexed"
                )
                scanned, scan_stats = predict_next_effect_with_access(
                    state, query, mode="full_scan"
                )
                indexed_ns.append(indexed_stats.elapsed_ns)
                scan_ns.append(scan_stats.elapsed_ns)
                indexed_work.append(indexed_stats.events_examined)
                scan_work.append(scan_stats.events_examined)
                indexed_correct += indexed.predicted_effects == [expected]
                scan_correct += scanned.predicted_effects == [expected]
                mismatches += indexed.to_dict() != scanned.to_dict()

            update_samples = _incremental_order_update_samples(state, 9)
            replay_budget = int(manifest["replay_budget"])
            replay_selection_samples = []
            indexed_replay_events = []
            replay_selection_work = 0
            for _ in range(9):
                replay_selection_started = perf_counter_ns()
                indexed_replay_events, replay_selection_work = replay_event_window(
                    state, replay_budget
                )
                replay_selection_samples.append(
                    perf_counter_ns() - replay_selection_started
                )
            indexed_replay_ids = [event.id for event in indexed_replay_events]
            full_scan_replay_ids = [
                event.id
                for event in sorted(
                    state.events_by_id.values(),
                    key=lambda item: (item.timestamp, item.id),
                )[-replay_budget:]
            ]
            replay_summary = replay_structural_memory(
                state, max_events=replay_budget
            )
            query_count = len(queries)
            indexed_accuracy = indexed_correct / query_count
            scan_accuracy = scan_correct / query_count
            mean_indexed_work = sum(indexed_work) / query_count
            mean_scan_work = sum(scan_work) / query_count
            row = {
                "seed": seed,
                "event_scale": scale,
                "query_count": query_count,
                "indexed_accuracy": round(indexed_accuracy, 6),
                "full_scan_accuracy": round(scan_accuracy, 6),
                "quality_loss": round(scan_accuracy - indexed_accuracy, 6),
                "prediction_mismatches": mismatches,
                "indexed_mean_events_examined": round(mean_indexed_work, 3),
                "full_scan_mean_events_examined": round(mean_scan_work, 3),
                "event_work_reduction": round(
                    mean_scan_work / max(1.0, mean_indexed_work), 3
                ),
                "indexed_p50_ms": _percentile_ms(indexed_ns, 0.50),
                "indexed_p95_ms": _percentile_ms(indexed_ns, 0.95),
                "full_scan_p50_ms": _percentile_ms(scan_ns, 0.50),
                "full_scan_p95_ms": _percentile_ms(scan_ns, 0.95),
                "latency_reduction": round(
                    _percentile_ns(scan_ns, 0.95)
                    / max(1, _percentile_ns(indexed_ns, 0.95)),
                    3,
                ),
                "incremental_order_update_p50_ms": round(
                    median(update_samples) / 1_000_000, 6
                ),
                "incremental_order_update_p95_ms": round(
                    _percentile_ns(update_samples, 0.95) / 1_000_000, 6
                ),
                "incremental_order_update_scope": 1,
                "replay_budget": replay_budget,
                "replay_window_mismatches": sum(
                    left != right
                    for left, right in zip(
                        indexed_replay_ids, full_scan_replay_ids
                    )
                )
                + abs(len(indexed_replay_ids) - len(full_scan_replay_ids)),
                "replay_selection_events_examined": (
                    replay_summary.selection_events_examined
                ),
                "replay_selection_p95_ms": _percentile_ms(
                    replay_selection_samples, 0.95
                ),
                "replay_selection_reported_work": replay_selection_work,
                "replayed_events": replay_summary.replayed_events,
                "stored_bytes": len(
                    json.dumps(
                        state.to_dict(), sort_keys=True, separators=(",", ":")
                    ).encode("utf-8")
                ),
                "elapsed_seconds": round(perf_counter() - started, 6),
            }
            rows.append(row)
            if row["elapsed_seconds"] > float(
                manifest["scale_time_budget_seconds"]
            ):
                stopped_scales.append(
                    {
                        "seed": seed,
                        "event_scale": scale,
                        "elapsed_seconds": row["elapsed_seconds"],
                    }
                )
                break

    tolerance = float(manifest["quality_loss_tolerance"])
    minimum_work_reduction = float(manifest["minimum_work_reduction"])
    all_exact = all(
        row["prediction_mismatches"] == 0
        and row["indexed_accuracy"] + tolerance >= row["full_scan_accuracy"]
        for row in rows
    )
    work_gate = all(
        row["event_work_reduction"] >= minimum_work_reduction for row in rows
    )
    replay_gate = all(
        row["replayed_events"] <= row["replay_budget"]
        and row["replay_selection_events_examined"] <= row["replay_budget"]
        and row["replay_selection_reported_work"] <= row["replay_budget"]
        and row["replay_window_mismatches"] == 0
        for row in rows
    )
    expected_rows = len(manifest["seeds"]) * len(manifest["event_scales"])
    manifest_digest = hashlib.sha256(
        json.dumps(manifest, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "benchmark_version": manifest["benchmark_version"],
        "manifest_sha256": manifest_digest,
        "manifest": manifest,
        "rows": rows,
        "aggregate": {
            "completed_scale_rows": len(rows),
            "expected_scale_rows": expected_rows,
            "maximum_completed_event_scale": max(
                (row["event_scale"] for row in rows), default=0
            ),
            "prediction_mismatches": sum(
                row["prediction_mismatches"] for row in rows
            ),
            "minimum_event_work_reduction": min(
                (row["event_work_reduction"] for row in rows), default=0.0
            ),
            "minimum_latency_reduction": min(
                (row["latency_reduction"] for row in rows), default=0.0
            ),
            "maximum_replay_selection_events_examined": max(
                (row["replay_selection_events_examined"] for row in rows),
                default=0,
            ),
            "replay_window_mismatches": sum(
                row["replay_window_mismatches"] for row in rows
            ),
            "stopped_scales": stopped_scales,
        },
        "decision": (
            "adopt_indexed_event_access_and_bounded_replay"
            if all_exact
            and work_gate
            and replay_gate
            and len(rows) == expected_rows
            else "scale_gate_incomplete"
        ),
    }


def _scale_state(seed: int, scale: int, manifest: dict[str, Any]) -> RisaState:
    action_count = int(manifest["action_count"])
    actor_count = int(manifest["actor_count"])
    context_count = int(manifest["context_count"])
    state = RisaState()
    for index in range(scale):
        action_index = index % action_count
        event = Event(
            id=f"scale-{seed}-{index:06d}",
            timestamp=index + 1,
            actor=f"actor-{index % actor_count}",
            action=f"action-{action_index}",
            observed_effects=[f"effect-{action_index}"],
            context_tags=[f"context-{index % context_count}"],
            episode_id=f"scale-{seed}",
            source="synthetic-scale",
        )
        state.events_by_id[event.id] = event
        state.event_primitive_ids[event.id] = [f"scale-primitive-{action_index}"]
    for action_index in range(min(action_count, scale)):
        primitive_id = f"scale-primitive-{action_index}"
        state.structural_primitives[primitive_id] = StructuralPrimitive(
            id=primitive_id,
            relation_type="transition",
            role_signature="entity->process->state",
            input_conditions={f"process:action-{action_index}"},
            output_state=f"effect-{action_index}",
            support=max(1, scale // action_count),
            validation_score=1.0,
            reuse_score=1.0,
            adoption_score=1.0,
            adopted=True,
        )
    rebuild_event_order(state)
    rebuild_prediction_indexes(state)
    for event in state.events_by_id.values():
        index_event_evidence(state, event)
    return state


def _queries(
    seed: int,
    scale: int,
    manifest: dict[str, Any],
    state: RisaState,
) -> list[tuple[PredictionQuery, str]]:
    randomizer = random.Random(seed + scale)
    events = list(state.events_by_id.values())
    queries = []
    for _ in range(int(manifest["queries_per_scale"])):
        event = events[randomizer.randrange(len(events))]
        queries.append(
            (
                PredictionQuery(
                    actor=event.actor,
                    action=event.action,
                    context_tags=list(event.context_tags),
                    enable_candidate_concepts=False,
                    enable_change_adaptation=False,
                ),
                event.observed_effects[0],
            )
        )
    return queries


def _incremental_order_update_samples(
    state: RisaState,
    repetitions: int,
) -> list[int]:
    samples = []
    latest_timestamp = max(
        (event.timestamp for event in state.events_by_id.values()), default=0
    )
    for index in range(repetitions):
        event = Event(
            id=f"order-probe-{index}",
            timestamp=latest_timestamp + 1,
            actor="probe",
            action="probe",
        )
        state.events_by_id[event.id] = event
        started = perf_counter_ns()
        index_event_order(state, event)
        samples.append(perf_counter_ns() - started)
        state.event_order.pop()
        state.events_by_id.pop(event.id)
    return samples


def _percentile_ns(values: list[int], quantile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, int(quantile * len(ordered) + 0.999999) - 1)
    return ordered[index]


def _percentile_ms(values: list[int], quantile: float) -> float:
    return round(_percentile_ns(values, quantile) / 1_000_000, 6)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="experiments/g3_scale_manifest.json")
    parser.add_argument("--output", default="docs/g3-scale-results.json")
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    result = run_scale_evaluation(manifest)
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": args.output, "decision": result["decision"]}))


if __name__ == "__main__":
    main()
