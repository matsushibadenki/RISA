from copy import deepcopy
import sys
import pytest
from experiments.grounding_total_budget_evaluation import event, cases, query, OPTIONS
from risa.core.state import RisaState
from risa.engine.runtime import train_events
from risa.engine.primitive_grounding import build_primitive_grounding, invalidate_primitive_grounding


def measured(index):
    return sum(sys.getsizeof(e['lookup']) + sum(sys.getsizeof(b) + sys.getsizeof(b['targets'])
        for b in e['lookup'].values()) for e in index['entries'].values() if e['lookup'] is not None)


def base():
    state = RisaState()
    train_events(state, [event(p, k) for p in range(4) for k in range(8)], OPTIONS)
    return state


def test_aggregate_mixed_boundaries_order_and_dual_caps():
    state = base()
    full = build_primitive_grounding(state, total_lookup_budget_bytes=1000000)
    assert full['lookup_bytes_used'] == measured(full)
    sizes = [e['lookup_bytes'] for _, e in sorted(full['entries'].items())]
    budget = sum(sizes[:2])
    for cap in (0, budget-1, budget, sum(sizes)):
        index = build_primitive_grounding(state, total_lookup_budget_bytes=cap)
        assert index['lookup_bytes_used'] == measured(index) <= cap
        if cap == budget:
            assert sum(e['lookup'] is not None for e in index['entries'].values()) == 2
        for case in cases():
            assert query(state, case, True) == query(state, case, False)
    index = build_primitive_grounding(state, total_lookup_budget_bytes=budget, lookup_budget_bytes=sizes[0])
    assert index['lookup_bytes_used'] <= budget
    assert all(e['lookup_bytes'] <= sizes[0] for e in index['entries'].values())
    selected = [k for k,e in index['entries'].items() if e['lookup'] is not None]
    state.structural_primitives = dict(reversed(list(state.structural_primitives.items())))
    index = build_primitive_grounding(state, total_lookup_budget_bytes=budget, lookup_budget_bytes=sizes[0])
    assert [k for k,e in index['entries'].items() if e['lookup'] is not None] == selected
    for invalid in (-1, True, 1.5):
        with pytest.raises(ValueError):
            build_primitive_grounding(state, total_lookup_budget_bytes=invalid)


def test_append_releases_budget_and_correction_replacement_preserve_cap():
    state = base()
    index = build_primitive_grounding(state, incremental=True, total_lookup_budget_bytes=8192)
    before = index['lookup_bytes_used']
    first = next(k for k in index['entries'] if ':go0->' in k)
    e = event(0, 8)
    e.actor_roles = [f'wide{i}' for i in range(64)]
    e.target_roles = [f'target{i}' for i in range(64)]
    train_events(state, [e], OPTIONS)
    assert index['entries'][first]['lookup'] is None
    assert index['lookup_bytes_used'] == measured(index) < before
    e = event(0, 9)
    e.action, e.observed_effects = 'new-action', ['new-done']
    train_events(state, [e], OPTIONS)
    assert any('new-action' in k and v['lookup'] is not None for k,v in index['entries'].items())
    assert index['lookup_bytes_used'] == measured(index) <= 8192
    train_events(state, [e], OPTIONS)
    assert index['lookup_bytes_used'] == measured(index)
    state.events_by_id['0-0'].target = 'shared'
    invalidate_primitive_grounding(state)
    for case in cases():
        assert query(state, case, True) == query(state, case, False)
    index = state._primitive_grounding_index
    assert index['total_lookup_budget_bytes'] == 8192
    state.structural_primitives[first] = deepcopy(state.structural_primitives[first])
    assert query(state, cases()[0], True) == query(state, cases()[0], False)
    assert state._primitive_grounding_index['lookup_bytes_used'] == measured(state._primitive_grounding_index) <= 8192
    restored = RisaState.from_dict(state.to_dict())
    assert not hasattr(restored, '_primitive_grounding_total_lookup_budget')


def test_mixed_experiment_saved_and_complete_parity():
    from experiments.grounding_total_budget_evaluation import run_worker
    result = run_worker()
    assert all(r['mismatches'] == 0 and r['stats']['mixed']['used'] <= 8192 for r in result['rows'])
