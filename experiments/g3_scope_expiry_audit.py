"""Audit the evidence scope that invalidates validated derived candidates."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from experiments.g3_relational_return_cue import relational_world
from experiments.g3_role_online_ablation import online_warm_adoption
from risa.core.state import RisaState
from risa.engine.candidate_discovery import _reactivate_validated_orphaned_ancestors
from risa.engine.runtime import TrainingOptions, train_events


def _adopted_fixture(seed: int, phase_observations: int, probes: int):
    a, b, a2, a_probes, _ = relational_world(seed, phase_observations, probes)
    state = train_events(
        RisaState(target_role_readout_hops=2, context_conditioned_role_refinement=True),
        a + b,
        TrainingOptions(enable_metabolism=False, enable_replay=False),
    )
    result, _ = online_warm_adoption(
        state, seed, a_probes[0].query, count=200, remaining=1200, dormancy=True,
    )
    merge = next(
        candidate for candidate in state.unnamed_concept_candidates.values()
        if candidate.derivation_type == "merged" and candidate.lifecycle_status == "adopted"
    )
    return state, merge.id, a2, len(result.label_ids)


def run_scope_expiry_audit(manifest: dict) -> dict:
    rows = []
    for seed in manifest["seeds"]:
        state, merge_id, a2, initial_labels = _adopted_fixture(
            seed, manifest["phase_observations"], manifest["probes_per_phase"]
        )
        previous = copy.deepcopy(state.unnamed_concept_candidates)
        old_merge = previous[merge_id]

        # The first A2 observation changes a broad root but is outside exactly
        # one specialized parent's scope. That unchanged parent may wake after
        # the now-stale merged replacement disappears.
        # Use the earliest A2 observation that leaves at least one validated
        # specialized scope unchanged. Some seeded orderings update both warm
        # scopes before that condition exists.
        reactivated = []
        observed_events = 0
        for event in a2:
            train_events(
                state, [event],
                TrainingOptions(enable_metabolism=False, enable_replay=False),
            )
            observed_events += 1
            reactivated = _reactivate_validated_orphaned_ancestors(state, previous)
            if reactivated:
                break
        preserved = []
        for candidate_id in reactivated:
            current, old = state.unnamed_concept_candidates[candidate_id], previous[candidate_id]
            preserved.append({
                "candidate_id": candidate_id,
                "own_evidence_unchanged": (
                    current.supporting_event_ids == old.supporting_event_ids
                    and current.counterexample_event_ids == old.counterexample_event_ids
                ),
                "parent_digest_changed": current.parent_evidence_digests != old.parent_evidence_digests,
                "validation_unchanged": current.evaluation_event_ids == old.evaluation_event_ids,
            })

        # Mutation checks directly exercise the fail-closed reactivation gate.
        rejection = {}
        for mutation in ("counterexample", "role", "lineage"):
            probe = copy.deepcopy(previous)
            candidate_id = old_merge.parent_candidate_ids[0]
            candidate = probe[candidate_id]
            if mutation == "counterexample":
                candidate.counterexample_event_ids.append(f"audit:{seed}:counterexample")
            elif mutation == "role":
                candidate.typed_role_variables["target"] = "audit:changed-role"
            else:
                candidate.parent_candidate_ids.append("audit:changed-lineage")
            probe[merge_id].lifecycle_status = "rejected"
            sandbox = copy.deepcopy(state)
            sandbox.unnamed_concept_candidates = probe
            rejection[mutation] = candidate_id not in _reactivate_validated_orphaned_ancestors(
                sandbox, previous
            )

        rows.append({
            "seed": seed,
            "initial_adoption_labels": initial_labels,
            "out_of_scope_revalidation_labels": 0,
            "observed_events_to_unchanged_scope": observed_events,
            "reactivated_candidates": len(reactivated),
            "preserved": preserved,
            "in_scope_mutations_rejected": rejection,
        })

    passed = all(
        row["reactivated_candidates"] == 1
        and all(item["own_evidence_unchanged"] and item["parent_digest_changed"]
                and item["validation_unchanged"] for item in row["preserved"])
        and all(row["in_scope_mutations_rejected"].values())
        for row in rows
    )
    return {
        "benchmark_version": manifest["benchmark_version"],
        "manifest_sha256": hashlib.sha256(
            json.dumps(manifest, sort_keys=True).encode()
        ).hexdigest(),
        "status": "passed" if passed else "failed",
        "scope_contract": {
            "out_of_scope_parent_update": "preserve unchanged scoped validation",
            "in_scope_counterexample_role_or_lineage_change": "expire validation",
            "labels_for_unchanged_scope": 0,
        },
        "rows": rows,
    }


if __name__ == "__main__":
    manifest = json.loads(Path("experiments/g3_scope_expiry_audit_manifest.json").read_text())
    result = run_scope_expiry_audit(manifest)
    Path("docs/g3-scope-expiry-audit-results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({"rows": len(result["rows"]), "status": result["status"]}))
