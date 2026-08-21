import unittest

from risa.core.models import Edge, Node
from risa.core.state import RisaState
from risa.engine.metabolism import (
    activate_nodes,
    apply_competition_inhibition,
    apply_prediction_outcome_plasticity,
    decay_nodes,
    reinforce_coactivation,
    reinforce_reproducible_relation,
)


class MetabolismTests(unittest.TestCase):
    def test_node_becomes_dormant_after_long_inactivity(self) -> None:
        state = RisaState()
        state.graph.add_or_update_node(
            Node(
                id="state:unused",
                kind="state",
                label="unused",
                created_at=1,
                energy=0.2,
                recent_activity=0.2,
            )
        )

        decay_nodes(state, current_timestamp=100, dormancy_idle_threshold=10)

        node = state.graph.get_node("state:unused")
        self.assertIsNotNone(node)
        self.assertTrue(node.dormant)
        self.assertLessEqual(node.energy, 0.12)

    def test_activation_revives_dormant_node(self) -> None:
        state = RisaState()
        state.graph.add_or_update_node(
            Node(
                id="state:fatigue_up",
                kind="state",
                label="fatigue_up",
                created_at=1,
                energy=0.0,
                recent_activity=0.0,
                dormant=True,
            )
        )

        activate_nodes(state, ["state:fatigue_up"], timestamp=5)

        node = state.graph.get_node("state:fatigue_up")
        self.assertIsNotNone(node)
        self.assertFalse(node.dormant)
        self.assertGreater(node.energy, 0.0)
        self.assertGreater(node.recent_activity, 0.0)

    def test_connection_cost_reduces_energy_faster(self) -> None:
        state = RisaState()
        state.graph.add_or_update_node(
            Node(
                id="concept:shared_run_fatigue_up",
                kind="concept",
                label="shared_run_fatigue_up",
                created_at=1,
                energy=0.5,
                recent_activity=1.0,
            )
        )
        for index in range(5):
            neighbor_id = f"entity:neighbor_{index}"
            state.graph.add_or_update_node(Node(id=neighbor_id, kind="entity", label=neighbor_id, created_at=1))
            state.graph.add_or_update_edge(
                Edge(
                    source="concept:shared_run_fatigue_up",
                    target=neighbor_id,
                    relation_type="instance_of",
                    evidence_count=1,
                )
            )

        decay_nodes(state, current_timestamp=20, dormancy_idle_threshold=5)

        node = state.graph.get_node("concept:shared_run_fatigue_up")
        self.assertIsNotNone(node)
        self.assertLess(node.energy, 0.2)

    def test_coactivation_reinforcement_strengthens_pair_usage(self) -> None:
        state = RisaState()
        state.graph.add_or_update_node(Node(id="entity:dog", kind="entity", label="dog", created_at=1))
        state.graph.add_or_update_node(Node(id="process:run", kind="process", label="run", created_at=1))

        reinforce_coactivation(state, ["entity:dog", "process:run"], timestamp=5)
        reinforce_coactivation(state, ["entity:dog", "process:run"], timestamp=6)

        edge = state.graph.edges_by_key.get(("entity:dog", "process:run", "co_activates_with"))
        self.assertIsNotNone(edge)
        assert edge is not None
        self.assertGreaterEqual(edge.evidence_count, 2)
        self.assertGreater(edge.reliability, 0.08)
        self.assertLess(edge.plasticity, 0.97)

    def test_competition_inhibition_weakens_loser_and_strengthens_winner(self) -> None:
        state = RisaState()
        state.graph.add_or_update_node(Node(id="process:run", kind="process", label="run", created_at=1))
        state.graph.add_or_update_node(Node(id="state:fatigue_up", kind="state", label="fatigue_up", created_at=1))
        state.graph.add_or_update_node(Node(id="state:thirst_down", kind="state", label="thirst_down", created_at=1))
        state.graph.add_or_update_edge(
            Edge(
                source="process:run",
                target="state:fatigue_up",
                relation_type="co_activates_with",
                reliability=0.5,
                plasticity=0.2,
                evidence_count=1,
                last_updated=1,
            )
        )
        state.graph.add_or_update_edge(
            Edge(
                source="process:run",
                target="state:thirst_down",
                relation_type="co_activates_with",
                reliability=0.2,
                plasticity=0.5,
                evidence_count=1,
                last_updated=1,
            )
        )

        apply_competition_inhibition(
            state,
            action_id="process:run",
            losing_effect_id="state:fatigue_up",
            winning_effect_ids=["state:thirst_down"],
            timestamp=3,
        )

        loser = state.graph.edges_by_key.get(("process:run", "state:fatigue_up", "co_activates_with"))
        winner = state.graph.edges_by_key.get(("process:run", "state:thirst_down", "co_activates_with"))
        self.assertIsNotNone(loser)
        self.assertIsNotNone(winner)
        assert loser is not None
        assert winner is not None
        self.assertLess(loser.reliability, 0.5)
        self.assertGreater(loser.plasticity, 0.2)
        self.assertGreater(winner.reliability, 0.2)
        self.assertLess(winner.plasticity, 0.5)

    def test_reproducible_relation_stabilizes_and_failed_prediction_reopens_plasticity(self) -> None:
        state = RisaState()
        state.graph.add_or_update_edge(
            Edge(
                source="process:run",
                target="state:fatigue_up",
                relation_type="affects",
                reliability=0.4,
                plasticity=0.6,
                evidence_count=1,
                last_updated=1,
            )
        )

        reinforce_reproducible_relation(
            state,
            source="process:run",
            target="state:fatigue_up",
            relation_type="affects",
            timestamp=2,
        )
        apply_prediction_outcome_plasticity(
            state,
            action_id="process:run",
            predicted_effect_id="state:fatigue_up",
            matched=True,
            timestamp=3,
        )

        edge = state.graph.edges_by_key[("process:run", "state:fatigue_up", "affects")]
        self.assertGreater(edge.reliability, 0.4)
        self.assertLess(edge.plasticity, 0.6)

        stable_reliability = edge.reliability
        stable_plasticity = edge.plasticity
        apply_prediction_outcome_plasticity(
            state,
            action_id="process:run",
            predicted_effect_id="state:fatigue_up",
            matched=False,
            timestamp=4,
        )

        self.assertLess(edge.reliability, stable_reliability)
        self.assertGreater(edge.plasticity, stable_plasticity)


if __name__ == "__main__":
    unittest.main()
