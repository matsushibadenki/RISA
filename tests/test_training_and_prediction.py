import unittest

from risa.core.models import Event, PredictionQuery
from risa.core.state import RisaState
from risa.engine.abstractor import rebuild_concepts
from risa.engine.composer import compose_to_effect, forecast_next_effects
from risa.engine.event_parser import parse_events
from risa.engine.predictor import predict_next_effect
from risa.engine.runtime import train_events


class TrainingAndPredictionTests(unittest.TestCase):
    def test_train_and_predict_generalizes_run_to_fatigue(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        result = predict_next_effect(state, PredictionQuery(actor="wolf", action="run"))

        self.assertEqual(result.predicted_effects, ["fatigue_up"])
        self.assertGreater(result.score, 0)
        self.assertGreaterEqual(len(state.concept_members), 1)
        self.assertTrue(any("event:" in " -> ".join(path) for path in result.supporting_paths))

    def test_context_bias_changes_local_prediction_candidates(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        result = predict_next_effect(
            state,
            PredictionQuery(actor="dog", action="drink", context_tags=["animal", "hydration"]),
        )

        self.assertEqual(result.predicted_effects, ["thirst_down"])
        self.assertGreater(result.score, 0)

    def test_concept_cell_receives_energy_when_pattern_is_supported(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)
        rebuild_concepts(state)

        concept = state.graph.get_node("concept:shared_run_fatigue_up")
        self.assertIsNotNone(concept)
        self.assertFalse(concept.dormant)
        self.assertGreater(concept.energy, 0.4)

    def test_training_creates_coactivation_trace_for_repeated_memory(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        edge = state.graph.edges_by_key.get(("entity:dog", "process:run", "co_activates_with"))
        self.assertIsNotNone(edge)
        assert edge is not None
        self.assertGreater(edge.reliability, 0.0)
        self.assertGreaterEqual(edge.evidence_count, 1)

    def test_prediction_exposes_coactivation_support_path(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        result = predict_next_effect(state, PredictionQuery(actor="dog", action="run"))

        self.assertEqual(result.predicted_effects, ["fatigue_up"])
        self.assertTrue(any("co_activates_with" in path for path in result.supporting_paths))
        self.assertIn("co-activation", result.explanation)

    def test_prediction_can_use_coactivation_candidates_without_activation_index(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        state.activation_index = {}
        result = predict_next_effect(state, PredictionQuery(actor="dog", action="run"))

        self.assertEqual(result.predicted_effects, ["fatigue_up"])
        self.assertGreater(result.score, 0)

    def test_prediction_can_use_coactivation_radius_without_direct_counts(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        state.activation_index = {}
        state.actor_action_effect_counts = {}
        state.actor_action_context_effect_counts = {}
        state.action_context_effect_counts = {}

        result = predict_next_effect(state, PredictionQuery(actor="dog", action="run"))

        self.assertEqual(result.predicted_effects, ["fatigue_up"])
        self.assertGreater(result.score, 0)

    def test_structural_pattern_is_learned_from_contextual_transition(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        pattern = state.structural_patterns.get("structural:entity->process->state:animal|movement")
        self.assertIsNotNone(pattern)
        assert pattern is not None
        self.assertIn("run", pattern.actions)
        self.assertIn("fatigue_up", pattern.effects)
        self.assertGreaterEqual(pattern.support, 3)

    def test_prediction_can_fallback_to_structural_pattern_memory(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        state.activation_index = {}
        state.actor_action_effect_counts = {}
        state.action_effect_counts = {}
        state.actor_action_context_effect_counts = {}
        state.action_context_effect_counts = {}

        result = predict_next_effect(
            state,
            PredictionQuery(actor="unknown_animal", action="unknown_move", context_tags=["animal", "movement"]),
        )

        self.assertEqual(result.predicted_effects, ["fatigue_up"])
        self.assertGreater(result.score, 0)
        self.assertTrue(any(path[0].startswith("structural:") for path in result.supporting_paths))

    def test_structure_delta_is_stored_between_structural_patterns(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        delta_id = (
            "delta:structural:entity->process->state:animal|movement"
            "=>structural:entity->process->state:animal|recovery"
        )
        delta = state.structure_deltas.get(delta_id)
        self.assertIsNotNone(delta)
        assert delta is not None
        self.assertIn("REMOVE_ACTION:run", delta.operations)
        self.assertIn("ADD_ACTION:rest", delta.operations)
        self.assertIn("REMOVE_EFFECT:fatigue_up", delta.operations)
        self.assertIn("ADD_EFFECT:fatigue_down", delta.operations)

    def test_training_records_local_prediction_validation_history(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        bucket = state.prediction_validation_stats.get("action_context:run:animal|movement")
        self.assertIsNotNone(bucket)
        assert bucket is not None
        self.assertGreater(bucket["total"], 0)
        self.assertGreater(bucket["correct"], 0)
        effect_bucket = state.prediction_validation_stats.get(
            "action_context_effect:run:animal|movement:fatigue_up"
        )
        self.assertIsNotNone(effect_bucket)

    def test_prediction_uses_validation_history_in_explanation(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        result = predict_next_effect(state, PredictionQuery(actor="dog", action="run"))

        self.assertEqual(result.predicted_effects, ["fatigue_up"])
        self.assertIn("prediction-validation history", result.explanation)

    def test_pattern_and_structural_pattern_receive_validation_score(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        pattern = state.patterns.get("pattern:run->fatigue_up")
        structural_pattern = state.structural_patterns.get("structural:entity->process->state:animal|movement")
        self.assertIsNotNone(pattern)
        self.assertIsNotNone(structural_pattern)
        assert pattern is not None
        assert structural_pattern is not None
        self.assertGreaterEqual(pattern.validation_score, 0.5)
        self.assertGreaterEqual(structural_pattern.validation_score, 0.5)

    def test_mispredicted_effect_builds_competition_history(self) -> None:
        state = RisaState()
        events = [
            Event(
                id="e001",
                timestamp=1,
                actor="dog",
                action="run",
                observed_effects=["fatigue_up"],
                context_tags=["animal", "movement"],
            ),
            Event(
                id="e002",
                timestamp=2,
                actor="human",
                action="run",
                observed_effects=["fatigue_up"],
                context_tags=["animal", "movement"],
            ),
            Event(
                id="e003",
                timestamp=3,
                actor="horse",
                action="run",
                observed_effects=["thirst_down"],
                context_tags=["animal", "movement"],
            ),
        ]
        train_events(state, events)

        competition_bucket = state.prediction_competition_stats.get(
            "action_context_competition:run:animal|movement:fatigue_up"
        )
        self.assertIsNotNone(competition_bucket)
        assert competition_bucket is not None
        self.assertGreaterEqual(competition_bucket.get("thirst_down", 0), 1)

    def test_prediction_exposes_competition_inhibition_path_when_present(self) -> None:
        state = RisaState()
        events = [
            Event(
                id="e001",
                timestamp=1,
                actor="dog",
                action="run",
                observed_effects=["fatigue_up"],
                context_tags=["animal", "movement"],
            ),
            Event(
                id="e002",
                timestamp=2,
                actor="human",
                action="run",
                observed_effects=["fatigue_up"],
                context_tags=["animal", "movement"],
            ),
            Event(
                id="e003",
                timestamp=3,
                actor="horse",
                action="run",
                observed_effects=["thirst_down"],
                context_tags=["animal", "movement"],
            ),
        ]
        train_events(state, events)

        result = predict_next_effect(
            state,
            PredictionQuery(actor="horse", action="run", context_tags=["animal", "movement"]),
        )

        self.assertEqual(result.predicted_effects, ["thirst_down"])
        self.assertIn("competition inhibition", result.explanation)
        self.assertTrue(any("competition_inhibits" in path for path in result.supporting_paths))

    def test_repeated_observations_stabilize_action_effect_relation(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        edge = state.graph.edges_by_key.get(("process:run", "state:fatigue_up", "affects"))
        self.assertIsNotNone(edge)
        assert edge is not None
        self.assertGreater(edge.reliability, 0.0)
        self.assertLess(edge.plasticity, 1.0)

        result = predict_next_effect(state, PredictionQuery(actor="dog", action="run"))
        self.assertIn("reproducibility plasticity", result.explanation)
        self.assertTrue(any("reproducibly_affects" in path for path in result.supporting_paths))

    def test_repeated_transition_is_extracted_as_structural_primitive(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        primitive_id = "primitive:transition:entity->process->state:run->fatigue_up"
        primitive = state.structural_primitives.get(primitive_id)
        self.assertIsNotNone(primitive)
        assert primitive is not None
        self.assertEqual(primitive.relation_type, "transition")
        self.assertIn("process:run", primitive.input_conditions)
        self.assertEqual(primitive.output_state, "fatigue_up")
        self.assertGreaterEqual(primitive.support, 3)
        self.assertIn(primitive_id, state.event_primitive_ids["e001"])
        self.assertTrue(primitive.adopted)
        self.assertGreater(primitive.reuse_score, 0.9)
        self.assertGreater(primitive.compression_proxy, 0.0)

        one_shot = state.structural_primitives[
            "primitive:transition:entity->process->state:drink->thirst_down"
        ]
        self.assertFalse(one_shot.adopted)

        restored = RisaState.from_dict(state.to_dict())
        self.assertIn(primitive_id, restored.structural_primitives)
        self.assertIn(primitive_id, restored.event_primitive_ids["e001"])
        self.assertTrue(restored.structural_primitives[primitive_id].adopted)

        result = predict_next_effect(state, PredictionQuery(actor="dog", action="run"))
        self.assertIn("structural primitives", result.explanation)
        self.assertTrue(any(path[0] == primitive_id and "composes_to" in path for path in result.supporting_paths))

    def test_composer_finds_local_sequence_of_adopted_primitives(self) -> None:
        state = RisaState()
        events = [
            Event("e001", 1, "dog", "run", observed_effects=["fatigue_up"], context_tags=["animal", "sequence"]),
            Event("e002", 2, "dog", "rest", observed_effects=["fatigue_down"], context_tags=["animal", "sequence"]),
            Event("e003", 3, "horse", "run", observed_effects=["fatigue_up"], context_tags=["animal", "sequence"]),
            Event("e004", 4, "horse", "rest", observed_effects=["fatigue_down"], context_tags=["animal", "sequence"]),
        ]
        train_events(state, events)

        result = compose_to_effect(
            state,
            start_action="run",
            target_effect="fatigue_down",
            context_tags=["animal", "sequence"],
            max_steps=2,
        )

        self.assertEqual(result.target_effect, "fatigue_down")
        self.assertEqual(len(result.primitive_ids), 2)
        self.assertEqual(
            result.primitive_ids[0],
            "primitive:transition:entity->process->state:run->fatigue_up",
        )
        self.assertEqual(
            result.primitive_ids[1],
            "primitive:transition:entity->process->state:rest->fatigue_down",
        )
        self.assertGreater(result.score, 0.0)
        self.assertTrue(any("precedes" in path for path in result.supporting_paths))

    def test_composer_respects_state_preconditions(self) -> None:
        state = RisaState()
        events = [
            Event(
                "e001",
                1,
                "dog",
                "run",
                preconditions=["rested"],
                observed_effects=["fatigue_up"],
                context_tags=["animal", "sequence"],
            ),
            Event(
                "e002",
                2,
                "dog",
                "rest",
                preconditions=["fatigue_up"],
                observed_effects=["fatigue_down"],
                context_tags=["animal", "sequence"],
            ),
            Event(
                "e003",
                3,
                "horse",
                "run",
                preconditions=["rested"],
                observed_effects=["fatigue_up"],
                context_tags=["animal", "sequence"],
            ),
            Event(
                "e004",
                4,
                "horse",
                "rest",
                preconditions=["fatigue_up"],
                observed_effects=["fatigue_down"],
                context_tags=["animal", "sequence"],
            ),
        ]
        train_events(state, events)

        blocked = compose_to_effect(
            state,
            start_action="run",
            target_effect="fatigue_down",
            context_tags=["animal", "sequence"],
            start_states=["fatigue_up"],
            max_steps=2,
        )
        self.assertEqual(blocked.primitive_ids, [])

        result = compose_to_effect(
            state,
            start_action="run",
            target_effect="fatigue_down",
            context_tags=["animal", "sequence"],
            start_states=["rested"],
            max_steps=2,
        )
        self.assertEqual(len(result.primitive_ids), 2)
        self.assertIn("state:rested", state.structural_primitives[result.primitive_ids[0]].input_state_conditions)
        self.assertIn("state:fatigue_up", state.structural_primitives[result.primitive_ids[1]].input_state_conditions)

    def test_forecast_returns_multiple_state_compatible_effects(self) -> None:
        state = RisaState()
        events = [
            Event("e001", 1, "dog", "touch", preconditions=["charged"], observed_effects=["warm"], context_tags=["warm"]),
            Event("e002", 2, "dog", "touch", preconditions=["charged"], observed_effects=["warm"], context_tags=["warm"]),
            Event("e003", 3, "horse", "touch", preconditions=["charged"], observed_effects=["spark"], context_tags=["spark"]),
            Event("e004", 4, "horse", "touch", preconditions=["charged"], observed_effects=["spark"], context_tags=["spark"]),
        ]
        train_events(state, events)

        candidates = forecast_next_effects(
            state,
            action="touch",
            current_states=["charged"],
            max_candidates=3,
        )

        self.assertEqual({candidate.target_effect for candidate in candidates}, {"spark", "warm"})
        self.assertTrue(all(candidate.score > 0.0 for candidate in candidates))
        self.assertTrue(all("state:charged" in candidate.supporting_paths[0] for candidate in candidates))

        blocked = forecast_next_effects(state, action="touch", current_states=["uncharged"])
        self.assertEqual(blocked, [])


if __name__ == "__main__":
    unittest.main()
