"""Development A→B→A pilot with probe-validated A1 candidate adoption."""

from __future__ import annotations

import argparse
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from experiments.g3_drift_preflight import ARMS, _events, _probes, mechanism_opportunity_audit
from experiments.g3_lifecycle_readiness import _panel
from risa.core.state import RisaState
from risa.engine.candidate_discovery import (
    rebuild_candidate_inference_index,
    select_derived_candidates_for_final,
)
from risa.engine.candidate_lifecycle import capture_context_conditions
from risa.engine.runtime import TrainingOptions, train_events
from risa.evaluation.candidate_adoption import evaluate_candidate_on_probes
from risa.evaluation.drift_metrics import snapshot_mechanisms
from risa.evaluation.drift_runner import ValidationStepResult, run_aba


def _adopt_warm_candidates(
    state: RisaState, seed: int, *, dormancy: bool, count: int,
    bootstrap_samples: int, phase: str = "A1",
) -> int:
    warm = next(
        candidate for candidate in state.unnamed_concept_candidates.values()
        if candidate.derivation_generation == 0
        and candidate.structural_schema.get("effects") == ["warm"]
    )
    parents = sorted(
        (candidate for candidate in state.unnamed_concept_candidates.values()
         if candidate.derivation_type == "specialized"
         and candidate.parent_candidate_ids == [warm.id]),
        key=lambda candidate: candidate.id,
    )
    if len(parents) != 2:
        raise ValueError(f"{phase} must have two warm specialization candidates")
    merge = next(
        (candidate for candidate in state.unnamed_concept_candidates.values()
         if candidate.derivation_type == "merged"
         and set(candidate.parent_candidate_ids) == {parent.id for parent in parents}),
        None,
    )
    label_count = 0
    for candidate in parents + ([merge] if merge is not None else []):
        development = _panel(seed, f"{phase}:{candidate.id}:development", count)
        final = _panel(seed, f"{phase}:{candidate.id}:final", count)
        dev = evaluate_candidate_on_probes(
            state, candidate.id, development, partition="development",
            bootstrap_samples=bootstrap_samples, seed=seed,
        )
        label_count += len(development)
        if dev["status"] != "provisional":
            raise ValueError(f"{phase} development rejected {candidate.id}")
        select_derived_candidates_for_final(state, [candidate.id])
        approved = evaluate_candidate_on_probes(
            state, candidate.id, final, partition="final",
            development_probes=development,
            bootstrap_samples=bootstrap_samples, seed=seed + 1,
            enable_ancestor_dormancy=dormancy,
        )
        label_count += len(final)
        if approved["status"] != "adopted":
            raise ValueError(f"{phase} final rejected {candidate.id}")
    return label_count


def _online_validate_warm_candidates(
    state: RisaState, seed: int, *, dormancy: bool, count: int,
    bootstrap_samples: int, phase: str,
) -> ValidationStepResult:
    """Attempt validation without treating rejection or missing proposals as errors."""
    warm = next(
        (candidate for candidate in state.unnamed_concept_candidates.values()
         if candidate.derivation_generation == 0
         and candidate.structural_schema.get("effects") == ["warm"]),
        None,
    )
    if warm is None:
        return ValidationStepResult()
    parents = sorted(
        (candidate for candidate in state.unnamed_concept_candidates.values()
         if candidate.derivation_type == "specialized"
         and candidate.parent_candidate_ids == [warm.id]),
        key=lambda candidate: candidate.id,
    )
    if len(parents) != 2:
        return ValidationStepResult()
    merge = next(
        (candidate for candidate in state.unnamed_concept_candidates.values()
         if candidate.derivation_type == "merged"
         and set(candidate.parent_candidate_ids) == {parent.id for parent in parents}),
        None,
    )
    if merge is None:
        return ValidationStepResult()
    used: list[str] = []
    decisions = 0
    for candidate in parents + [merge]:
        if candidate.lifecycle_status == "adopted" and not candidate.dormant:
            continue
        # A new independent validation cycle keeps the historical ID union for
        # provenance but replaces stale partition panels from the A1 cycle.
        candidate.development_evaluation_event_ids = []
        candidate.final_evaluation_event_ids = []
        candidate.selected_for_final = False
        candidate.lifecycle_status = "proposed"
        rebuild_candidate_inference_index(state)
        development = _panel(seed, f"{phase}:{candidate.id}:development", count)
        final = _panel(seed, f"{phase}:{candidate.id}:final", count)
        dev = evaluate_candidate_on_probes(
            state, candidate.id, development, partition="development",
            bootstrap_samples=bootstrap_samples, seed=seed,
        )
        used.extend(probe.id for probe in development)
        decisions += 1
        if dev["status"] != "provisional":
            continue
        select_derived_candidates_for_final(state, [candidate.id])
        approved = evaluate_candidate_on_probes(
            state, candidate.id, final, partition="final",
            development_probes=development,
            bootstrap_samples=bootstrap_samples, seed=seed + 1,
            enable_ancestor_dormancy=dormancy,
        )
        used.extend(probe.id for probe in final)
        decisions += 1
        if approved["status"] == "adopted" and candidate.dormant:
            candidate.dormant = False
            rebuild_candidate_inference_index(state)
    return ValidationStepResult(tuple(used), decisions)


