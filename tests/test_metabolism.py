import unittest

from risa.core.models import Edge, Node
from risa.core.state import RisaState
from risa.engine.metabolism import activate_nodes, decay_nodes


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


if __name__ == "__main__":
    unittest.main()
