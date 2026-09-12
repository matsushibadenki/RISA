"""Evaluate bounded role disambiguation and role-free plan-variable transfer."""

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
from risa.engine.composer import compose_to_effect, forecast_next_effects
from risa.engine.predictor import predict_next_effect
from risa.engine.role_induction import (
    MAX_ROLE_REFINEMENTS_PER_BASE,
    MAX_ROLE_SIGNATURE_HOPS,
)
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
    if int(manifest["max_role_hops"]) != MAX_ROLE_SIGNATURE_HOPS:
        raise ValueError("manifest max_role_hops must match the runtime role budget")
    if (
        int(manifest["max_role_refinements_per_base"])
        != MAX_ROLE_REFINEMENTS_PER_BASE
    ):
        raise ValueError(
            "manifest max_role_refinements_per_base must match the runtime role budget"
        )
    return manifest


def run_role_disambiguation_evaluation(manifest: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    lifecycle: list[dict[str, Any]] = []
    for raw_seed in manifest["seeds"]:
        seed = int(raw_seed)
        induced_collision = _collision_training_state(seed, supplied_roles=False)
        supplied_collision = _collision_training_state(seed, supplied_roles=True)
        induced_plans = _plan_training_state(seed, supplied_roles=False)
        supplied_plans = _plan_training_state(seed, supplied_roles=True)
        collision_candidates = _candidates(induced_collision, "single_transition")
        supplied_collision_candidates = _candidates(
            supplied_collision, "single_transition"
        )
        plan_candidates = _plan_candidates(induced_plans)
        supplied_plan_candidates = _plan_candidates(supplied_plans)
        development = _cases(
            seed, "development", int(manifest["development_episodes_per_seed"])
        )
        final = _cases(seed, "final", int(manifest["final_episodes_per_seed"]))
        lifecycle_row: dict[str, Any] = {
            "seed": seed,
            "support_ids": sorted(
                set(induced_collision.events_by_id) | set(induced_plans.events_by_id)
            ),
            "development_ids": _case_ids(development),
            "final_ids": _case_ids(final),
            "collision_candidate_count": len(collision_candidates),
            "plan_candidate_count": len(plan_candidates),
            "unresolved_beyond_budget_candidate_count": _unresolved_candidate_count(
                seed
            ),
            "role_depths": sorted(
                int(candidate.structural_schema.get("target_role_depth", 0))
                for candidate in collision_candidates
            ),
        }
        for partition_index, (partition, cases) in enumerate(
            (("development", development), ("final", final))
        ):
            collision_metrics = _collision_metrics(
                induced_collision,
                supplied_collision,
                collision_candidates,
                supplied_collision_candidates,
                cases,
            )
            plan_metrics = _plan_metrics(
                induced_plans,
                supplied_plans,
                plan_candidates,
                supplied_plan_candidates,
                cases,
            )
            collision_prediction_ci = _bootstrap(
                collision_metrics["induced_prediction"],
                collision_metrics["bounded_one_hop_prediction"],
                int(manifest["bootstrap_samples"]),
                seed + partition_index,
            )
            supplied_collision_prediction_ci = _bootstrap(
                collision_metrics["supplied_prediction"],
                collision_metrics["bounded_one_hop_prediction"],
                int(manifest["bootstrap_samples"]),
                seed + 10 + partition_index,
            )
            collision_composition_ci = _bootstrap(
                collision_metrics["induced_composition"],
                collision_metrics["bounded_one_hop_composition"],
                int(manifest["bootstrap_samples"]),
                seed + 100 + partition_index,
            )
            supplied_collision_composition_ci = _bootstrap(
                collision_metrics["supplied_composition"],
                collision_metrics["bounded_one_hop_composition"],
                int(manifest["bootstrap_samples"]),
                seed + 110 + partition_index,
            )
            plan_composition_ci = _bootstrap(
                plan_metrics["induced"],
                plan_metrics["disabled"],
                int(manifest["bootstrap_samples"]),
                seed + 200 + partition_index,
            )
            supplied_plan_composition_ci = _bootstrap(
                plan_metrics["supplied"],
                plan_metrics["disabled"],
                int(manifest["bootstrap_samples"]),
                seed + 210 + partition_index,
            )
            _evaluate_candidates(
                induced_collision,
                collision_candidates,
                partition,
                [f"collision:{case['id']}" for case in cases["collision"]],
                prediction_delta=_delta(
                    collision_metrics["induced_prediction"],
                    collision_metrics["bounded_one_hop_prediction"],
                ),
                composition_delta=_delta(
                    collision_metrics["induced_composition"],
                    collision_metrics["bounded_one_hop_composition"],
                ),
                prediction_ci=collision_prediction_ci[0],
                composition_ci=collision_composition_ci[0],
                minimum_gain=float(manifest["minimum_gain"]),
            )
            _evaluate_candidates(
                supplied_collision,
                supplied_collision_candidates,
                partition,
                [f"supplied-collision:{case['id']}" for case in cases["collision"]],
                prediction_delta=_delta(
                    collision_metrics["supplied_prediction"],
                    collision_metrics["bounded_one_hop_prediction"],
                ),
                composition_delta=_delta(
                    collision_metrics["supplied_composition"],
                    collision_metrics["bounded_one_hop_composition"],
                ),
                prediction_ci=supplied_collision_prediction_ci[0],
                composition_ci=supplied_collision_composition_ci[0],
                minimum_gain=float(manifest["minimum_gain"]),
            )
            _evaluate_candidates(
                induced_plans,
                plan_candidates,
                partition,
                [f"plan:{case['id']}" for case in cases["plan"]],
                prediction_delta=0.0,
                composition_delta=_delta(
                    plan_metrics["induced"], plan_metrics["disabled"]
                ),
                prediction_ci=0.0,
                composition_ci=plan_composition_ci[0],
                minimum_gain=float(manifest["minimum_gain"]),
            )
            _evaluate_candidates(
                supplied_plans,
                supplied_plan_candidates,
                partition,
                [f"supplied-plan:{case['id']}" for case in cases["plan"]],
                prediction_delta=0.0,
                composition_delta=_delta(
                    plan_metrics["supplied"], plan_metrics["disabled"]
                ),
                prediction_ci=0.0,
                composition_ci=supplied_plan_composition_ci[0],
                minimum_gain=float(manifest["minimum_gain"]),
            )
            rows.append(
                {
                    "seed": seed,
                    "partition": partition,
                    "collision_episodes": len(cases["collision"]),
                    "plan_episodes": len(cases["plan"]),
                    "induced_prediction_success_rate": _mean(
                        collision_metrics["induced_prediction"]
                    ),
                    "supplied_prediction_success_rate": _mean(
                        collision_metrics["supplied_prediction"]
                    ),
                    "bounded_one_hop_prediction_success_rate": _mean(
                        collision_metrics["bounded_one_hop_prediction"]
                    ),
                    "induced_composition_success_rate": _mean(
                        collision_metrics["induced_composition"]
                    ),
                    "supplied_composition_success_rate": _mean(
                        collision_metrics["supplied_composition"]
                    ),
                    "bounded_one_hop_composition_success_rate": _mean(
                        collision_metrics["bounded_one_hop_composition"]
                    ),
                    "collision_prediction_delta": _delta(
                        collision_metrics["induced_prediction"],
                        collision_metrics["bounded_one_hop_prediction"],
                    ),
                    "collision_prediction_delta_95ci": list(
                        collision_prediction_ci
                    ),
                    "supplied_collision_prediction_delta_95ci": list(
                        supplied_collision_prediction_ci
                    ),
                    "collision_composition_delta": _delta(
                        collision_metrics["induced_composition"],
                        collision_metrics["bounded_one_hop_composition"],
                    ),
                    "collision_composition_delta_95ci": list(
                        collision_composition_ci
                    ),
                    "supplied_collision_composition_delta_95ci": list(
                        supplied_collision_composition_ci
                    ),
                    "induced_collision_mistyping_rate": collision_metrics[
                        "induced_mistyping_rate"
                    ],
                    "induced_plan_success_rate": _mean(plan_metrics["induced"]),
                    "supplied_plan_success_rate": _mean(plan_metrics["supplied"]),
                    "disabled_plan_success_rate": _mean(plan_metrics["disabled"]),
                    "plan_composition_delta": _delta(
                        plan_metrics["induced"], plan_metrics["disabled"]
                    ),
                    "plan_composition_delta_95ci": list(plan_composition_ci),
                    "supplied_plan_composition_delta_95ci": list(
                        supplied_plan_composition_ci
                    ),
                }
            )
        lifecycle_row.update(
            {
                "collision_after_final": _statuses(collision_candidates),
                "supplied_collision_after_final": _statuses(
                    supplied_collision_candidates
                ),
                "plan_after_final": _statuses(plan_candidates),
                "supplied_plan_after_final": _statuses(
                    supplied_plan_candidates
                ),
                "induced_state_bytes": _state_bytes(
                    induced_collision
                )
                + _state_bytes(induced_plans),
                "supplied_state_bytes": _state_bytes(
                    supplied_collision
                )
                + _state_bytes(supplied_plans),
            }
        )
        lifecycle.append(lifecycle_row)
    digest = hashlib.sha256(
        json.dumps(manifest, sort_keys=True).encode("utf-8")
    ).hexdigest()
    adopted = all(
        all(set(row[key]) == {"adopted"} for key in (
            "collision_after_final",
            "supplied_collision_after_final",
            "plan_after_final",
            "supplied_plan_after_final",
        ))
        and row["unresolved_beyond_budget_candidate_count"] == 0
        for row in lifecycle
    )
    return {
        "benchmark_version": manifest["benchmark_version"],
        "manifest_sha256": digest,
        "manifest": manifest,
        "leakage_audit": _audit(lifecycle),
        "rows": rows,
        "aggregate": _aggregate(rows, lifecycle),
        "lifecycle": lifecycle,
        "decision": "adopt_bounded_role_disambiguation" if adopted else "reject",
    }


def _collision_training_state(seed: int, *, supplied_roles: bool) -> RisaState:
    state = RisaState()
    events = []
    timestamp = 1
    for effect, source_relation, role in (
        ("warm", "uses_solar", "solar_powered_device"),
        ("cold", "uses_nuclear", "nuclear_powered_device"),
    ):
        for index in range(8):
            target = f"collision-{effect}-{seed}-{index}"
            events.append(
                Event(
                    id=f"collision-support:{seed}:{effect}:{index}",
                    timestamp=timestamp,
                    actor=f"collision-trainer-{index}",
                    action="inspect",
                    target=target,
                    target_roles=[role] if supplied_roles else [],
                    observed_effects=[effect],
                    episode_id=f"collision-support:{seed}:{effect}:{index}",
                    source=f"collision-source-{effect}-{index}",
                    entity_bindings={
                        "object": target,
                        "supply": f"supply-{seed}-{effect}-{index}",
                        "resource": f"resource-{seed}-{effect}-{index}",
                    },
                    entity_relations=[
                        {"source": "object", "relation": "powered_by", "target": "supply"},
                        {"source": "supply", "relation": source_relation, "target": "resource"},
                    ],
                    entity_relations_observed=True,
                )
            )
            timestamp += 1
    _train(state, events)
    return state


def _plan_training_state(seed: int, *, supplied_roles: bool) -> RisaState:
    state = RisaState()
    events = []
    timestamp = 1
    for index in range(4):
        actor = f"plan-controller-{seed}-{index}"
        target = f"plan-device-{seed}-{index}"
        episode = f"plan-support:{seed}:{index}"
        bindings = {
            "operator": actor,
            "machine": target,
            "supply": f"plan-grid-{seed}-{index}",
        }
        relations = [
            {"source": "operator", "relation": "controls", "target": "machine"},
            {"source": "machine", "relation": "powered_by", "target": "supply"},
        ]
        entity_roles = (
            {
                "operator": ["controller"],
                "machine": ["powered_device"],
                "supply": ["power_supply"],
            }
            if supplied_roles
            else {}
        )
        common = {
            "actor": actor,
            "target": target,
            "actor_roles": ["controller"] if supplied_roles else [],
            "target_roles": ["powered_device"] if supplied_roles else [],
            "episode_id": episode,
            "entity_bindings": bindings,
            "entity_role_bindings": entity_roles,
            "entity_relations": relations,
            "entity_relations_observed": True,
        }
        events.extend(
            [
                Event(
                    id=f"{episode}:prepare",
                    timestamp=timestamp,
                    action="prepare",
                    observed_effects=["ready"],
                    source=f"plan-source-{index}-a",
                    **common,
                ),
                Event(
                    id=f"{episode}:start",
                    timestamp=timestamp + 1,
                    action="start",
                    preconditions=["ready"],
                    observed_states_before=["ready"],
                    before_state_observed=True,
                    observed_effects=["running"],
                    source=f"plan-source-{index}-b",
                    **common,
                ),
            ]
        )
        timestamp += 2
    _train(state, events)
    return state


def _train(state: RisaState, events: list[Event]) -> None:
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


def _cases(seed: int, partition: str, count: int) -> dict[str, list[dict[str, Any]]]:
    collision = []
    plan = []
    collision_variants = (
        ("uses_solar", "solar_powered_device", "warm"),
        ("uses_nuclear", "nuclear_powered_device", "cold"),
        ("uses_wind", "wind_powered_device", None),
        (None, "unknown_device", None),
    )
    for index in range(count):
        relation, role, expected = collision_variants[index % 4]
        target = f"heldout-collision-{seed}-{partition}-{index}"
        bindings = {"item": target, "grid": f"heldout-grid-{index}"}
        relations = [
            {"source": "item", "relation": "powered_by", "target": "grid"}
        ]
        if relation is not None:
            bindings["resource"] = f"heldout-resource-{index}"
            relations.append(
                {"source": "grid", "relation": relation, "target": "resource"}
            )
        collision.append(
            {
                "id": f"{partition}:{seed}:collision:{index}",
                "target": target,
                "role": role,
                "expected": expected,
                "entity_bindings": bindings,
                "entity_relations": relations,
            }
        )
        valid = index % 2 == 0
        plan.append(
            {
                "id": f"{partition}:{seed}:plan:{index}",
                "valid": valid,
                "actor": f"heldout-controller-{index}",
                "target": f"heldout-device-{index}",
            }
        )
    random.Random(f"role-v2:{seed}:{partition}").shuffle(collision)
    random.Random(f"plan-v2:{seed}:{partition}").shuffle(plan)
    return {"collision": collision, "plan": plan}


def _collision_metrics(
    induced_state: RisaState,
    supplied_state: RisaState,
    induced_candidates: list[UnnamedConceptCandidate],
    supplied_candidates: list[UnnamedConceptCandidate],
    cases: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    induced = _adopted_state(induced_state, induced_candidates)
    supplied = _adopted_state(supplied_state, supplied_candidates)
    results = {
        key: []
        for key in (
            "induced_prediction",
            "supplied_prediction",
            "bounded_one_hop_prediction",
            "induced_composition",
            "supplied_composition",
            "bounded_one_hop_composition",
        )
    }
    false_predictions = negatives = 0
    for case in cases["collision"]:
        expected = case["expected"]
        outputs = {
            "induced_prediction": _collision_predict(induced, case, "induced"),
            "supplied_prediction": _collision_predict(supplied, case, "supplied"),
            "bounded_one_hop_prediction": _collision_predict(
                induced, case, "one_hop"
            ),
            "induced_composition": _collision_forecast(induced, case, "induced"),
            "supplied_composition": _collision_forecast(supplied, case, "supplied"),
            "bounded_one_hop_composition": _collision_forecast(
                induced, case, "one_hop"
            ),
        }
        for key, output in outputs.items():
            results[key].append(int(output == expected))
        if expected is None:
            negatives += 1
            false_predictions += int(outputs["induced_prediction"] is not None)
    results["induced_mistyping_rate"] = false_predictions / negatives
    return results


def _collision_predict(
    state: RisaState, case: dict[str, Any], method: str
) -> str | None:
    relations = list(case["entity_relations"])
    bindings = dict(case["entity_bindings"])
    if method == "one_hop":
        relations = relations[:1]
        bindings = {key: value for key, value in bindings.items() if key in {"item", "grid"}}
    result = predict_next_effect(
        state,
        PredictionQuery(
            actor="heldout-robot",
            action="inspect",
            target=str(case["target"]),
            target_roles=[str(case["role"])] if method == "supplied" else [],
            entity_bindings=bindings,
            entity_relations=relations,
        ),
    )
    return result.predicted_effects[0] if result.predicted_effects else None


def _collision_forecast(
    state: RisaState, case: dict[str, Any], method: str
) -> str | None:
    relations = list(case["entity_relations"])
    bindings = dict(case["entity_bindings"])
    if method == "one_hop":
        relations = relations[:1]
        bindings = {key: value for key, value in bindings.items() if key in {"item", "grid"}}
    outputs = forecast_next_effects(
        state,
        "inspect",
        target_roles=[str(case["role"])] if method == "supplied" else [],
        target=str(case["target"]),
        entity_bindings=bindings,
        entity_relations=relations,
    )
    return outputs[0].added_states[0] if outputs else None


def _plan_metrics(
    induced_state: RisaState,
    supplied_state: RisaState,
    induced_candidates: list[UnnamedConceptCandidate],
    supplied_candidates: list[UnnamedConceptCandidate],
    cases: dict[str, list[dict[str, Any]]],
) -> dict[str, list[int]]:
    induced = _adopted_state(induced_state, induced_candidates)
    supplied = _adopted_state(supplied_state, supplied_candidates)
    results = {"induced": [], "supplied": [], "disabled": []}
    for case in cases["plan"]:
        for method, state in (
            ("induced", induced),
            ("supplied", supplied),
            ("disabled", induced),
        ):
            success = _plan_success(state, case, method)
            results[method].append(int(success == bool(case["valid"])))
    return results


def _plan_success(state: RisaState, case: dict[str, Any], method: str) -> bool:
    valid = bool(case["valid"])
    actor_relation = "controls" if valid else "observes"
    actor = str(case["actor"])
    target = str(case["target"])
    bindings = {"operator": actor, "machine": target, "supply": f"{target}-grid"}
    relations = [
        {"source": "operator", "relation": actor_relation, "target": "machine"},
        {"source": "machine", "relation": "powered_by", "target": "supply"},
    ]
    correct_roles = valid and method == "supplied"
    result = compose_to_effect(
        state,
        "prepare",
        "running",
        actor=actor,
        target=target,
        actor_roles=["controller" if correct_roles else "observer"]
        if method == "supplied"
        else [],
        target_roles=["powered_device" if correct_roles else "observed_device"]
        if method == "supplied"
        else [],
        entity_bindings=bindings,
        entity_role_bindings=(
            {
                "operator": ["controller" if valid else "observer"],
                "machine": ["powered_device" if valid else "observed_device"],
                "supply": ["power_supply"],
            }
            if method == "supplied"
            else {}
        ),
        entity_relations=relations,
        enable_role_induction=method != "disabled",
        max_steps=2,
    )
    return bool(result.primitive_ids)


def _unresolved_candidate_count(seed: int) -> int:
    state = RisaState()
    events = []
    for index, (effect, third_relation) in enumerate(
        (("warm", "solar_class"), ("warm", "solar_class"),
         ("cold", "nuclear_class"), ("cold", "nuclear_class")),
        1,
    ):
        target = f"unresolved-{seed}-{index}"
        events.append(
            Event(
                id=f"unresolved-support:{seed}:{index}",
                timestamp=index,
                actor=f"unresolved-actor-{index}",
                action="inspect",
                target=target,
                observed_effects=[effect],
                episode_id=f"unresolved-support:{seed}:{index}",
                source=f"unresolved-source-{index}",
                entity_bindings={
                    "object": target,
                    "supply": f"unresolved-supply-{index}",
                    "fuel": f"unresolved-fuel-{index}",
                    "class": f"unresolved-class-{index}",
                },
                entity_relations=[
                    {"source": "object", "relation": "powered_by", "target": "supply"},
                    {"source": "supply", "relation": "uses_fuel", "target": "fuel"},
                    {"source": "fuel", "relation": third_relation, "target": "class"},
                ],
                entity_relations_observed=True,
            )
        )
    _train(state, events)
    return len(_candidates(state, "single_transition"))


def _candidates(state: RisaState, kind: str) -> list[UnnamedConceptCandidate]:
    return sorted(
        (
            candidate
            for candidate in state.unnamed_concept_candidates.values()
            if candidate.structural_schema.get("kind", "single_transition") == kind
            and candidate.derivation_generation == 0
        ),
        key=lambda candidate: candidate.id,
    )


def _plan_candidates(state: RisaState) -> list[UnnamedConceptCandidate]:
    return sorted(
        (
            candidate
            for candidate in state.unnamed_concept_candidates.values()
            if candidate.structural_schema.get("kind")
            in {"temporal_sequence", "relational_sequence"}
            and candidate.derivation_generation == 0
        ),
        key=lambda candidate: candidate.id,
    )


def _adopted_state(
    source: RisaState, candidates: list[UnnamedConceptCandidate]
) -> RisaState:
    state = RisaState.from_dict(source.to_dict())
    for candidate in candidates:
        state.unnamed_concept_candidates[candidate.id].lifecycle_status = "adopted"
    state.action_target_role_context_effect_counts.clear()
    state.structural_primitives.clear()
    rebuild_candidate_inference_index(state)
    return state


def _evaluate_candidates(
    state: RisaState,
    candidates: list[UnnamedConceptCandidate],
    partition: str,
    ids: list[str],
    *,
    prediction_delta: float,
    composition_delta: float,
    prediction_ci: float,
    composition_ci: float,
    minimum_gain: float,
) -> None:
    for candidate in candidates:
        evaluate_unnamed_candidate(
            state,
            candidate.id,
            partition=partition,
            evaluation_event_ids=ids,
            prediction_delta=prediction_delta,
            composition_delta=composition_delta,
            prediction_delta_ci_lower=prediction_ci,
            composition_delta_ci_lower=composition_ci,
            false_generalization_delta=0.0,
            minimum_gain=minimum_gain,
        )


def _bootstrap(
    left: list[int], right: list[int], samples: int, seed: int
) -> tuple[float, float]:
    rng = random.Random(seed)
    deltas = []
    for _ in range(samples):
        indexes = [rng.randrange(len(left)) for _ in left]
        deltas.append(sum(left[index] - right[index] for index in indexes) / len(indexes))
    deltas.sort()
    return (
        deltas[int(samples * 0.025)],
        deltas[min(samples - 1, int(samples * 0.975))],
    )


def _delta(left: list[int], right: list[int]) -> float:
    return _mean(left) - _mean(right)


def _mean(values: list[int]) -> float:
    return sum(values) / len(values)


def _statuses(candidates: list[UnnamedConceptCandidate]) -> list[str]:
    return sorted(candidate.lifecycle_status for candidate in candidates)


def _case_ids(cases: dict[str, list[dict[str, Any]]]) -> list[str]:
    return sorted(
        str(case["id"])
        for partition_cases in cases.values()
        for case in partition_cases
    )


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
    keys = (
        "induced_prediction_success_rate",
        "supplied_prediction_success_rate",
        "bounded_one_hop_prediction_success_rate",
        "induced_composition_success_rate",
        "supplied_composition_success_rate",
        "bounded_one_hop_composition_success_rate",
        "collision_prediction_delta",
        "collision_composition_delta",
        "induced_collision_mistyping_rate",
        "induced_plan_success_rate",
        "supplied_plan_success_rate",
        "disabled_plan_success_rate",
        "plan_composition_delta",
    )
    aggregate = {
        key: sum(float(row[key]) for row in final) / len(final) for key in keys
    }
    aggregate["mean_induced_state_bytes"] = sum(
        row["induced_state_bytes"] for row in lifecycle
    ) / len(lifecycle)
    aggregate["mean_supplied_state_bytes"] = sum(
        row["supplied_state_bytes"] for row in lifecycle
    ) / len(lifecycle)
    aggregate["mean_collision_candidate_count"] = sum(
        row["collision_candidate_count"] for row in lifecycle
    ) / len(lifecycle)
    aggregate["mean_plan_candidate_count"] = sum(
        row["plan_candidate_count"] for row in lifecycle
    ) / len(lifecycle)
    return aggregate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", default="experiments/g2_role_disambiguation_manifest.json"
    )
    parser.add_argument(
        "--output", default="docs/g2-role-disambiguation-results.json"
    )
    args = parser.parse_args()
    result = run_role_disambiguation_evaluation(load_manifest(args.manifest))
    Path(args.output).write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["aggregate"], indent=2))


if __name__ == "__main__":
    main()
