from __future__ import annotations

import copy
import pytest

from experiments.g3_drift_preflight import ARMS, _events, mechanism_opportunity_audit, run_preflight
from experiments.g3_lifecycle_readiness import run_lifecycle_readiness
from experiments.g3_drift_candidate_primed import run_candidate_primed_preflight
from experiments.g3_split_drift_opportunity import run_split_opportunity
from risa.core.models import (
    Event, Node, ReplaySummary, StructuralAdaptationCandidate,
    UnnamedConceptCandidate,
)
from risa.core.models import PredictionQuery
from risa.core.state import RisaState
from risa.engine.adaptation import execute_safe_adaptations
from risa.engine.candidate_discovery import (
    evaluate_derived_candidate,
    matching_adopted_candidates,
    rebuild_candidate_inference_index,
    select_derived_candidates_for_final,
)
from risa.engine.candidate_lifecycle import capture_context_conditions
from risa.engine.runtime import TrainingOptions, train_events
from risa.evaluation.candidate_extension import CandidateExtensionValidator, ExtensionProbe
from risa.evaluation.candidate_adoption import ApplicabilityProbe, evaluate_candidate_on_probes
from risa.evaluation.drift_metrics import (
    adaptation_touch_counts,
    mechanism_delta,
    recovery_events,
    replay_cost,
    snapshot_mechanisms,
    snapshot_structures,
)
from risa.evaluation.drift_runner import (
    DriftProbe, ValidationStepResult, run_aba, run_drift_phase,
)


def test_touch_ratio_excludes_access_counters_and_counts_removal() -> None:
    state = RisaState()
    state.graph.add_or_update_node(Node("n1", "entity", "first"))
    state.graph.add_or_update_node(Node("n2", "entity", "second"))
    before = snapshot_structures(state)
    state.graph.nodes_by_id["n1"].usage_count += 1
    state.graph.nodes_by_id["n1"].last_activated_at = 5
    state.graph.nodes_by_id.pop("n2")
    after = snapshot_structures(state)
    result = adaptation_touch_counts(before, after)
    assert result["pre_boundary"] == 2
    assert result["touched"] == 1
    assert result["adaptation_touch_ratio"] == 0.5
    assert result["removed"] == 1


def test_event_records_do_not_dilute_knowledge_touch_ratio() -> None:
    state = train_events(
        RisaState(),
        [Event("record:1", 1, "actor", "move", observed_effects=["arrived"])],
        TrainingOptions(enable_replay=False),
    )
    snapshot = snapshot_structures(state)
    assert "event:record:1" not in snapshot.fingerprints["nodes"]
    assert all("event:record:1" not in key for key in snapshot.fingerprints["edges"])


def test_recovery_is_censored_and_uses_observed_event_counts() -> None:
    samples = [(0, 0.2), (2, 0.8), (4, 0.96), (6, 1.0)]
    assert recovery_events(samples, 1.0, window=2) == 6
    assert recovery_events(samples[:3], 1.0, window=2) is None
    assert recovery_events(samples, 0.0, window=2) is None


def test_phase_runner_keeps_probes_out_of_learning_and_bounds_replay_cost() -> None:
    state = train_events(
        RisaState(),
        [Event("a1:1", 1, "actor", "move", observed_effects=["arrived"])],
        TrainingOptions(enable_replay=False),
    )
    probe = DriftProbe("heldout:1", PredictionQuery("actor", "move"), ("arrived",))
    result = run_drift_phase(
        state,
        [Event("a2:1", 2, "actor", "move", observed_effects=["arrived"])],
        [probe], TrainingOptions(replay_max_events=1),
        reference_accuracy=1.0, replay_interval=1, recovery_window=1,
    )
    assert result["entry_accuracy"] == 1.0
    assert result["recovery_events"] == 0
    assert result["replay"]["calls"] == 1
    assert result["replay_cost_per_recovery"]["calls"] == 0
    assert "heldout:1" not in state.events_by_id