def run_candidate_primed_preflight(manifest: dict) -> dict:
    if set(manifest["arms"]) != set(ARMS):
        raise ValueError("all seven arms are required")
    count = int(manifest["adoption_probes_per_partition"])
    if count < 4 or count % 4:
        raise ValueError("adoption probe count must be a positive multiple of four")
    rows = []
    for seed in manifest["seeds"]:
        a1 = _events(seed, "A1", 6)
        reference = train_events(
            RisaState(), a1,
            TrainingOptions(enable_replay=False, enable_metabolism=False),
        )
        frozen = capture_context_conditions(reference)
        b = _events(seed, "B", int(manifest["phase_observations"]))
        a2 = _events(seed, "A2", int(manifest["phase_observations"]))
        a_probes = _probes(seed, "A", int(manifest["probes_per_phase"]))
        b_probes = _probes(seed, "B", int(manifest["probes_per_phase"]))
        for arm in manifest["arms"]:
            split, merge, dormancy = ARMS[arm]
            options = TrainingOptions(
                enable_metabolism=False, enable_replay=True,
                enable_context_split=split,
                enable_candidate_specialization=split,
                enable_candidate_merge=merge,
                frozen_context_conditions=frozen if not split else None,
                replay_max_events=int(manifest["replay_max_events"]),
            )
            state = train_events(
                RisaState(), a1,
                TrainingOptions(
                    enable_metabolism=False, enable_replay=False,
                    enable_context_split=split,
                    enable_candidate_specialization=split,
                    enable_candidate_merge=merge,
                    frozen_context_conditions=frozen if not split else None,
                ),
            )
            labels = _adopt_warm_candidates(
                state, seed, dormancy=dormancy, count=count,
                bootstrap_samples=int(manifest["bootstrap_samples"]),
            )
            a1_mechanisms = snapshot_mechanisms(state)
            online_schedule = tuple(manifest.get("online_validation_a2_events", []))
            online_cap = int(manifest.get("online_validation_label_budget", 0))
            if online_cap < 0 or any(
                not isinstance(index, int) or index < 1
                or index > len(a2) for index in online_schedule
            ) or len(set(online_schedule)) != len(online_schedule):
                raise ValueError("invalid online validation schedule or label budget")

            def validate_online(current, index, event, remaining):
                if not event.id.startswith("A2:") or index not in online_schedule:
                    return ValidationStepResult()
                if remaining is not None and remaining < 6 * count:
                    return ValidationStepResult()
                return _online_validate_warm_candidates(
                    current, seed, dormancy=dormancy, count=count,
                    bootstrap_samples=int(manifest["bootstrap_samples"]),
                    phase=f"A2-online-{index}",
                )

            outcome = run_aba(
                state, b, a2, a_probes, b_probes, options,
                replay_interval=int(manifest["replay_interval"]),
                recovery_window=int(manifest["recovery_window"]),
                validation_step=validate_online if online_schedule else None,
                validation_label_budget=online_cap if online_schedule else None,
            )
            final = snapshot_mechanisms(state)
            postphase_labels = 0
            postphase_adopted_merges = 0
            if final.merged_proposals and not online_schedule:
                revalidated = copy.deepcopy(state)
                postphase_labels = _adopt_warm_candidates(
                    revalidated, seed, dormancy=dormancy, count=count,
                    bootstrap_samples=int(manifest["bootstrap_samples"]),
                    phase="A2-postphase",
                )
                postphase_adopted_merges = len(
                    snapshot_mechanisms(revalidated).adopted_merges
                )
            extra_to_proposal = None
            if merge:
                extra_to_proposal = _extra_events_to_merge_proposal(
                    state, seed, options,
                    int(manifest.get("extra_a2_observations", 0)),
                )
            rows.append({
                "seed": seed, "arm": arm,
                "split_enabled": split, "merge_enabled": merge,
                "dormancy_enabled": dormancy,
                "a1_adopted_merges": len(a1_mechanisms.adopted_merges),
                "a1_merged_proposals": len(a1_mechanisms.merged_proposals),
                "a1_dormant_candidates": len(a1_mechanisms.dormant_candidates),
                "a1_supervised_adoption_labels": labels,
                "online_validation_labels": outcome["validation_labels_total"],
                "online_validation_decisions": (
                    outcome["B"]["validation_adoption_decisions"]
                    + outcome["A2"]["validation_adoption_decisions"]
                ),
                "A2_online_validation_trace": outcome["A2"]["validation_trace"],
                "final_adopted_merges": len(final.adopted_merges),
                "final_merged_proposals": len(final.merged_proposals),
                "final_dormant_candidates": len(final.dormant_candidates),
                "final_executed_context_splits": len(final.executed_context_splits),
                "A2_postphase_revalidation_labels": postphase_labels,
                "A2_postphase_revalidated_merges": postphase_adopted_merges,
                "A2_extra_events_to_merge_proposal": extra_to_proposal,
                "A2_extra_proposal_censored": merge and extra_to_proposal is None,
                "a1_accuracy": outcome["a1_accuracy"],
                "retention_after_return": outcome["retention_after_return"],
                "B_recovery_events": outcome["B"]["recovery_events"],
                "A2_recovery_events": outcome["A2"]["recovery_events"],
                "B_adaptation_touch_ratio": outcome["B"]["adaptation"]["adaptation_touch_ratio"],
                "A2_adaptation_touch_ratio": outcome["A2"]["adaptation"]["adaptation_touch_ratio"],
                "B_replay_cost_per_recovery": outcome["B"]["replay_cost_per_recovery"],
                "A2_replay_cost_per_recovery": outcome["A2"]["replay_cost_per_recovery"],
                "B_mechanism_trace": outcome["B"]["mechanism_trace"],
                "A2_mechanism_trace": outcome["A2"]["mechanism_trace"],
            })
    opportunity = mechanism_opportunity_audit(rows)
    return {
        "benchmark_version": manifest["benchmark_version"],
        "manifest_sha256": hashlib.sha256(
            json.dumps(manifest, sort_keys=True).encode()
        ).hexdigest(),
        "status": "development_preflight_only",
        "mechanism_opportunity_gate": opportunity["status"],
        "mechanism_opportunity_audit": opportunity,
        "rows": rows,
    }


