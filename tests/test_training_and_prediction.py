import unittest

from risa.core.models import PredictionQuery
from risa.core.state import RisaState
from risa.engine.abstractor import rebuild_concepts
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


if __name__ == "__main__":
    unittest.main()