def test_aba_runner_reports_pre_relearning_retention() -> None:
    state = train_events(
        RisaState(),
        [Event("aba:a1", 1, "actor", "tune", observed_effects=["stable"])],
        TrainingOptions(enable_replay=False),
    )
    result = run_aba(
        state,
        [Event("aba:b", 2, "actor", "tune", observed_effects=["unstable"])],
        [Event("aba:a2", 3, "actor", "tune", observed_effects=["stable"])],
        [DriftProbe("probe:a", PredictionQuery("actor", "tune"), ("stable",))],
        [DriftProbe("probe:b", PredictionQuery("actor", "tune"), ("unstable",))],
        TrainingOptions(enable_replay=False), recovery_window=1,
    )
    assert result["a1_accuracy"] == 1.0
    assert result["retention_after_return"] == result["a2_entry_accuracy"]
    assert "probe:a" not in state.events_by_id
    assert "probe:b" not in state.events_by_id


def test_aba_validation_counts_labels_under_shared_budget() -> None:
    state = RisaState()
    result = run_aba(
        state,
        [Event("b:1", 1, "actor", "move", observed_effects=["b"])],
        [Event("a:2", 2, "actor", "move", observed_effects=["a"])],
        [DriftProbe("probe:a", PredictionQuery("actor", "move"), ("a",))],
        [DriftProbe("probe:b", PredictionQuery("actor", "move"), ("b",))],
        TrainingOptions(enable_replay=False), recovery_window=1,
        validation_step=lambda state, index, event, remaining: ValidationStepResult(
            (f"label:{event.id}",), 1
        ),
        validation_label_budget=2,
    )
    assert result["validation_labels_total"] == 2
    assert result["B"]["validation_labels_total"] == 1
    assert result["A2"]["validation_labels_total"] == 1
    assert result["B"]["validation_adoption_decisions"] == 1
    assert result["A2"]["validation_trace"][0]["labels_consumed"] == 1


def test_aba_validation_rejects_budget_overrun_and_reused_label() -> None:
    args = (
        [Event("b:1", 1, "actor", "move", observed_effects=["b"])],
        [Event("a:2", 2, "actor", "move", observed_effects=["a"])],
        [DriftProbe("probe:a", PredictionQuery("actor", "move"), ("a",))],
        [DriftProbe("probe:b", PredictionQuery("actor", "move"), ("b",))],
        TrainingOptions(enable_replay=False),
    )
    distinct = lambda state, index, event, remaining: ValidationStepResult(
        (f"label:{event.id}",)
    )
    with pytest.raises(ValueError, match="budget exceeded"):
        run_aba(RisaState(), *args, validation_step=distinct, validation_label_budget=1)
    reused = lambda state, index, event, remaining: ValidationStepResult(("label:1",))
    with pytest.raises(ValueError, match="unique across the phase"):
        run_aba(RisaState(), *args, validation_step=reused, validation_label_budget=2)


def test_aba_validation_rejects_either_scoring_panel_as_evidence() -> None:
    def leak(state, index, event, remaining):
        state.events_by_id["probe:a"] = event
        return ValidationStepResult()

    with pytest.raises(ValueError, match="scoring probes entered learned Events"):
        run_aba(
            RisaState(),
            [Event("b:1", 1, "actor", "move", observed_effects=["b"])],
            [],
            [DriftProbe("probe:a", PredictionQuery("actor", "move"), ("a",))],
            [DriftProbe("probe:b", PredictionQuery("actor", "move"), ("b",))],
            TrainingOptions(enable_replay=False), validation_step=leak,
        )


def test_phase_rejects_scoring_probe_in_candidate_evaluation() -> None:
    def leak(state, index, event, remaining):
        state.unnamed_concept_candidates["leak"] = UnnamedConceptCandidate(
            "leak", evaluation_event_ids=["probe:heldout"]
        )
        return ValidationStepResult()

    with pytest.raises(ValueError, match="scoring probes entered candidate validation"):
        run_drift_phase(
            RisaState(),
            [Event("observe:1", 1, "actor", "move", observed_effects=["a"])],
            [DriftProbe("probe:heldout", PredictionQuery("actor", "move"), ("a",))],
            TrainingOptions(enable_replay=False), reference_accuracy=1.0,
            validation_step=leak,
        )


