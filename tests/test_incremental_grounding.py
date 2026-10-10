from copy import deepcopy

from experiments.compositional_holdout import training_episode, heldout_cases
from experiments.compositional_grounding_costs import _query
from risa.core.models import Event, StructuralPrimitive, StructuralAdaptationCandidate
from risa.core.state import RisaState
from risa.engine.runtime import train_events, TrainingOptions
from risa.engine.primitive_grounding import build_primitive_grounding, invalidate_primitive_grounding
from risa.engine.composer import _primitive_actor_binding_matches, _primitive_target_role_matches
from risa.engine.graph_builder import ingest_event


def test_incremental_append_idempotence_reload_and_full_result_equality():
    state = RisaState()
    index = build_primitive_grounding(state, incremental=True)
    options = TrainingOptions(enable_metabolism=False, enable_replay=False)
    for i in range(16):
        events = training_episode(701, 'coupled', i)
        train_events(state, events, options)
        assert state._primitive_grounding_index is index
        assert index['update_event_reads'] == 3 * (i + 1)
        train_events(state, events, options)
        assert index['update_event_reads'] == 3 * (i + 1)
        for case in heldout_cases(701, 'coupled'):
            for enabled in (False, True):
                assert _query(state, case, enabled, False) == _query(state, case, enabled, True)
    restored = RisaState.from_dict(deepcopy(state.to_dict()))
    assert getattr(restored, '_primitive_grounding_index', None) is None
    build_primitive_grounding(restored, incremental=True)
    for case in heldout_cases(701, 'coupled'):
        assert _query(state, case, True, False) == _query(restored, case, True, True)


def test_diverse_joint_witnesses_corrections_and_replacement():
    state = RisaState()
    build_primitive_grounding(state, incremental=True)
    for i in range(24):
        event = Event(id=str(i), timestamp=i, actor=f'a{i}', target=f'b{i}', action='go',
            actor_roles=[f'operator{i}'], target_roles=[f'unit{i}'], observed_effects=['done'], source=str(i % 2))
        train_events(state, [event], TrainingOptions(enable_metabolism=False, enable_replay=False))
    primitive = next(iter(state.structural_primitives.values()))
    for i in range(24):
        for j in range(24):
            args = (state, primitive, [f'operator{i}'], 'new-a', 'new-b', [f'unit{j}'])
            assert _primitive_actor_binding_matches(*args, indexed=True) == (i == j)
            assert _primitive_actor_binding_matches(*args) == (i == j)
    # Direct mutation requires explicit invalidation; ingestion replacement is automatic.
    state.events_by_id['0'].actor = state.events_by_id['0'].target
    invalidate_primitive_grounding(state)
    build_primitive_grounding(state, incremental=True)
    assert _primitive_actor_binding_matches(state, primitive, ['operator0'], 'same', 'same', ['unit0'], indexed=True)
    ingest_event(state, deepcopy(state.events_by_id['1']))
    assert state._primitive_grounding_index is None
    build_primitive_grounding(state, incremental=True)
    replacement = deepcopy(primitive)
    replacement.evidence_event_ids = {'2'}
    state.structural_primitives[primitive.id] = replacement
    assert not _primitive_actor_binding_matches(state, replacement, ['operator0'], 'a', 'b', ['unit0'], indexed=True)


def test_split_new_primitives_rebuild_and_missing_evidence_arrival():
    from risa.engine.adaptation import _execute_context_split
    state = RisaState()
    events = [Event(id=str(i), timestamp=i, actor=f'a{i}', target=f'b{i}', action='go',
        actor_roles=['operator'], target_roles=['unit'], context_tags=[str(i % 2)],
        observed_effects=['done']) for i in range(8)]
    train_events(state, events, TrainingOptions(enable_metabolism=False, enable_replay=False, enable_adaptation=False))
    primitive = next(iter(state.structural_primitives.values()))
    build_primitive_grounding(state, incremental=True)
    # Use the real context split operation, then compare each new evidence subset.
    candidate = StructuralAdaptationCandidate(primitive_id=primitive.id,
        reason='context regression', proposed_operation='SPLIT_CONTEXT', pressure=1.0)
    _execute_context_split(state, candidate)
    assert candidate.status == 'executed'
    for p in state.structural_primitives.values():
        assert _primitive_target_role_matches(state, p, ['unit']) == _primitive_target_role_matches(state, p, ['unit'], indexed=True)
    primitive.evidence_event_ids.add('missing')
    build_primitive_grounding(state, incremental=True)
    ingest_event(state, Event(id='missing', timestamp=100, actor='x', action='go', target='y', target_roles=['new']))
    assert state._primitive_grounding_index is None
    assert _primitive_target_role_matches(state, primitive, ['new'], indexed=True)


def test_three_arm_measurement_counts_update_work_and_saved_equivalence():
    from experiments.incremental_grounding_evaluation import run
    result = run(dict(seeds=[701], worlds=['independent'], event_batches=[24],
                      queries_per_update=[1], repetitions=1))
    row = result['rows'][0]
    assert row['mismatches'] == 0 and row['complete_comparisons'] == 4
    assert row['stats']['incremental']['update_reads'] == 96
    assert row['stats']['incremental']['build_reads'] == 0
    assert row['stats']['rebuild']['build_reads'] == 240
    assert row['saved_bytes'] > 0


def test_append_reuses_witness_storage_and_exports_canonical_summary():
    from risa.engine.primitive_grounding import grounding_payload_bytes
    state = RisaState()
    index = build_primitive_grounding(state, incremental=True)
    options = TrainingOptions(enable_metabolism=False, enable_replay=False)
    train_events(state, training_episode(701, 'coupled', 0), options)
    storage = {key: entry['rows'] for key, entry in index['entries'].items()}
    for i in range(1, 8):
        train_events(state, training_episode(701, 'coupled', i), options)
    for key, rows in storage.items():
        assert index['entries'][key]['rows'] is rows
    assert index['signature_count'] == sum(len(e['rows']) for e in index['entries'].values())
    size = grounding_payload_bytes(index)
    rebuilt = build_primitive_grounding(state, incremental=True)
    assert grounding_payload_bytes(rebuilt) == size
    assert rebuilt['entries'] == index['entries']


def test_diversity_measurement_parity():
    from experiments.grounding_diversity_evaluation import run
    result = run(diversities=(4,), densities=(2,), repetitions=1, updates=4)
    assert len(result['rows']) == 2
    assert all(row['mismatches'] == 0 and row['saved_bytes'] > 0 for row in result['rows'])


def test_diversity_fixture_has_positive_and_joint_identity_negatives():
    from experiments.grounding_diversity_evaluation import event, query
    for shape in ('roles', 'shared_actor'):
        state = RisaState()
        train_events(state, [event(i, 8, shape) for i in range(8)],
                     TrainingOptions(enable_metabolism=False, enable_replay=False))
        for indexed in (False, True):
            assert query(state, 0, 8, shape, indexed, 0).primitive_ids
            assert not query(state, 0, 8, shape, indexed, 1).primitive_ids
            assert not query(state, 0, 8, shape, indexed, 2).primitive_ids
