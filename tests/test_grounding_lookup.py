from itertools import combinations, product

from experiments import grounding_linear_reference as linear
from risa.engine import primitive_grounding as grounding


def subsets(values):
    return [list(c) for n in range(len(values) + 1) for c in combinations(values, n)]


def test_joint_lookup_exhaustive_masks_multirole_and_wildcards():
    # Independent evidence must not create (b,y,equal) or (a,x,different).
    fixtures = [
        {(('a', 'b'), ('x',), True), (('a',), ('y', 'z'), False)},
        {(('a',), (), False), (('b',), ('x',), None), ((), ('y',), True)},
        {((), (), None)},
        {(('a', 'b'), ('x', 'y'), None), (('a',), ('z',), True)},
        {(('a',), ('x',), True), (('a',), ('x',), False), (('b',), (), True)},
        set(),
    ]
    for rows in fixtures:
        entry = dict(rows=rows, actor_typed=any(ar for ar, _, _ in rows), lookup={})
        for row in rows:
            grounding._add_lookup(entry['lookup'], row)
        for ar, tr, identities in product(subsets(('a', 'b', 'absent')), subsets(('x', 'y', 'z', 'absent')),
                                           [(None, None), ('q', None), (None, 'r'), ('q', 'r'), (' Q ', 'q')]):
            args = (entry, ar, *identities, tr)
            assert grounding.actor_matches(*args) == linear.actor_matches(*args)


def test_lookup_experiment_checks_saved_bytes_and_costs():
    from experiments.grounding_lookup_evaluation import run
    result = run(diversities=(8,), widths=(2,), repetitions=1, updates=2)
    row = result['rows'][0]
    assert row['mismatches'] == 0
    assert row['stats']['lookup']['probes'] > 0
    assert row['stats']['lookup']['heap_after'] > row['stats']['linear']['heap_after']
    assert row['stats']['lookup']['update_reads'] == 2


def test_complete_results_multirole_wildcard_append_reload_and_saved_bytes(tmp_path):
    from risa.core.models import Event
    from risa.core.state import RisaState
    from risa.engine.runtime import train_events, TrainingOptions
    from risa.engine.persistence import save_state, load_state
    from risa.engine.composer import compose_to_effect

    state = RisaState()
    grounding.build_primitive_grounding(state, incremental=True)
    options = TrainingOptions(enable_metabolism=False, enable_replay=False, enable_adaptation=False)
    specs = [(['a', 'b'], ['x'], 'one'), (['a'], ['y', 'z'], 'other'),
             (['c'], [], None), ([], [], None)]
    for i in range(12):
        ar, tr, target = specs[i % 4]
        train_events(state, [Event(id=str(i), timestamp=i, actor='one', target=target,
            action='go', observed_effects=['done'], actor_roles=ar, target_roles=tr, source=str(i % 2))], options)
    plain = RisaState.from_dict(state.to_dict())
    save_state(state, tmp_path / 'indexed')
    save_state(plain, tmp_path / 'plain')
    assert (tmp_path / 'indexed/state.json').read_bytes() == (tmp_path / 'plain/state.json').read_bytes()
    restored = load_state(tmp_path / 'indexed')
    for ar, tr, identities, candidates in product(
            [[], ['a'], ['b'], ['c'], ['a', 'b'], ['absent', 'c']],
            [[], ['x'], ['y'], ['y', 'z'], ['absent']],
            [(None, None), ('new', None), ('new', 'new'), ('new', 'other')], [False, True]):
        kwargs = dict(actor_roles=ar, target_roles=tr, actor=identities[0], target=identities[1],
                      enable_candidate_concepts=candidates)
        expected = compose_to_effect(plain, 'go', 'done', **kwargs)
        assert compose_to_effect(state, 'go', 'done', use_grounding_index=True, **kwargs) == expected
        assert compose_to_effect(restored, 'go', 'done', use_grounding_index=True, **kwargs) == expected
    assert not compose_to_effect(state, 'go', 'done', actor_roles=['b'], target_roles=['y'],
                                 actor='new', target='other', use_grounding_index=True).primitive_ids