def test_preflight_rejects_fixture_without_active_mechanism_opportunities() -> None:
    result = run_preflight({
        "benchmark_version": "test-g3.2-preflight",
        "seeds": [11],
        "phase_observations": 6,
        "probes_per_phase": 6,
        "replay_interval": 2,
        "replay_max_events": 4,
        "recovery_window": 2,
        "arms": ["full", "split_only", "merge_only", "no_split",
                 "no_merge", "no_dormancy", "none"],
    })
    assert len(result["rows"]) == 7
    assert result["mechanism_opportunity_gate"] == "fail"
    assert all(row["final_adopted_merges"] == 0 for row in result["rows"])
    assert "split:full" in result["mechanism_opportunity_audit"]["missing_opportunities"]


def test_opportunity_gate_requires_executed_split_and_adopted_merge() -> None:
    rows = [{
        "arm": arm,
        "seed": 11,
        "final_executed_context_splits": int(split),
        "final_adopted_merges": int(merge),
        "final_dormant_candidates": int(dormancy),
    } for arm, (split, merge, dormancy) in {
        "full": (True, True, True),
        "split_only": (True, False, False),
        "merge_only": (False, True, False),
        "no_split": (False, True, True),
        "no_merge": (True, False, True),
        "no_dormancy": (True, True, False),
        "none": (False, False, False),
    }.items()]
    assert mechanism_opportunity_audit(rows)["status"] == "pass"
    rows[0]["final_executed_context_splits"] = 0
    audit = mechanism_opportunity_audit(rows)
    assert audit["status"] == "fail"
    assert audit["missing_opportunities"] == ["split:full"]
    rows[0]["final_executed_context_splits"] = 1
    rows[-1]["final_adopted_merges"] = 1
    audit = mechanism_opportunity_audit(rows)
    assert audit["status"] == "fail"
    assert audit["unintended_executions"] == ["merge:none:11"]


def test_probe_backed_lifecycle_exposes_unadoptable_broad_ancestor() -> None:
    state = train_events(
        RisaState(), _events(11, "A1", 6),
        TrainingOptions(enable_replay=False, enable_metabolism=False),
    )
    broad = next(candidate for candidate in state.unnamed_concept_candidates.values()
                 if candidate.derivation_generation == 0
                 and candidate.structural_schema.get("effects") == ["warm"])
    merged = next(candidate for candidate in state.unnamed_concept_candidates.values()
                  if candidate.derivation_type == "merged")

    def panel(prefix: str) -> list[ApplicabilityProbe]:
        variants = (("indoor", True), ("sheltered", True),
                    ("outdoor", False), ("exposed", False))
        return [ApplicabilityProbe(
            f"{prefix}:{index}", f"{prefix}:episode:{index}",
            f"{prefix}:source:{index % 2}", (variants[index % 4][0],),
            variants[index % 4][1],
        ) for index in range(200)]

    broad_result = evaluate_candidate_on_probes(
        state, broad.id, panel("broad-development"),
        partition="development", bootstrap_samples=200,
    )
    assert broad_result["status"] == "rejected"
    assert broad_result["false_generalization_delta"] == 1.0

    development_panel = panel("merge-development")
    development = evaluate_candidate_on_probes(
        state, merged.id, development_panel,
        partition="development", bootstrap_samples=200,
    )
    assert development["status"] == "provisional"
    assert development["parent_ci_lower"] > 0
    select_derived_candidates_for_final(state, [merged.id])
    with pytest.raises(ValueError, match="disjoint from development"):
        evaluate_candidate_on_probes(
            state, merged.id, development_panel,
            partition="final", development_probes=development_panel,
            bootstrap_samples=200,
        )
    final = evaluate_candidate_on_probes(
        state, merged.id, panel("merge-final"),
        partition="final", development_probes=development_panel,
        bootstrap_samples=200,
    )
    assert final["status"] == "adopted"
    assert final["supervised_labels"] == 200
    assert not broad.dormant

    leaked = panel("leaked")
    leaked[0] = ApplicabilityProbe(
        leaked[0].id, leaked[0].episode_id,
        state.events_by_id[broad.supporting_event_ids[0]].source,
        leaked[0].context_tags, leaked[0].expected_applicable,
    )
    with pytest.raises(ValueError, match="disjoint from candidate ancestry"):
        evaluate_candidate_on_probes(
            state, broad.id, leaked, partition="development", bootstrap_samples=200,
        )


