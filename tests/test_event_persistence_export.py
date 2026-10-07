from dataclasses import fields

from risa.core.models import Event, StateVariableSpec
from risa.core.state import _EVENT_PERSISTENCE_DEFAULTS, _event_persistence_record


def legacy(event):
    record = event.to_dict()
    record.pop('id', None)
    return {key: value for key, value in record.items()
            if key not in _EVENT_PERSISTENCE_DEFAULTS or value != _EVENT_PERSISTENCE_DEFAULTS[key]}


def test_all_event_fields_and_nested_data_match_legacy_export():
    event = Event(id='e', timestamp=1, actor='ロボット', action='charge', target='站',
                  preconditions=['ready'], consumed_states=['empty'], state_group_updates={'power': 'full'},
                  numeric_preconditions={'power': 0.5}, state_variable_deltas={'power': 2.5},
                  state_variable_specs={'power': StateVariableSpec('J', 0, 100)},
                  observed_effects=['full'], context_tags=['inside'], episode_id='ep', source='test',
                  actor_roles=['worker'], target_roles=['station'], entity_bindings={'x': 'robot'},
                  entity_role_bindings={'x': ['worker']}, entity_relations=[{'source': 'x', 'target': 'y'}],
                  entity_relations_observed=True, observed_states_before=['empty'],
                  before_state_observed=True, transition_succeeded=False)
    exported = _event_persistence_record(event)
    assert exported == legacy(event)
    assert set(exported) == {item.name for item in fields(Event)} - {'id'}
    exported['entity_role_bindings']['x'].append('changed')
    exported['entity_relations'][0]['target'] = 'changed'
    exported['state_variable_specs']['power']['unit'] = 'changed'
    assert event.entity_role_bindings == {'x': ['worker']}
    assert event.entity_relations[0]['target'] == 'y'
    assert event.state_variable_specs['power'].unit == 'J'


def test_defaults_are_omitted_without_changing_public_export():
    event = Event('e', 1, 'robot', 'charge')
    assert _event_persistence_record(event) == legacy(event)
    assert len(event.to_dict()) == len(fields(Event))


def test_custom_event_export_is_preserved():
    class CustomEvent(Event):
        def to_dict(self):
            return {**super().to_dict(), 'custom': ['value']}
    event = CustomEvent('e', 1, 'robot', 'charge')
    assert _event_persistence_record(event) == legacy(event)
