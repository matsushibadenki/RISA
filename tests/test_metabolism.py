import unittest

from risa.core.models import Node
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


if __name__ == "__main__":
    unittest.main()