def test_lifecycle_readiness_isolates_dormancy_after_validated_merge() -> None:
    result = run_lifecycle_readiness({
        "benchmark_version": "test-lifecycle-readiness",
        "seeds": [11], "probes_per_partition": 200, "bootstrap_samples": 200,
    })
    on, off = result["rows"]
    assert on["merged_status"] == off["merged_status"] == "adopted"
    assert on["dormant_parent_count"] == 2
    assert off["dormant_parent_count"] == 0
    assert on["indoor_matching_candidates"] == 1
    assert off["indoor_matching_candidates"] == 2
    assert on["supervised_labels_per_arm"] == off["supervised_labels_per_arm"] == 1200


def test_replay_instability_creates_real_split_opportunity() -> None:
    events = [Event(
        id=f"split-opportunity:{index}", timestamp=index + 1,
        actor="shared-actor", action="inspect", target="shared-device",
        target_roles=["device"],
        context_tags=["indoor" if index % 2 == 0 else "outdoor"],
        observed_effects=["warm" if index < 4 else "cold"],
        episode_id=f"split-episode:{index}", source=f"split-source:{index}",
    ) for index in range(16)]
    enabled = train_events(
        RisaState(), events,
        TrainingOptions(enable_metabolism=False, enable_context_split=True),
    )
    disabled = train_events(
        RisaState(), events,
        TrainingOptions(enable_metabolism=False, enable_context_split=False),
    )
    primitive_id = "primitive:transition:entity->process->state:inspect->warm"
    assert enabled.structural_primitives[primitive_id].replay_score < 0.6
    assert enabled.structural_adaptation_candidates[primitive_id].status == "executed"
    assert primitive_id in snapshot_mechanisms(enabled).executed_context_splits
    assert disabled.structural_adaptation_candidates[primitive_id].status == "proposed"
    assert not snapshot_mechanisms(disabled).executed_context_splits


def test_candidate_primed_drift_records_online_validation_loss() -> None:
    result = run_candidate_primed_preflight({
        "benchmark_version": "test-candidate-primed",
        "seeds": [11], "phase_observations": 6, "probes_per_phase": 6,
        "adoption_probes_per_partition": 200, "bootstrap_samples": 200,
        "extra_a2_observations": 96,
        "replay_interval": 2, "replay_max_events": 4,
        "recovery_window": 2, "arms": list(ARMS),
    })
    full = next(row for row in result["rows"] if row["arm"] == "full")
    disabled = next(row for row in result["rows"] if row["arm"] == "no_dormancy")
    assert full["a1_adopted_merges"] == disabled["a1_adopted_merges"] == 1
    assert full["a1_dormant_candidates"] == 2
    assert disabled["a1_dormant_candidates"] == 0
    assert full["a1_supervised_adoption_labels"] == 1200
    assert len(full["B_mechanism_trace"]) == 6
    assert full["B_mechanism_trace"][-1]["adopted_merges"] == 0
    assert full["final_merged_proposals"] == 0
    frozen = next(row for row in result["rows"] if row["arm"] == "no_split")
    assert frozen["final_merged_proposals"] == 1
    assert frozen["final_adopted_merges"] == 0
    assert frozen["A2_postphase_revalidated_merges"] == 1
    assert frozen["A2_postphase_revalidation_labels"] == 1200
    assert frozen["A2_extra_events_to_merge_proposal"] == 0
    assert full["A2_extra_events_to_merge_proposal"] > 0
    assert result["mechanism_opportunity_gate"] == "fail"


