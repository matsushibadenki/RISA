from experiments.independent_joint_quality import training_episode, heldout_cases
from risa.core.models import Event, StructuralPrimitive
from risa.core.state import RisaState
from risa.engine.runtime import train_events, TrainingOptions
from risa.engine.composer import compose_to_effect, _primitive_actor_binding_matches, _primitive_target_role_matches
from risa.engine.primitive_grounding import build_primitive_grounding, invalidate_primitive_grounding


def test_index_is_exact_after_append_reload_and_removes_query_event_reads():
    state = RisaState()
    for start, end in ((0, 4), (4, 8)):
        train_events(state, [e for i in range(start, end) for e in training_episode(419, i)],
                     TrainingOptions(enable_metabolism=False, enable_replay=False))
        assert getattr(state, '_primitive_grounding_index', None) is None
        index = build_primitive_grounding(state)
        assert index['build_event_reads'] > 0
        restored = RisaState.from_dict(state.to_dict())
        for case in heldout_cases(419, 'read-model-test', 10):
            kwargs = dict(actor=case['actor'], target=case['target'], actor_roles=case['actor_roles'],
                target_roles=case['target_roles'], start_states=case['states'], start_variables={'energy': case['energy']}, max_steps=2)
            full = compose_to_effect(state, 'prime', 'done', **kwargs)
            diagnostic = {}
            indexed = compose_to_effect(state, 'prime', 'done', **kwargs, use_grounding_index=True, search_diagnostics=diagnostic)
            assert indexed == full == compose_to_effect(restored, 'prime', 'done', **kwargs, use_grounding_index=True)
            assert diagnostic['grounding_event_reads'] == diagnostic['index_build_event_reads'] == 0


def test_joint_roles_equality_missing_targets_and_untyped_rows_remain_exact():
    state = RisaState()
    events = [Event(id='first', timestamp=1, actor='a', action='go', target='b', actor_roles=['controller'], target_roles=['remote']),
              Event(id='second', timestamp=2, actor='c', action='go', target='c', actor_roles=['observer'], target_roles=['self']),
              Event(id='untyped', timestamp=3, actor='u', action='go', target=None)]
    state.events_by_id = {e.id: e for e in events}
    primitive = StructuralPrimitive(id='mixed', relation_type='transition', role_signature='mixed', evidence_event_ids=set(state.events_by_id))
    state.structural_primitives[primitive.id] = primitive
    build_primitive_grounding(state)
    for ar in ([], ['controller'], ['observer'], ['controller', 'observer']):
        for tr in ([], ['remote'], ['self'], ['unknown']):
            for actor, target in ((None, None), ('x', 'y'), ('x', 'x'), ('x', None)):
                assert _primitive_actor_binding_matches(state, primitive, ar, actor, target, tr) == _primitive_actor_binding_matches(state, primitive, ar, actor, target, tr, indexed=True)
            assert _primitive_target_role_matches(state, primitive, tr) == _primitive_target_role_matches(state, primitive, tr, indexed=True)
    # Explicit direct correction requires invalidation, just like any derived read model.
    state.events_by_id['first'].actor_roles = ['revised']
    invalidate_primitive_grounding(state)
    assert _primitive_actor_binding_matches(state, primitive, ['controller'], 'x', 'y', ['remote'], indexed=True) is False
