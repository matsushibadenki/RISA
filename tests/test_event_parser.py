import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from risa.engine.event_parser import parse_events


class EventParserTests(unittest.TestCase):
    def test_parse_events_from_json_array(self) -> None:
        events = parse_events(Path("data/toy_world.json"))
        self.assertEqual(len(events), 5)
        self.assertEqual(events[0].actor, "dog")
        self.assertEqual(events[0].observed_effects, ["fatigue_up"])

    def test_parse_optional_state_preconditions(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.json"
            path.write_text(
                '[{"id":"e001","timestamp":1,"actor":"dog","action":"rest",'
                '"preconditions":["fatigue_up"],"observed_effects":["fatigue_down"]}]',
                encoding="utf-8",
            )
            events = parse_events(path)

        self.assertEqual(events[0].preconditions, ["fatigue_up"])


if __name__ == "__main__":
    unittest.main()