def test_online_validation_pilot_counts_labels_and_keeps_failed_gate() -> None:
    result = run_candidate_primed_preflight({
        "benchmark_version": "test-online-validation",
        "seeds": [11], "phase_observations": 12, "probes_per_phase": 6,
        "adoption_probes_per_partition": 200, "bootstrap_samples": 200,
        "extra_a2_observations": 0,
        "replay_interval": 4, "replay_max_events": 8,
        "recovery_window": 3, "arms": list(ARMS),
        "online_validation_a2_events": [1, 6, 12],
        "online_validation_label_budget": 3600,
    })
    rows = {row["arm"]: row for row in result["rows"]}
    assert rows["full"]["online_validation_labels"] == 0
    assert rows["no_split"]["online_validation_labels"] == 3600
    assert rows["no_split"]["online_validation_decisions"] == 18
    assert rows["no_split"]["final_adopted_merges"] == 1
    assert rows["no_split"]["final_dormant_candidates"] == 2
    assert result["mechanism_opportunity_gate"] == "fail"


def test_split_drift_opportunity_executes_without_recovery_gain() -> None:
    result = run_split_opportunity({
        "benchmark_version": "test-split-drift",
        "seeds": [11], "a1_observations": 4,
        "phase_observations": 12, "replay_interval": 1,
        "replay_max_events": 28, "recovery_window": 2,
    })
    on, off = result["rows"]
    assert on["arm"] == "split_on" and off["arm"] == "split_off"
    assert on["final_executed_context_splits"] > 0
    assert off["final_executed_context_splits"] == 0
    assert on["B_recovery_events"] == off["B_recovery_events"]
    assert on["A2_recovery_events"] == off["A2_recovery_events"]


def test_replay_cost_uses_actual_summaries() -> None:
    result = replay_cost([
        ReplaySummary(selection_events_examined=8, replayed_events=3, deployment_replayed_events=2),
        ReplaySummary(selection_events_examined=8, replayed_events=4, deployment_replayed_events=1),
    ])
    assert result == {
        "calls": 2,
        "selection_events_examined": 16,
        "model_events_reapplied": 7,
        "deployment_events_reapplied": 3,
    }


def test_training_exposes_actual_replay_summary() -> None:
    summaries: list[ReplaySummary] = []
    train_events(
        RisaState(),
        [Event("replay:1", 1, "actor", "move", observed_effects=["arrived"])],
        TrainingOptions(replay_max_events=1, replay_summaries=summaries),
    )
    assert len(summaries) == 1
    assert replay_cost(summaries)["selection_events_examined"] == 1


def test_candidate_specialization_and_merge_can_be_switched_separately() -> None:
    observations = [
        ("indoor", "warm"), ("indoor", "warm"),
        ("sheltered", "warm"), ("sheltered", "warm"),
        ("outdoor", "cold"), ("outdoor", "cold"),
    ]
    events = [
        Event(
            id=f"support:{index}", timestamp=index, actor=f"actor:{index}",
            action="inspect", target=f"device:{index}",
            target_roles=["device"], context_tags=[context],
            observed_effects=[effect], episode_id=f"episode:{index}",
            source=f"sensor:{index}",
        )
        for index, (context, effect) in enumerate(observations, 1)
    ]
    options = TrainingOptions(
        enable_replay=False, enable_metabolism=False,
        enable_candidate_merge=False,
    )
    state = train_events(RisaState(), events, options)
    snapshot = snapshot_structures(state)
    assert snapshot.fingerprints["candidates"]
    assert snapshot.fingerprints["primitives"]
    assert any(item.derivation_type == "specialized" for item in state.unnamed_concept_candidates.values())
    assert not any(item.derivation_type == "merged" for item in state.unnamed_concept_candidates.values())
    state = train_events(
        RisaState(), events,
        TrainingOptions(enable_replay=False, enable_metabolism=False,
                        enable_candidate_specialization=False),
    )
    assert all(item.derivation_generation == 0 for item in state.unnamed_concept_candidates.values())


