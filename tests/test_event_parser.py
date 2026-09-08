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

    def test_parse_typed_actor_and_target_roles(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.json"
            path.write_text(
                '[{"id":"e-role","timestamp":1,"actor":"robot","action":"inspect",'
                '"target":"heater","actor_roles":["inspector"],'
                '"target_roles":["heating_device"],"observed_effects":["warm"]}]',
                encoding="utf-8",
            )
            events = parse_events(path)

        self.assertEqual(events[0].actor_roles, ["inspector"])
        self.assertEqual(events[0].target_roles, ["heating_device"])

    def test_parse_failed_transition_with_complete_empty_before_state(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.json"
            path.write_text(
                '[{"id":"failed","timestamp":1,"actor":"robot","action":"open",'
                '"observed_states_before":[],"transition_succeeded":false,'
                '"observed_effects":[]}]',
                encoding="utf-8",
            )
            events = parse_events(path)

        self.assertFalse(events[0].transition_succeeded)
        self.assertTrue(events[0].before_state_observed)


if __name__ == "__main__":
    unittest.main()
