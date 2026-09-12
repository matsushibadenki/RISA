from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from experiments.candidate_transfer_evaluation import run_candidate_transfer
from experiments.context_conjunction_evaluation import (
    run_context_conjunction_evaluation,
)
from experiments.derived_candidate_evaluation import run_derived_candidate_evaluation
from experiments.generic_relation_candidate_evaluation import (
    run_generic_relation_evaluation,
)
from experiments.g2_persistence_evaluation import run_persistence_evaluation
from experiments.structural_role_evaluation import run_structural_role_evaluation
from experiments.temporal_candidate_evaluation import (
    run_temporal_candidate_evaluation,
)
from risa.evaluation.benchmark import generate_benchmark, load_manifest, run_benchmark


MANIFEST_PATH = Path(__file__).parents[1] / "experiments" / "g1_manifest.json"


class ComparativeEvaluationTests(unittest.TestCase):
    def test_structure_induced_roles_match_supplied_roles_on_heldout_targets(self) -> None:
        result = run_structural_role_evaluation(
            {
                "benchmark_version": "test-structural-role",
                "seeds": [37],
                "development_episodes_per_seed": 40,
                "final_episodes_per_seed": 40,
                "bootstrap_samples": 100,
                "minimum_gain": 0.05,
            }
        )

        self.assertEqual(result["decision"], "adopt_structural_role_induction")
        self.assertTrue(all(value == 0 for value in result["leakage_audit"].values()))
        aggregate = result["aggregate"]
        self.assertEqual(aggregate["induced_prediction_success_rate"], 1.0)
        self.assertEqual(aggregate["supplied_prediction_success_rate"], 1.0)
        self.assertEqual(aggregate["no_role_prediction_success_rate"], 0.5)
        self.assertEqual(aggregate["induced_composition_success_rate"], 1.0)
        self.assertEqual(aggregate["supplied_composition_success_rate"], 1.0)
        self.assertEqual(aggregate["no_role_composition_success_rate"], 0.5)
        self.assertEqual(aggregate["induced_mistyping_rate"], 0.0)
        self.assertEqual(aggregate["supplied_mistyping_rate"], 0.0)
        self.assertLess(
            aggregate["mean_induced_state_bytes"],
            aggregate["mean_supplied_state_bytes"],
        )
        self.assertEqual(
            set(result["lifecycle"][0]["induced_after_final"]), {"adopted"}
        )

    def test_noisy_context_conjunction_selects_one_causal_final_candidate(self) -> None:
        result = run_context_conjunction_evaluation(
            {
                "benchmark_version": "test-context-conjunction",
                "seeds": [31],
                "development_episodes_per_seed": 160,
                "final_episodes_per_seed": 40,
                "bootstrap_samples": 100,
                "minimum_gain": 0.05,
                "proxy_count": 6,
            }
        )
        self.assertEqual(result["decision"], "adopt_bounded_conjunction_selection")
        self.assertEqual(
            result["leakage_audit"],
            {
                "support_development_overlap": 0,
                "support_final_overlap": 0,
                "development_final_overlap": 0,
            },
        )
        self.assertEqual(result["aggregate"]["generated_candidates"], 7.0)
        self.assertEqual(result["aggregate"]["explored_hypotheses"], 36.0)
        self.assertEqual(result["aggregate"]["candidate_success_rate"], 1.0)
        self.assertEqual(result["aggregate"]["parent_success_rate"], 0.5)
        self.assertTrue(result["lifecycle"][0]["selected_stable_condition"])

    def test_automatic_context_merge_beats_its_parent_on_heldout_cases(self) -> None:
        result = run_derived_candidate_evaluation(
            {
                "benchmark_version": "test-derived-context",
                "seeds": [17],
                "development_episodes_per_seed": 40,
                "final_episodes_per_seed": 40,
                "minimum_gain": 0.05,
                "bootstrap_samples": 100,
            }
        )
        self.assertEqual(result["decision"], "adopt")
        self.assertTrue(result["lifecycle"][0]["broad_ancestor_dormant_after_final"])
        self.assertEqual(result["aggregate"]["derived_success_rate"], 1.0)
        self.assertEqual(result["aggregate"]["parent_success_rate"], 0.75)
        self.assertEqual(result["aggregate"]["derived_vs_parent_delta"], 0.25)
        self.assertEqual(result["aggregate"]["broad_ancestor_success_rate"], 0.5)
        self.assertEqual(
            result["aggregate"]["derived_false_generalization_rate"], 0.0
        )
        self.assertEqual(
            result["aggregate"]["parent_false_generalization_rate"], 0.0
        )
        self.assertEqual(
            result["aggregate"]["broad_ancestor_false_generalization_rate"], 1.0
        )

    def test_schema_v4_persistence_is_smaller_and_behaviorally_equivalent(self) -> None:
        result = run_persistence_evaluation(
            {
                "benchmark_version": "test-persistence",
                "source_manifest": str(
                    Path(__file__).parents[1] / "experiments" / "g2_manifest.json"
                ),
                "seeds": [31],
                "load_repetitions": 2,
            }
        )
        aggregate = result["aggregate"]
        self.assertEqual(result["decision"], "accepted_schema_v4_persistence")
        self.assertLess(
            aggregate["mean_schema_v4_bytes"],
            aggregate["mean_verbose_equivalent_bytes"],
        )
        self.assertEqual(aggregate["prediction_mismatches"], 0)
        self.assertEqual(aggregate["planning_mismatches"], 0)
        self.assertEqual(aggregate["composition_matches"], 1)
        self.assertEqual(aggregate["simulation_matches"], 1)

    def test_generator_is_reproducible_and_keeps_evaluation_ids_held_out(self) -> None:
        manifest = replace(
            load_manifest(MANIFEST_PATH),
            seeds=(7,),
            held_out_episodes_per_split=60,
        )

        first = generate_benchmark(7, manifest)
        second = generate_benchmark(7, manifest)

        self.assertEqual(first.static_cases, second.static_cases)
        self.assertEqual(first.drift_cases, second.drift_cases)
        self.assertEqual(first.audit["event_id_overlap"], 0)
        self.assertEqual(first.audit["composition_temporal_edges_supplied"], 0)
        self.assertEqual(
            {case.split for case in first.static_cases} | {"drift"},
            set(manifest.splits),
        )
        for phase in {case.phase for case in first.drift_cases}:
            partitions = {
                case.partition for case in first.drift_cases if case.phase == phase
            }
            self.assertEqual(partitions, {"development", "final"})
        self.assertTrue(any(case.observation_mask for case in first.static_cases))
        self.assertTrue(any(case.forbidden_states for case in first.static_cases))
        self.assertTrue(any(case.observation_delay for case in first.drift_cases))
        self.assertTrue(any(case.context for case in first.drift_cases if case.phase == "B"))

    def test_partial_observation_mask_scores_the_observed_subset(self) -> None:
        manifest = replace(
            load_manifest(MANIFEST_PATH),
            seeds=(11,),
            held_out_episodes_per_split=6,
            methods=("risa", "oracle"),
        )

        result = run_benchmark(manifest)

        uncertainty_rows = [
            row
            for row in result["rows"]
            if row["split"] == "uncertainty" and row["method"] == "risa"
        ]
        self.assertTrue(uncertainty_rows)
        self.assertTrue(all(row["success_rate"] >= 0.0 for row in uncertainty_rows))
        self.assertTrue(all("success_95ci" in row for row in uncertainty_rows))

    def test_all_declared_methods_and_splits_produce_results(self) -> None:
        manifest = replace(
            load_manifest(MANIFEST_PATH),
            seeds=(13,),
            held_out_episodes_per_split=6,
        )

        result = run_benchmark(manifest)

        observed_methods = {row["method"] for row in result["rows"]}
        observed_splits = {row["split"] for row in result["rows"]}
        self.assertEqual(observed_methods, set(manifest.methods))
        self.assertEqual(observed_splits, set(manifest.splits))
        self.assertTrue(
            all("stored_bytes" in row and "mean_episode_ms" in row for row in result["rows"])
        )
        drift_rows = [row for row in result["rows"] if row["split"] == "drift"]
        self.assertTrue(all("forgetting_delta_a1_minus_a2" in row for row in drift_rows))

    def test_g2_role_binding_and_learned_applicability_are_ablatable(self) -> None:
        manifest = replace(
            load_manifest(Path(__file__).parents[1] / "experiments" / "g2_manifest.json"),
            seeds=(17,),
            held_out_episodes_per_split=10,
            methods=(
                "risa",
                "grounded_transition",
                "risa_no_role_binding",
                "risa_no_change_adaptation",
            ),
        )

        result = run_benchmark(manifest)

        def success(method: str, split: str) -> float:
            rows = [
                row
                for row in result["aggregate"]
                if row["method"] == method and row["split"] == split
            ]
            return max(row["success_rate"] for row in rows)

        self.assertEqual(success("risa", "binding"), 1.0)
        self.assertLess(success("risa_no_role_binding", "binding"), 1.0)
        self.assertEqual(success("risa", "composition_learned"), 1.0)
        self.assertEqual(success("grounded_transition", "composition_learned"), 0.0)

    def test_redundant_candidate_is_rejected_but_preserves_compressed_readout(self) -> None:
        result = run_candidate_transfer(
            {
                "benchmark_version": "test-candidate",
                "seeds": [19],
                "development_episodes_per_seed": 16,
                "final_episodes_per_seed": 4,
                "minimum_gain": 0.05,
                "bootstrap_samples": 100,
            }
        )

        self.assertEqual(
            result["decision"], "rejected_redundant_single_transition_candidate"
        )
        self.assertEqual(
            result["compaction_decision"],
            "rejected_persisted_total_state_growth",
        )
        self.assertEqual(result["leakage_audit"]["development_final_overlap"], 0)
        final = next(
            row for row in result["aggregate"] if row["partition"] == "final"
        )
        self.assertEqual(final["paired_delta"], 0.0)
        self.assertEqual(final["false_generalization_delta"], 0.0)
        self.assertEqual(final["compressed_readout_candidate_success_rate"], 1.0)
        self.assertLess(final["compressed_readout_no_candidate_success_rate"], 1.0)
        self.assertEqual(final["regression_queries_checked"], 4)
        self.assertGreater(final["mean_total_state_bytes_before"], 0)
        self.assertGreater(final["mean_total_state_bytes_after"], 0)
        self.assertLess(
            final["mean_reconstructed_candidate_state_bytes"],
            final["mean_full_candidate_state_bytes"],
        )
        self.assertLess(
            final["mean_compact_event_state_bytes"],
            final["mean_verbose_event_state_bytes"],
        )
        self.assertLess(
            final["mean_compact_event_state_bytes"],
            final["mean_uncompressed_reconstructable_state_bytes"],
        )
        self.assertLess(
            final["mean_compact_derived_state_bytes"],
            final["mean_verbose_derived_state_bytes"],
        )
        self.assertGreater(final["mean_prediction_p95_ms_before"], 0.0)
        self.assertGreater(final["mean_prediction_p95_ms_after"], 0.0)

    def test_role_scoped_temporal_candidate_is_adopted_on_disjoint_evidence(self) -> None:
        result = run_temporal_candidate_evaluation(
            {
                "benchmark_version": "test-temporal-candidate",
                "seeds": [23],
                "development_episodes_per_seed": 16,
                "final_episodes_per_seed": 40,
                "minimum_gain": 0.05,
                "bootstrap_samples": 100,
            }
        )

        self.assertEqual(
            result["decision"], "adopted_role_scoped_temporal_candidate"
        )
        self.assertEqual(result["leakage_audit"]["support_development_overlap"], 0)
        self.assertEqual(result["leakage_audit"]["support_final_overlap"], 0)
        self.assertEqual(result["leakage_audit"]["development_final_overlap"], 0)
        final = next(
            row for row in result["aggregate"] if row["partition"] == "final"
        )
        self.assertEqual(final["candidate_success_rate"], 1.0)
        self.assertEqual(final["existing_path_success_rate"], 0.75)
        self.assertEqual(final["paired_delta"], 0.25)
        self.assertEqual(final["candidate_false_generalization_rate"], 0.0)

    def test_actor_target_relational_candidate_is_adopted(self) -> None:
        result = run_temporal_candidate_evaluation(
            {
                "benchmark_version": "test-relational-candidate",
                "seeds": [29],
                "development_episodes_per_seed": 20,
                "final_episodes_per_seed": 40,
                "minimum_gain": 0.05,
                "bootstrap_samples": 100,
                "actor_target_role_binding": True,
            }
        )

        self.assertEqual(
            result["decision"], "adopted_role_scoped_temporal_candidate"
        )
        final = next(
            row for row in result["aggregate"] if row["partition"] == "final"
        )
        self.assertEqual(final["candidate_success_rate"], 1.0)
        self.assertEqual(final["existing_path_success_rate"], 0.4)
        self.assertEqual(final["paired_delta"], 0.6)
        self.assertEqual(final["candidate_false_generalization_rate"], 0.0)

    def test_generic_entity_relation_candidate_is_adopted(self) -> None:
        result = run_generic_relation_evaluation(
            {
                "benchmark_version": "test-generic-relation",
                "seeds": [31],
                "development_episodes_per_seed": 20,
                "final_episodes_per_seed": 40,
                "minimum_gain": 0.05,
                "bootstrap_samples": 100,
            }
        )

        self.assertEqual(result["decision"], "adopted_generic_relation_candidate")
        self.assertTrue(all(value == 0 for value in result["leakage_audit"].values()))
        final = next(
            row for row in result["aggregate"] if row["partition"] == "final"
        )
        self.assertEqual(final["candidate_success_rate"], 1.0)
        self.assertEqual(final["existing_path_success_rate"], 0.2)
        self.assertEqual(final["paired_delta"], 0.8)
        self.assertEqual(final["candidate_false_generalization_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