def test_merge_only_refreshes_frozen_scopes_from_current_evidence() -> None:
    observations = [
        ("indoor", "warm"), ("indoor", "warm"),
        ("sheltered", "warm"), ("sheltered", "warm"),
        ("outdoor", "cold"), ("outdoor", "cold"),
    ]
    events = [
        Event(f"frozen:{index}", index, f"actor:{index}", "inspect",
              target=f"device:{index}", target_roles=["device"],
              context_tags=[context], observed_effects=[effect],
              episode_id=f"episode:{index}", source=f"sensor:{index}")
        for index, (context, effect) in enumerate(observations, 1)
    ]
    state = train_events(
        RisaState(), events,
        TrainingOptions(enable_replay=False, enable_candidate_merge=False),
    )
    conditions = capture_context_conditions(state)
    before_mechanisms = snapshot_mechanisms(state)
    assert conditions
    warm_parent = next(item for item in state.unnamed_concept_candidates.values()
                       if item.derivation_generation == 0
                       and item.structural_schema.get("effects") == ["warm"])
    old_support = set(warm_parent.supporting_event_ids)
    train_events(
        state,
        [Event("frozen:7", 7, "actor:7", "inspect", target="device:7",
               target_roles=["device"], context_tags=["indoor"],
               observed_effects=["warm"], episode_id="episode:7", source="sensor:7")],
        TrainingOptions(enable_replay=False, enable_candidate_specialization=False,
                        enable_candidate_merge=True,
                        frozen_context_conditions=conditions),
    )
    new_parent = state.unnamed_concept_candidates[warm_parent.id]
    assert set(new_parent.supporting_event_ids) == old_support | {"frozen:7"}
    assert any(item.derivation_type == "merged" for item in state.unnamed_concept_candidates.values())
    audit = mechanism_delta(before_mechanisms, snapshot_mechanisms(state))
    assert audit["new_merged_proposals"] >= 1
    assert audit["new_adopted_merges"] == 0
    assert all(
        tuple(item.structural_schema["required_context_tags"]) in conditions[warm_parent.id]
        for item in state.unnamed_concept_candidates.values()
        if item.derivation_type == "specialized" and item.parent_candidate_ids == [warm_parent.id]
    )


def test_context_split_switch_leaves_proposal_pending() -> None:
    state = train_events(RisaState(), [
        Event(f"split:{index}", index, f"actor:{index}", "move",
              observed_effects=["arrived"], context_tags=[context])
        for index, context in enumerate(("indoor", "indoor", "outdoor", "outdoor"), 1)
    ], TrainingOptions(enable_replay=False))
    primitive_id = "primitive:transition:entity->process->state:move->arrived"
    state.structural_adaptation_candidates[primitive_id] = StructuralAdaptationCandidate(
        primitive_id=primitive_id, reason="drift", proposed_operation="SPLIT_CONTEXT",
        pressure=0.8,
    )
    assert execute_safe_adaptations(state, enable_context_split=False) == []
    assert state.structural_adaptation_candidates[primitive_id].status == "proposed"
    assert len(execute_safe_adaptations(state, enable_context_split=True)) == 1
    assert primitive_id in snapshot_mechanisms(state).executed_context_splits
    # Replay replaces transient proposals; the executed split remains in the Primitive lineage.
    from risa.engine.replay import replay_structural_memory
    replay_structural_memory(state)
    assert primitive_id in snapshot_mechanisms(state).executed_context_splits


