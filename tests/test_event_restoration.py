import copy

import pytest

from risa.core.state import RisaState
from experiments.references.state_before_event_restore_20261008 import RisaState as BeforeState


@pytest.mark.parametrize('version', [1, 4, 6])
def test_compact_event_restoration_preserves_values_defaults_and_input_aliases(version):
    payload = {'schema_version':version, 'events':{
        'e1': {'timestamp':1, 'actor':'ロボット', 'action':'充电', 'observed_effects':['ready'],
               'numeric_preconditions':{'power':.5}, 'entity_role_bindings':{'x':['worker']}},
        'e2': {'timestamp':2, 'actor':'robot', 'action':'wait'}}}
    snapshot = copy.deepcopy(payload)
    state, reference = RisaState.from_dict(payload), BeforeState.from_dict(payload)
    assert state.to_dict() == reference.to_dict()
    assert payload == snapshot
    assert state.events_by_id['e1'].id == 'e1'
    assert state.events_by_id['e1'].observed_effects is payload['events']['e1']['observed_effects']
    assert state.events_by_id['e1'].state_variable_specs is not state.events_by_id['e2'].state_variable_specs
    assert state.event_order == reference.event_order
    assert state.evidence_index == reference.evidence_index


def test_explicit_ids_specs_and_pair_records_keep_legacy_conversion():
    payload = {'events':{
        'e1': {'id':'e1', 'timestamp':1, 'actor':'a', 'action':'charge',
               'state_variable_specs':{'power':{'unit':'J','minimum':0,'maximum':100}}},
        'e2': [('id','e2'), ('timestamp',2), ('actor','a'), ('action','wait')]}}
    state, reference = RisaState.from_dict(payload), BeforeState.from_dict(payload)
    assert state.to_dict() == reference.to_dict()
    assert state.events_by_id['e1'].state_variable_specs['power'].unit == 'J'


@pytest.mark.parametrize('extra', [{'unknown_field':True}, {'state_variable_specs':None},
                                  {'state_variable_specs':{'x':{'unexpected':1}}}])
def test_invalid_event_records_keep_the_same_rejection(extra):
    payload = {'events':{'e':{'timestamp':1,'actor':'a','action':'b',**extra}}}
    errors = []
    for cls in (BeforeState, RisaState):
        with pytest.raises(Exception) as result:
            cls.from_dict(payload)
        errors.append((type(result.value),str(result.value)))
    assert errors[0] == errors[1]
