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

    def test_parse_arbitrary_typed_entities_and_relations(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.json"
            path.write_text(
                '[{"id":"rel","timestamp":1,"actor":"robot","action":"unlock",'
                '"observed_effects":["open"],'
                '"entity_bindings":{"operator":"robot","door":"door-a","key":"key-a"},'
                '"entity_role_bindings":{"operator":["controller"],"door":["lockable"],'
                '"key":["credential"]},'
                '"entity_relations":[{"source":"operator","relation":"holds",'
                '"target":"key"},{"source":"key","relation":"opens","target":"door"}]}]',
                encoding="utf-8",
            )
            event = parse_events(path)[0]

        self.assertEqual(event.entity_bindings["key"], "key-a")
        self.assertEqual(event.entity_role_bindings["door"], ["lockable"])
        self.assertEqual(event.entity_relations[1]["relation"], "opens")
        self.assertTrue(event.entity_relations_observed)

    def test_explicit_empty_entity_relation_observation_is_preserved(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.json"
            path.write_text(
                '[{"id":"no-rel","timestamp":1,"actor":"robot","action":"wait",'
                '"observed_effects":[],"transition_succeeded":false,'
                '"entity_bindings":{"operator":"robot","door":"door-a"},'
                '"entity_role_bindings":{"operator":["controller"],'
                '"door":["lockable"]},"entity_relations":[]}]',
                encoding="utf-8",
            )
            event = parse_events(path)[0]

        self.assertEqual(event.entity_relations, [])
        self.assertTrue(event.entity_relations_observed)

    def test_entity_relation_rejects_an_unknown_variable(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.json"
            path.write_text(
                '[{"id":"bad-rel","timestamp":1,"actor":"robot","action":"unlock",'
                '"observed_effects":["open"],"entity_bindings":{"door":"door-a"},'
                '"entity_relations":[{"source":"missing","relation":"opens",'
                '"target":"door"}]}]',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unknown variables: missing"):
                parse_events(path)


if __name__ == "__main__":
    unittest.main()
