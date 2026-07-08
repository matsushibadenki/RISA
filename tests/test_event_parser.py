import unittest
from pathlib import Path

from risa.engine.event_parser import parse_events


class EventParserTests(unittest.TestCase):
    def test_parse_events_from_json_array(self) -> None:
        events = parse_events(Path("data/toy_world.json"))
        self.assertEqual(len(events), 5)
        self.assertEqual(events[0].actor, "dog")
        self.assertEqual(events[0].observed_effects, ["fatigue_up"])


if __name__ == "__main__":
    unittest.main()
