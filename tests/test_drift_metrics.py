from __future__ import annotations

import copy
from dataclasses import replace
import pytest

from experiments.g3_drift_preflight import ARMS, _events, mechanism_opportunity_audit, run_preflight
from experiments.g3_lifecycle_readiness import run_lifecycle_readiness
from experiments.g3_drift_candidate_primed import run_candidate_primed_preflight
from experiments.g3_split_drift_opportunity import (
    _events as split_events, _probes as split_probes, run_split_opportunity,
)
from risa.core.models import (
    Event, Node, ReplaySummary, StructuralAdaptationCandidate, StructuralPrimitive,
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
from risa.engine.predictor import (
    _matching_primitives, _primitive_support, predict_next_effect,
)
from risa.evaluation.candidate_extension import CandidateExtensionValidator, ExtensionProbe
from risa.evaluation.candidate_adoption import ApplicabilityProbe, evaluate_candidate_on_probes
from risa.evaluation.drift_metrics import (
    adaptation_touch_counts,
    mechanism_delta,
    recovery_events,
    retention_adaptation_audit,
    replay_cost,
    snapshot_mechanisms,
    snapshot_structures,
)
from risa.evaluation.drift_runner import (
    DriftProbe, ValidationStepResult, probe_return_identifiability, run_aba,
    run_drift_phase,
)
from risa.evaluation.replay_diagnostics import contextual_replay_errors
from risa.evaluation.readout_attribution import attribute_prediction_readout
from risa.evaluation.grounded_role_baseline import (
    GroundedRoleCountBaseline, GroundedRoleTransitionBaseline,
)
from risa.evaluation.split_variant_validation import audit_split_variants_on_probes


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


def test_retention_requires_b_adaptation_for_qualified_interpretation() -> None:
    underadapted = retention_adaptation_audit(
        a1_accuracy=1.0, b_exit_accuracy=0.5, a2_entry_accuracy=1.0,
    )
    assert underadapted["retention_after_return"] == 1.0
    assert underadapted["b_adapted_at_return"] is False
    assert underadapted["retention_given_b_adaptation"] is None
    adapted = retention_adaptation_audit(
        a1_accuracy=1.0, b_exit_accuracy=1.0, a2_entry_accuracy=0.5,
    )
    assert adapted["b_adapted_at_return"] is True
    assert adapted["retention_given_b_adaptation"] == 0.5
    assert retention_adaptation_audit(
        a1_accuracy=0.0, b_exit_accuracy=1.0, a2_entry_accuracy=0.0,
    )["retention_given_b_adaptation"] is None
    with pytest.raises(ValueError, match="probe accuracies"):
        retention_adaptation_audit(
            a1_accuracy=1.0, b_exit_accuracy=1.1, a2_entry_accuracy=1.0,
        )


def test_return_probe_identifiability_detects_same_query_conflict() -> None:
    indoor = PredictionQuery("actor", "inspect", "device", context_tags=["indoor"])
    outdoor = replace(indoor, context_tags=["outdoor"])
    a = [DriftProbe("a:indoor", indoor, ("warm",)),
         DriftProbe("a:outdoor", outdoor, ("warm",))]
    b = [DriftProbe("b:indoor", indoor, ("cold",)),
         DriftProbe("b:outdoor", outdoor, ("warm",))]
    audit = probe_return_identifiability(a, b)
    assert audit == {
        "identical_query_conflicting_a_probes": 1,
        "a_probe_count": 2,
        "b_reference_internally_consistent": True,
        "a_accuracy_ceiling_given_perfect_b": 0.5,
    }
    cued_b = [replace(probe, query=replace(probe.query, context_tags=[
        *probe.query.context_tags, "phase:B",
    ])) for probe in b]
    assert probe_return_identifiability(a, cued_b)[
        "a_accuracy_ceiling_given_perfect_b"
    ] == 1.0
    contradictory_b = b + [DriftProbe("b:other", indoor, ("warm",))]
    assert probe_return_identifiability(a, contradictory_b)[
        "a_accuracy_ceiling_given_perfect_b"
    ] is None


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


def test_phase_pre_update_diagnostic_runs_before_learning_and_is_read_only() -> None:
    state = RisaState()
    event = Event("observe:diagnostic", 1, "actor", "move", observed_effects=["a"])
    probe = DriftProbe("probe:diagnostic", PredictionQuery("actor", "move"), ("a",))

    def inspect(current, index, pending):
        return {"not_learned_yet": pending.id not in current.events_by_id}

    result = run_drift_phase(
        state, [event], [probe], TrainingOptions(enable_replay=False),
        reference_accuracy=1.0, pre_update_diagnostic=inspect,
    )
    assert result["pre_update_diagnostic_trace"][0]["diagnostic"] == {
        "not_learned_yet": True
    }
    assert event.id in state.events_by_id

    def mutate(current, index, pending):
        current.events_by_id[pending.id] = pending
        return {}

    with pytest.raises(ValueError, match="must not change learning state"):
        run_drift_phase(
            RisaState(), [event], [probe], TrainingOptions(enable_replay=False),
            reference_accuracy=1.0, pre_update_diagnostic=mutate,
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


def test_contextual_drift_retains_stable_context_but_does_not_trigger_split() -> None:
    result = run_split_opportunity({
        "benchmark_version": "test-contextual-split-drift",
        "seeds": [11], "a1_observations": 4,
        "phase_observations": 12, "contextual_drift": True,
        "replay_interval": 1, "replay_max_events": 28,
        "recovery_window": 2,
    })
    on, off = result["rows"]
    assert on["final_executed_context_splits"] == 0
    assert off["final_executed_context_splits"] == 0
    assert on["retention_after_return"] == off["retention_after_return"] == 0.5
    assert on["B_recovery_events"] == off["B_recovery_events"]
    warm = {
        row["context"]: row
        for row in on["B_contextual_replay_diagnostic"]["rows"]
        if row["primitive_id"].endswith("->warm")
    }
    assert warm["indoor"]["incorrect_events"] == warm["indoor"]["distinct_events"] == 2
    assert warm["outdoor"]["incorrect_events"] == 0
    assert warm["outdoor"]["distinct_events"] == 8
    assert warm["indoor"]["cumulative_replay_score"] > 0.6


def test_contextual_replay_diagnostic_does_not_change_learning_state() -> None:
    state = train_events(
        RisaState(), split_events(11, "A1", 4, True),
        TrainingOptions(enable_replay=False, enable_metabolism=False),
    )
    for event in split_events(11, "B", 12, True):
        train_events(state, [event], TrainingOptions(enable_metabolism=False))
    before = copy.deepcopy(state.to_dict())
    result = contextual_replay_errors(state, max_events=16)
    assert result["selected_events"] == 16
    assert state.to_dict() == before


def test_readout_attribution_does_not_change_learning_state() -> None:
    state = train_events(
        RisaState(), split_events(11, "A1", 4, True),
        TrainingOptions(enable_replay=False, enable_metabolism=False),
    )
    before = copy.deepcopy(state.to_dict())
    result = attribute_prediction_readout(state, [
        DriftProbe("heldout:attribution", PredictionQuery(
            "actor:11", "inspect", "device:11",
            context_tags=["indoor"], target_roles=["device"],
        ), ("warm",)),
    ])
    assert result["probe_count"] == 1
    assert state.to_dict() == before


def test_contextual_split_proposal_triggers_but_can_delay_recovery() -> None:
    result = run_split_opportunity({
        "benchmark_version": "test-contextual-proposal",
        "seeds": [23], "a1_observations": 4,
        "phase_observations": 12, "contextual_drift": True,
        "include_contextual_proposal": True,
        "replay_interval": 1, "replay_max_events": 28,
        "recovery_window": 2,
    })
    global_rule, contextual_rule, split_off = result["rows"]
    assert global_rule["final_executed_context_splits"] == 0
    assert contextual_rule["final_executed_context_splits"] == 1
    assert split_off["final_executed_context_splits"] == 0
    assert contextual_rule["B_split_variant_contexts"] == [["indoor"], ["outdoor"]]
    assert contextual_rule["retention_after_return"] == global_rule["retention_after_return"]
    assert contextual_rule["A2_recovery_events"] > global_rule["A2_recovery_events"]
    attribution = contextual_rule["B_readout_on_B_probes"]["variants"]
    assert attribution["full"]["accuracy"] == 1.0
    assert attribution["no_primitive"]["predictions_changed_vs_full"] == 0
    assert attribution["no_primitive"]["mean_absolute_score_change_vs_full"] == 0.05
    assert attribution["no_recent_outcome"]["predictions_changed_vs_full"] == 0
    assert attribution["no_recent_outcome"]["mean_absolute_score_change_vs_full"] == 0.5
    wrong = contextual_rule["A2_pre_update_readout_trace"][7]["diagnostic"]["variants"]
    assert wrong["full"]["predicted_effects_by_probe"]["A2:23:7"] == ["cold"]
    assert wrong["no_primitive"]["predicted_effects_by_probe"]["A2:23:7"] == ["warm"]
    transfer = contextual_rule["B_transfer_on_B_probes"]["variants"]
    assert transfer["full"]["accuracy"] == 1.0
    assert transfer["no_primitive"]["predictions_changed_vs_full"] == 0


def test_grounded_role_baseline_uses_only_observed_role_context() -> None:
    model = GroundedRoleTransitionBaseline()
    indoor = PredictionQuery(
        "new-actor", "inspect", "new-device",
        target_roles=["device"], context_tags=["indoor"],
    )
    outdoor = replace(indoor, context_tags=["outdoor"])
    missing_role = replace(indoor, target_roles=[])
    assert model.predict(indoor) == ()
    model.observe(Event(
        "a1:role", 1, "old-actor", "inspect", target="old-device",
        target_roles=["device"], context_tags=["indoor"],
        observed_effects=["warm"],
    ))
    assert model.predict(indoor) == ("warm",)
    assert model.predict(outdoor) == model.predict(missing_role) == ()
    model.observe(Event(
        "b:role", 2, "old-actor", "inspect", target="old-device",
        target_roles=["device"], context_tags=["indoor"],
        observed_effects=["cold"],
    ))
    assert model.predict(indoor) == ("cold",)


def test_grounded_role_count_baseline_votes_and_breaks_ties_by_recency() -> None:
    model = GroundedRoleCountBaseline()
    query = PredictionQuery(
        "new-actor", "inspect", "new-device",
        target_roles=["device"], context_tags=["indoor"],
    )
    assert model.predict(query) == ()
    for index, effect in enumerate(("warm", "warm", "cold", "cold", "warm"), 1):
        model.observe(Event(
            f"vote:{index}", index, "old-actor", "inspect", target="old-device",
            target_roles=["device"], context_tags=["indoor"],
            observed_effects=[effect],
        ))
        assert model.predict(query) == (
            ("warm",) if index != 4 else ("cold",)
        )
    assert model.stored_bytes() > 0


def test_role_baseline_is_stronger_on_contextual_drift_development_world() -> None:
    result = run_split_opportunity({
        "benchmark_version": "test-role-baseline",
        "seeds": [23], "a1_observations": 4,
        "phase_observations": 12, "contextual_drift": True,
        "include_contextual_proposal": True,
        "replay_interval": 1, "replay_max_events": 28,
        "recovery_window": 2,
    })
    baseline = result["grounded_role_baseline_rows"][0]
    contextual = next(row for row in result["rows"] if row["arm"] == "contextual_split")
    assert baseline["B"]["online_pre_update_accuracy"] == 11 / 12
    assert baseline["A2"]["online_pre_update_accuracy"] == 11 / 12
    assert baseline["B"]["recovery_events"] < contextual["B_recovery_events"]
    assert baseline["A2"]["recovery_events"] < contextual["A2_recovery_events"]
    assert baseline["retention_after_return"] == contextual["retention_after_return"]


def test_contextual_observation_noise_is_balanced_and_probes_latent_rule() -> None:
    for phase in ("B", "A2"):
        clean = split_events(11, phase, 20, True)
        noisy = split_events(11, phase, 20, True, 0.2)
        assert [event.id for event in noisy] == [event.id for event in clean]
        assert [event.context_tags for event in noisy] == [event.context_tags for event in clean]
        changed = [event for event, original in zip(noisy, clean)
                   if event.observed_effects != original.observed_effects]
        assert len(changed) == 4
        assert sum(event.context_tags == ["indoor"] for event in changed) == 2
        assert sum(event.context_tags == ["outdoor"] for event in changed) == 2
        probes = split_probes(11, "B" if phase == "B" else "A", True)
        assert [probe.expected_effects for probe in probes] == (
            [("cold",), ("warm",)] * 2 if phase == "B" else [("warm",)] * 4
        )
    assert [event.observed_effects for event in split_events(11, "A1", 10, True, 0.2)] == [
        ["warm"]
    ] * 10
    with pytest.raises(ValueError, match="exact count"):
        split_events(11, "B", 12, True, 0.2)


def test_return_cue_is_observable_and_removes_exact_query_conflict() -> None:
    a1 = split_events(11, "A1", 10, True, phase_context_cue=True)
    b = split_events(11, "B", 20, True, 0.2, True)
    a2 = split_events(11, "A2", 20, True, 0.2, True)
    assert {tuple(event.context_tags) for event in a1} == {
        ("indoor", "regime:A"), ("outdoor", "regime:A")
    }
    assert {tuple(event.context_tags) for event in b} == {
        ("indoor", "regime:B"), ("outdoor", "regime:B")
    }
    assert {tuple(event.context_tags) for event in a2} == {
        ("indoor", "regime:A"), ("outdoor", "regime:A")
    }
    assert all(event.observed_effects == ["warm"] for event in a1)
    assert sum(event.observed_effects != [
        "cold" if event.context_tags[0] == "indoor" else "warm"
    ] for event in b) == 4
    audit = probe_return_identifiability(
        split_probes(11, "A", True, True), split_probes(11, "B", True, True)
    )
    assert audit["identical_query_conflicting_a_probes"] == 0
    assert audit["a_accuracy_ceiling_given_perfect_b"] == 1.0


def test_noisy_return_cue_audits_adopted_off_rule_split_variants() -> None:
    result = run_split_opportunity({
        "benchmark_version": "test-return-cue-variant-audit",
        "seeds": [11], "a1_observations": 10, "phase_observations": 20,
        "contextual_drift": True, "phase_context_cue": True,
        "include_contextual_proposal": True,
        "observation_noise_fraction": 0.2,
        "split_validation_labels_per_context": 8,
        "replay_interval": 1, "replay_max_events": 50,
        "recovery_window": 2,
    })
    rows = {row["arm"]: row for row in result["rows"]}
    assert rows["split_off"]["B_split_variant_audit"]["B_scope_variants"] == 0
    contextual = rows["contextual_split"]["B_split_variant_audit"]
    assert contextual["B_scope_variants"] == 4
    assert contextual["adopted_off_rule_variants"] == 2
    assert sorted(row["support"] for row in contextual["rows"]
                  if row["adopted"] and not row["matches_B_latent_rule"]) == [2, 2]
    heldout = rows["contextual_split"]["B_split_heldout_validation"]
    assert heldout["available_labels"] == heldout["consumed_labels"] == 16
    assert heldout["variant_evaluations"] == 4
    assert heldout["adopted_variants_failing_heldout"] == 2
    assert sorted(row["heldout_accuracy"] for row in heldout["rows"]) == [0.0, 0.0, 1.0, 1.0]
    assert rows["contextual_split"]["B_probe_accuracy_by_observed_events"] == (
        rows["split_off"]["B_probe_accuracy_by_observed_events"]
    )


def test_split_variant_heldout_audit_is_read_only_and_rejects_label_overlap() -> None:
    state = RisaState()
    primitive = StructuralPrimitive(
        id="primitive:inspect->warm::context:indoor",
        relation_type="transition", role_signature="entity->process->state",
        input_conditions={"process:inspect"}, output_state="warm",
        context_tags={"indoor"}, support=2, adopted=True,
    )
    state.structural_primitives[primitive.id] = primitive
    probe = DriftProbe("validation:indoor", PredictionQuery(
        "new-actor", "inspect", context_tags=["indoor"]
    ), ("cold",))
    before = copy.deepcopy(state.to_dict())
    result = audit_split_variants_on_probes(state, [probe])
    assert result["adopted_variants_failing_heldout"] == 1
    assert result["rows"][0]["heldout_accuracy"] == 0.0
    assert state.to_dict() == before
    with pytest.raises(ValueError, match="overlap"):
        audit_split_variants_on_probes(state, [probe], scoring_probe_ids={probe.id})
    with pytest.raises(ValueError, match="unique"):
        audit_split_variants_on_probes(state, [probe, probe])


def test_split_variant_support_requires_exact_context_match() -> None:
    state = RisaState()
    split = StructuralPrimitive(
        id="primitive:inspect->warm::context:indoor|regime:a",
        relation_type="transition", role_signature="entity->process->state",
        input_conditions={"process:inspect"}, output_state="warm",
        context_tags={"indoor", "regime:a"}, support=5,
        validation_score=1.0, adopted=True,
    )
    state.structural_primitives[split.id] = split
    assert _primitive_support(state, "inspect", "warm", "indoor|regime:a") == 1.0
    assert _primitive_support(state, "inspect", "warm", "indoor|regime:b") == 0.0
    assert _matching_primitives(
        state, "inspect", "warm", context_key="indoor|regime:b"
    ) == []
    assert predict_next_effect(state, PredictionQuery(
        "actor", "inspect", context_tags=["indoor", "regime:B"]
    )).predicted_effects == []
    exact = predict_next_effect(state, PredictionQuery(
        "actor", "inspect", context_tags=["indoor", "regime:A"]
    ))
    assert exact.predicted_effects == ["warm"]
    assert any(split.id in path for path in exact.supporting_paths)
    unsplit = replace(split, id="primitive:inspect->warm")
    state.structural_primitives = {unsplit.id: unsplit}
    assert _primitive_support(state, "inspect", "warm", "indoor|regime:b") == 0.5
    assert _matching_primitives(
        state, "inspect", "warm", context_key="indoor|regime:b"
    ) == [unsplit]


def test_contextual_split_proposal_does_not_split_fully_stable_world() -> None:
    options = TrainingOptions(
        enable_metabolism=False, enable_contextual_split_proposal=True,
        enable_candidate_specialization=False, enable_candidate_merge=False,
    )
    state = train_events(
        RisaState(), split_events(11, "A1", 4, True),
        replace(options, enable_replay=False),
    )
    for event in split_events(11, "B", 12, True):
        train_events(state, [replace(event, observed_effects=["warm"])], options)
    assert not snapshot_mechanisms(state).executed_context_splits


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
