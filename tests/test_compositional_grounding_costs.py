import json
from pathlib import Path

from experiments.compositional_grounding_costs import run_cost_audit
from risa.core.models import Event, StructuralPrimitive
from risa.core.state import RisaState
from risa.engine.composer import _primitive_actor_binding_matches, _primitive_target_role_matches
from risa.engine.primitive_grounding import build_primitive_grounding, invalidate_primitive_grounding
from risa.engine.role_induction import effective_event_actor_roles, effective_event_target_roles


def test_compositional_append_save_load_and_cold_cost_contract(tmp_path):
    fixture = json.loads(Path('experiments/g3_compositional_holdout_manifest.json').read_text())
    fixture.update(seeds=[701], training_episode_checkpoints=[8, 16])
    fixture_path = tmp_path / 'fixture.json'
    fixture_path.write_text(json.dumps(fixture))
    result = run_cost_audit(dict(fixture_manifest=str(fixture_path), repetitions=2))
    assert result['paired_order_balanced']
    assert len(result['rows']) == 4
    for row in result['rows']:
        assert row['correct'] == row['queries'] == 40
        assert row['false_accepts'] == row['complete_result_mismatches'] == row['reload_mismatches'] == 0
        assert row['work']['reference']['grounding_event_reads'] > 0
        assert row['work']['indexed']['grounding_event_reads'] == 0
        assert row['work']['indexed']['index_build_event_reads'] == 0
        assert row['cold_work']['index_build_event_reads'] == row['events']
        assert row['index_build_event_reads'] == row['events']
        assert row['persisted_extra_bytes'] == 0
        assert len(set(row['persisted_file_bytes'])) == 1
        assert row['index_traced_peak_bytes'] >= row['index_traced_retained_bytes'] > 0
        assert all(len(samples) == 2 for samples in row['timing_samples'].values())


def test_induced_roles_wildcards_normalization_and_direct_rebuild():
    events = [
        Event(id='induced', timestamp=1, action='go', actor='agent', target='device',
              entity_bindings={'actor': 'agent', 'target': 'device'},
              entity_relations=[{'source': 'actor', 'relation': 'controls', 'target': 'target'}]),
        Event(id='wildcard', timestamp=2, action='go', actor=' A ', target=None,
              actor_roles=[' Operator ']),
        Event(id='normalized', timestamp=3, action='go', actor=' X ', target='x',
              actor_roles=[' Observer '], target_roles=[' Unit ']),
    ]
    state = RisaState()
    state.events_by_id = {e.id: e for e in events}
    primitive = StructuralPrimitive(id='roles', relation_type='transition', role_signature='joint',
                                    evidence_event_ids={e.id for e in events} | {'missing'})
    state.structural_primitives[primitive.id] = primitive
    induced_ar = effective_event_actor_roles(events[0])
    induced_tr = effective_event_target_roles(events[0])
    assert induced_ar and induced_tr
    build_primitive_grounding(state)
    for actor_roles in ([], [' Operator '], ['observer'], induced_ar):
        for target_roles in ([], [' Unit '], ['unknown'], induced_tr):
            for actor, target in ((None, None), ('x', 'y'), (' X ', 'x'), ('x', None)):
                full = _primitive_actor_binding_matches(state, primitive, actor_roles, actor, target, target_roles)
                assert full == _primitive_actor_binding_matches(state, primitive, actor_roles, actor, target, target_roles, indexed=True)
            assert _primitive_target_role_matches(state, primitive, target_roles) == _primitive_target_role_matches(
                state, primitive, target_roles, indexed=True)
    # Direct source edits are outside train_events' immutable-ID contract.
    # Explicit invalidation must handle same-size support replacement as well.
    primitive.evidence_event_ids.remove('normalized')
    primitive.evidence_event_ids.add('other-missing')
    invalidate_primitive_grounding(state)
    assert not _primitive_actor_binding_matches(state, primitive, ['observer'], 'x', 'x', ['unit'], indexed=True)
