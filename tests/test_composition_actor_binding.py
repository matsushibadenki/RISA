from experiments.temporal_candidate_evaluation import _training_state, _cases
from risa.engine.composer import compose_to_effect, _primitive_actor_binding_matches
from risa.core.models import Event, StructuralPrimitive
from risa.core.state import RisaState


def test_actor_binding_rejects_wrong_roles_and_self_binding_without_candidates():
    state = _training_state(29, True)
    for case in _cases(29, 'binding-regression', 40, True):
        for enabled in (True, False):
            result = compose_to_effect(state, 'charge', 'online',
                actor=case['actor'], target=case['target'], actor_roles=case['actor_roles'],
                target_roles=case['target_roles'], start_states=case['states'],
                start_variables=case['variables'], max_steps=2, enable_candidate_concepts=enabled)
            assert bool(result.primitive_ids) == case['expected']
    assert not compose_to_effect(state, 'charge', 'online', target='device',
        target_roles=['powered_device'], start_states=['connected'],
        start_variables={'energy': 2}, max_steps=2, enable_candidate_concepts=False).primitive_ids
    assert compose_to_effect(state, 'charge', 'online', start_states=['connected'],
                             start_variables={'energy': 2}, max_steps=2).primitive_ids


def test_actor_and_target_roles_require_one_joint_witness():
    state = RisaState()
    state.events_by_id = {
        'a': Event(id='a', timestamp=1, actor='control-a', action='go', target='device-a',
                   actor_roles=['controller'], target_roles=['powered']),
        'b': Event(id='b', timestamp=2, actor='watch-b', action='go', target='heater-b',
                   actor_roles=['observer'], target_roles=['heater']),
    }
    primitive = StructuralPrimitive(id='joint', relation_type='transition', role_signature='joint',
                                    evidence_event_ids={'a', 'b'})
    assert _primitive_actor_binding_matches(state, primitive, ['controller'], 'new-control', 'new-device', ['powered'])
    assert not _primitive_actor_binding_matches(state, primitive, ['controller'], 'new-control', 'new-heater', ['heater'])
    assert not _primitive_actor_binding_matches(state, primitive, ['controller'], 'same', 'same', ['powered'])
    state.events_by_id['a'].actor = state.events_by_id['a'].target
    assert _primitive_actor_binding_matches(state, primitive, ['controller'], 'same', 'same', ['powered'])
    assert not _primitive_actor_binding_matches(state, primitive, ['controller'], 'actor', 'target', ['powered'])