def _extra_events_to_merge_proposal(
    state: RisaState, seed: int, options: TrainingOptions, budget: int
) -> int | None:
    """Development diagnostic: first proposal after A2, without extra Replay."""
    probe_state = copy.deepcopy(state)
    if snapshot_mechanisms(probe_state).merged_proposals:
        return 0
    if budget < 0 or budget % 3:
        raise ValueError("extra A2 observation budget must be a nonnegative multiple of three")
    extra = [
        replace(
            event, id=f"A2-extra:{seed}:{index}", timestamp=212 + index,
            actor=f"extra-actor:{seed}:{index}",
            target=f"extra-device:{seed}:{index}",
            episode_id=f"extra-episode:{seed}:{index}",
            source=f"extra-sensor:{seed}:{index}",
        )
        for index, event in enumerate(_events(seed, "A2", budget))
    ]
    update_options = replace(options, enable_replay=False)
    for index, event in enumerate(extra, 1):
        train_events(probe_state, [event], update_options)
        if snapshot_mechanisms(probe_state).merged_proposals:
            return index
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="experiments/g3_drift_candidate_primed_manifest.json")
    parser.add_argument("--output", default="docs/g3-drift-candidate-primed-results.json")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    result = run_candidate_primed_preflight(manifest)
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"rows": len(result["rows"]),
                      "opportunity_gate": result["mechanism_opportunity_gate"]}))


if __name__ == "__main__":
    main()
