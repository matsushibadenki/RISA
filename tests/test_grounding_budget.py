import sys
import pytest
from experiments.grounding_lookup_evaluation import event, cases, query
from risa.core.state import RisaState
from risa.engine.runtime import train_events, TrainingOptions
from risa.engine.primitive_grounding import build_primitive_grounding, invalidate_primitive_grounding


def test_budget_overflow_append_correction_and_boundary():
    state = RisaState()
    opts = TrainingOptions(enable_metabolism=False, enable_replay=False, enable_adaptation=False)
    train_events(state, [event(i, i, 4) for i in range(8)], opts)
    index = build_primitive_grounding(state, incremental=True, lookup_budget_bytes=100000)
    entry = next(iter(index['entries'].values()))
    size = sys.getsizeof(entry['lookup']) + sum(sys.getsizeof(b) + sys.getsizeof(b['targets']) for b in entry['lookup'].values())
    assert entry['lookup_bytes'] == size
    for budget in (0, size - 1, size):
        index = build_primitive_grounding(state, incremental=True, lookup_budget_bytes=budget)
        entry = next(iter(index['entries'].values()))
        assert (entry['lookup'] is None) == (budget < size)
        for case in cases(8, 4, 7):
            assert query(state, case, True) == query(state, case, False)
    for i in range(8, 20):
        train_events(state, [event(i, i, 4)], opts)
    entry = next(iter(index['entries'].values()))
    assert entry['lookup'] is None and entry['lookup_bytes'] == 0
    state.events_by_id['0'].target = state.events_by_id['0'].actor
    invalidate_primitive_grounding(state)
    for case in cases(8, 4, 19):
        assert query(state, case, True) == query(state, case, False)
    assert state._primitive_grounding_index['lookup_budget_bytes'] == size
    assert '_primitive_grounding_lookup_budget' not in state.to_dict()
    for invalid in (-1, True, 1.5):
        with pytest.raises(ValueError):
            build_primitive_grounding(state, lookup_budget_bytes=invalid)


def test_budget_experiment_parity():
    from experiments.grounding_budget_evaluation import run
    result = run(widths=(4,), densities=(1,), repetitions=1)
    assert all(r['mismatches'] == 0 for r in result['rows'])


def test_budget_compositional_worlds_and_fallback_wildcards():
    from experiments.compositional_holdout import training_episode, heldout_cases
    from experiments.compositional_grounding_costs import _query
    from experiments.grounding_linear_reference import actor_matches as reference
    from risa.engine.primitive_grounding import actor_matches
    for world in ('independent', 'coupled'):
        state = RisaState()
        train_events(state, [e for i in range(8) for e in training_episode(701, world, i)],
                     TrainingOptions(enable_metabolism=False, enable_replay=False))
        for budget in (0, 8192):
            build_primitive_grounding(state, lookup_budget_bytes=budget)
            for case in heldout_cases(701, world):
                for candidates in (False, True):
                    assert _query(state, case, candidates, True) == _query(state, case, candidates, False)
    rows = {(('a', 'b'), (), None), (('c',), ('x',), True), ((), ('z',), False)}
    entry = dict(rows=rows, actor_typed=True, lookup=None)
    for ar in ([], ['a'], ['c'], ['a', 'c']):
        for tr in ([], ['x'], ['absent']):
            for actor, target in ((None, None), ('a', 'b'), ('a', 'a'), ('a', None)):
                assert actor_matches(entry, ar, actor, target, tr) == reference(entry, ar, actor, target, tr)