def test_ancestor_dormancy_switch_preserves_adopted_parent() -> None:
    observations = [
        ("indoor", "warm"), ("indoor", "warm"),
        ("sheltered", "warm"), ("sheltered", "warm"),
        ("outdoor", "cold"), ("outdoor", "cold"),
    ]
    events = [
        Event(f"dormancy:{index}", index, f"actor:{index}", "inspect",
              target=f"device:{index}", target_roles=["device"],
              context_tags=[context], observed_effects=[effect],
              episode_id=f"episode:{index}", source=f"sensor:{index}")
        for index, (context, effect) in enumerate(observations, 1)
    ]
    state = train_events(RisaState(), events, TrainingOptions(enable_replay=False))
    parent = next(item for item in state.unnamed_concept_candidates.values()
                  if item.derivation_generation == 0
                  and item.structural_schema.get("effects") == ["warm"])
    merged = next(item for item in state.unnamed_concept_candidates.values()
                  if item.derivation_type == "merged")
    parent.lifecycle_status = "adopted"
    rebuild_candidate_inference_index(state)
    arguments = dict(
        prediction_delta=0.25, composition_delta=0.0,
        prediction_delta_ci_lower=0.1, composition_delta_ci_lower=0.0,
        false_generalization_delta=-0.25,
        parent_prediction_delta=0.25, parent_composition_delta=0.0,
        parent_prediction_delta_ci_lower=0.1,
        parent_composition_delta_ci_lower=0.0,
        enable_ancestor_dormancy=False,
    )
    evaluate_derived_candidate(state, merged.id, partition="development",
                               evaluation_event_ids=["dev:probe"], **arguments)
    select_derived_candidates_for_final(state, [merged.id])
    evaluate_derived_candidate(state, merged.id, partition="final",
                               evaluation_event_ids=["final:probe"], **arguments)
    assert merged.lifecycle_status == "adopted"
    assert not parent.dormant
    before_online = snapshot_mechanisms(state)
    assert len(before_online.adopted_merges) == 1
    variants = (("indoor", True), ("sheltered", True),
                ("outdoor", False), ("exposed", False))
    development_validator = CandidateExtensionValidator([
        ExtensionProbe(
            id=f"extension-dev:{index}", episode_id=f"extension-episode:{index}",
            source=f"extension-source:{index % 2}",
            context_tags=(variants[index % 4][0],),
            expected_applicable=variants[index % 4][1],
        )
        for index in range(200)
    ], bootstrap_samples=200)

    with_unchanged_evidence = copy.deepcopy(state)
    with_unchanged_evidence_validation = TrainingOptions(
        enable_replay=False, retain_validated_on_consistent_extension=True
    )
    try:
        train_events(
            with_unchanged_evidence,
            [Event("should-not-learn", 7, "actor", "inspect", target="device")],
            with_unchanged_evidence_validation,
        )
    except ValueError as error:
        assert "extension validator" in str(error)
    else:
        raise AssertionError("validation inheritance must require a validator")
    consistent = copy.deepcopy(state)
    train_events(
        consistent,
        [Event("dormancy:support:7", 7, "actor:7", "inspect", target="device:7",
               target_roles=["device"], context_tags=["indoor"],
               observed_effects=["warm"], episode_id="episode:7", source="sensor:7")],
        TrainingOptions(enable_replay=False,
                        retain_validated_on_consistent_extension=True,
                        candidate_extension_validator=development_validator),
    )
    retained = snapshot_mechanisms(consistent)
    assert len(retained.adopted_merges) == 1
    assert retained.adopted_merges != before_online.adopted_merges
    assert any(decision["accepted"] for decision in development_validator.decisions)
    assert retained.adopted_merges.issubset({
        item.id for item in matching_adopted_candidates(
            consistent, "inspect", ["device"], ["indoor"]
        )
    })
    assert snapshot_mechanisms(RisaState.from_dict(consistent.to_dict())).adopted_merges == retained.adopted_merges
    rejected = copy.deepcopy(state)
    train_events(
        rejected,
        [Event("dormancy:support:8", 7, "actor:8", "inspect", target="device:8",
               target_roles=["device"], context_tags=["indoor"],
               observed_effects=["warm"], episode_id="episode:8", source="sensor:8")],
        TrainingOptions(enable_replay=False,
                        retain_validated_on_consistent_extension=True,
                        candidate_extension_validator=lambda current, old, new: False),
    )
    assert not snapshot_mechanisms(rejected).adopted_merges
    overlap = copy.deepcopy(state)
    train_events(
        overlap,
        [Event("final:probe", 7, "actor:7", "inspect", target="device:7",
               target_roles=["device"], context_tags=["indoor"],
               observed_effects=["warm"], episode_id="episode:7", source="sensor:7")],
        TrainingOptions(enable_replay=False,
                        retain_validated_on_consistent_extension=True,
                        candidate_extension_validator=development_validator),
    )
    assert not snapshot_mechanisms(overlap).adopted_merges
    train_events(
        state,
        [Event("dormancy:7", 7, "actor:7", "inspect", target="device:7",
               target_roles=["device"], context_tags=["indoor"],
               observed_effects=["cold"], episode_id="episode:7", source="sensor:7")],
        TrainingOptions(enable_replay=False,
                        retain_validated_on_consistent_extension=True,
                        candidate_extension_validator=development_validator),
    )
    after_online = snapshot_mechanisms(state)
    assert not after_online.adopted_merges
