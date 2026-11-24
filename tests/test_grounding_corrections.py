from copy import deepcopy
import pytest
from experiments.grounding_frequency_evaluation import event, query, OPTIONS
from risa.core.state import RisaState
from risa.engine.runtime import train_events
from risa.engine import primitive_grounding as g
from risa.engine.grounding_corrections import GroundingCorrectionTracker


def world():
    state = RisaState()
    train_events(state, [event(p,k) for p in range(4) for k in range(12)], OPTIONS)
    g.build_primitive_grounding(state, incremental=True, total_lookup_budget_bytes=3000, allocation_policy='frequency')
    return state


def check(state):
    for p in range(4):
        for k in (0,1,11):
            for v in range(3):
                assert query(state,p,k,v,True) == query(state,p,k,v,False)
    assert state._primitive_grounding_index['lookup_bytes_used'] <= 3000


def test_local_correction_and_calibration_invalidation():
    state = world()
    tracker = GroundingCorrectionTracker(state)
    before = dict(tracker.index['entries'])
    for e in before.values(): e['calibration_key'] = 'old'
    state.events_by_id['0-0'].target = 'shared'
    report = tracker.refresh(['0-0'])
    assert report['mode'] == 'partial' and report['event_reads'] == 12
    touched = set(report['affected_primitives'])
    for k,e in tracker.index['entries'].items():
        assert (e is before[k]) == (k not in touched)
        assert ('calibration_key' in e) == (k not in touched)
    check(state)
    state.events_by_id['0-0'].target = 'other0'
    assert tracker.refresh(['0-0'])['mode'] == 'partial'
    check(state)
    assert tracker.refresh([])['mode'] == 'noop'


@pytest.mark.parametrize('change,reason', [
    ('unknown','unknown_dependencies'), ('new','untracked_event'),
    ('delete','event_deleted'), ('support','primitive_or_support_changed'),
    ('replace','primitive_or_support_changed'), ('new_primitive','primitive_set_changed'),
    ('wide','wide_fanout'), ('invalidate','index_replaced'), ('missing','missing_reference_changed')])
def test_fallbacks(change, reason):
    state = world()
    primitive = next(iter(state.structural_primitives.values()))
    if change == 'missing': primitive.evidence_event_ids.add('missing')
    if change == 'missing': g.build_primitive_grounding(state, total_lookup_budget_bytes=3000)
    tracker = GroundingCorrectionTracker(state)
    ids = ['0-0']
    if change == 'new': ids=['new']
    if change == 'delete': del state.events_by_id['0-0']
    if change == 'support':
        primitive.evidence_event_ids.remove(next(iter(primitive.evidence_event_ids)))
        primitive.evidence_event_ids.add('1-0')
    if change == 'replace': state.structural_primitives[primitive.id] = deepcopy(primitive)
    if change == 'new_primitive': del state.structural_primitives[primitive.id]
    if change == 'wide': ids=[f'{p}-0' for p in range(4)]
    if change == 'invalidate': g.invalidate_primitive_grounding(state)
    if change == 'missing':
        new=event(0,99);new.id='missing';state.events_by_id['missing']=new;ids=['missing']
    report = tracker.refresh(ids, dependencies_known=change!='unknown')
    assert report['mode']=='full' and report['reason']==reason
    check(state)


def test_shared_support_rebuilds_all_dependents_and_detects_append():
    state=world()
    ps=list(state.structural_primitives.values())
    ps[1].evidence_event_ids.add('0-0')
    g.build_primitive_grounding(state, incremental=True, total_lookup_budget_bytes=3000)
    tracker=GroundingCorrectionTracker(state,max_fraction=1)
    state.events_by_id['0-0'].actor_roles=['different','joint']
    state.events_by_id['0-0'].target_roles=['new','unit']
    assert tracker.refresh(['0-0'])['rebuilt_primitives']==2
    check(state)
    train_events(state,[event(0,12)],OPTIONS)
    assert tracker.refresh(['0-12'])['mode']=='full'
    check(state)


def test_constructor_refreshes_stale_cache_and_same_row_clears_calibration():
    state = world()
    state.events_by_id['0-0'].target = 'shared'
    tracker = GroundingCorrectionTracker(state)
    check(state)
    affected = tracker.reverse['0-0']
    for key in affected:
        tracker.index['entries'][key]['calibration_key'] = 'stale'
    tracker.refresh(['0-0'])
    assert all('calibration_key' not in tracker.index['entries'][k] for k in affected)
    check(state)


def test_storage_order_and_evidence_id_rename():
    state = world()
    tracker = GroundingCorrectionTracker(state)
    state.events_by_id = dict(reversed(list(state.events_by_id.items())))
    assert tracker.refresh([])['mode'] == 'noop'
    check(state)
    item = state.events_by_id.pop('0-0')
    item.id = 'renamed'
    state.events_by_id[item.id] = item
    for primitive in state.structural_primitives.values():
        if '0-0' in primitive.evidence_event_ids:
            primitive.evidence_event_ids.remove('0-0')
            primitive.evidence_event_ids.add('renamed')
    assert tracker.refresh(['0-0','renamed'])['reason'] == 'primitive_or_support_changed'
    check(state)


@pytest.mark.parametrize('fraction', [-1, 1.1, float('nan'), float('inf'), True, '0.5'])
def test_invalid_fraction(fraction):
    with pytest.raises(ValueError):
        GroundingCorrectionTracker(RisaState(), max_fraction=fraction)
