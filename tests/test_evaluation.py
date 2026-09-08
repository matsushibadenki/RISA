from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from risa.evaluation.benchmark import generate_benchmark, load_manifest, run_benchmark


MANIFEST_PATH = Path(__file__).parents[1] / "experiments" / "g1_manifest.json"


class ComparativeEvaluationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
