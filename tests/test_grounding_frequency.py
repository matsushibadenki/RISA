import pytest
from experiments.grounding_frequency_evaluation import event,query,OPTIONS,verify
from risa.core.state import RisaState
from risa.engine.runtime import train_events
from risa.engine import primitive_grounding as g


def state():
    s=RisaState()
    train_events(s,[event(p,k) for p in range(4) for k in range(64)],OPTIONS)
    g.build_primitive_grounding(s,incremental=True,total_lookup_budget_bytes=12000,allocation_policy='frequency')
    return s


def selected(s,p):
    return next(e for k,e in s._primitive_grounding_index['entries'].items() if f':go{p}->' in k)['lookup'] is not None


def test_recent_frequency_promotes_demotes_and_repromotes_with_cost_cache():
    s=state()
    assert selected(s,0) and not selected(s,3)
    for hot in (3,0,3):
        for _ in range(8): query(s,hot,23,0,True)
        moved=g.rebalance_primitive_grounding(s)
        assert moved['promotions'] > 0 and selected(s,hot)
        assert s._primitive_grounding_index['lookup_bytes_used']<=12000
        assert all(e['query_hits']==0 for e in s._primitive_grounding_index['entries'].values())
        assert g.rebalance_primitive_grounding(s)['promotions']==0
    assert moved['cost_probes']==0
    # Equal frequency prefers the cheaper dictionary, not the higher-ID hot entry.
    for hot in (0,3): query(s,hot,23,0,True)
    g.rebalance_primitive_grounding(s)
    assert selected(s,0) and not selected(s,3)


def test_append_correction_and_policy_validation():
    s=state()
    query(s,3,23,0,True)
    g.rebalance_primitive_grounding(s)
    train_events(s,[event(p,64) for p in range(4)],OPTIONS)
    assert all(e['lookup_cost'] is None for e in s._primitive_grounding_index['entries'].values())
    query(s,2,64,0,True)
    assert g.rebalance_primitive_grounding(s)['cost_probes']>0
    s.events_by_id['0-0'].target='shared'
    g.invalidate_primitive_grounding(s)
    assert query(s,0,0,1,True)==query(s,0,0,1,False)
    assert s._primitive_grounding_index['allocation_policy']=='frequency'
    restored=RisaState.from_dict(s.to_dict())
    assert not hasattr(restored,'_primitive_grounding_allocation_policy')
    for kwargs in (dict(allocation_policy='unknown'),dict(allocation_policy='frequency')):
        with pytest.raises(ValueError): g.build_primitive_grounding(s,**kwargs)
    g.build_primitive_grounding(s,total_lookup_budget_bytes=0,allocation_policy='frequency')
    query(s,0,23,0,True)
    g.rebalance_primitive_grounding(s)
    assert s._primitive_grounding_index['lookup_bytes_used']==0


def test_frequency_experiment_exact_results_and_saved_bytes():
    from experiments.grounding_frequency_evaluation import run_worker
    result=run_worker(queries=8)
    assert all(r['mismatches']==0 for r in result['rows'])


def test_confirmation_breaks_on_empty_windows_and_append():
    s = state()
    def window():
        query(s,3,23,0,True)
        return g.rebalance_primitive_grounding(s, confirmation_windows=2)
    assert window()['promotions'] == 0
    g.rebalance_primitive_grounding(s, confirmation_windows=2)
    assert window()['promotions'] == 0
    train_events(s, [event(p,64) for p in range(4)], OPTIONS)
    assert window()['promotions'] == 0
    assert window()['promotions'] > 0 and selected(s,3)
    assert query(s,3,64,1,True) == query(s,3,64,1,False)
    # Correction rebuild forgets the old proposal but retains frequency mode.
    g.invalidate_primitive_grounding(s)
    assert window()['promotions'] == 0
    assert window()['promotions'] > 0


def test_residency_limits_moves_and_validates_controls():
    s = state()
    for hot, moves in ((3,False),(3,True),(0,False),(0,True)):
        query(s,hot,23,0,True)
        result = g.rebalance_primitive_grounding(s, minimum_residency_windows=2)
        assert bool(result['promotions']) == moves
        assert s._primitive_grounding_index['lookup_bytes_used'] <= 12000
    for kwargs in (dict(confirmation_windows=0), dict(confirmation_windows=True),
                   dict(minimum_residency_windows=-1), dict(minimum_residency_windows=1.5)):
        with pytest.raises(ValueError):
            g.rebalance_primitive_grounding(s, **kwargs)


def test_stability_experiment_parity():
    from experiments.grounding_stability_evaluation import GATES
    from experiments.grounding_frequency_evaluation import run_worker
    result = run_worker(queries=8, gates=GATES)
    assert all(row['mismatches'] == 0 for row in result['rows'])


def test_cold_probe_deferral_and_later_access():
    s = state()
    query(s,0,23,0,True)
    first = g.rebalance_primitive_grounding(s, confirmation_windows=2)
    assert first['cost_probes'] == 0
    cold = next(e for k,e in s._primitive_grounding_index['entries'].items() if ':go3->' in k)
    assert cold['lookup_cost'] is None
    query(s,3,23,0,True)
    assert g.rebalance_primitive_grounding(s, confirmation_windows=2)['cost_probes'] == 1
    query(s,3,23,0,True)
    assert g.rebalance_primitive_grounding(s, confirmation_windows=2)['promotions'] > 0
    assert selected(s,3)
    assert query(s,3,23,1,True) == query(s,3,23,1,False)
    eager = state()
    query(eager,0,23,0,True)
    assert g.rebalance_primitive_grounding(eager, confirmation_windows=2,
                                         probe_cold_candidates=True)['cost_probes'] == 2
    with pytest.raises(ValueError):
        g.rebalance_primitive_grounding(s, probe_cold_candidates=1)


def test_independent_world_payback_parity():
    from experiments.grounding_payback_evaluation import run_worker
    rows = run_worker(densities=(1,))['rows']
    assert {r['world'] for r in rows} == {'independent','coupled'}
    for row in rows:
        first = row['trace'][0]['arms']
        assert first['lazy']['probes'] < first['eager']['probes']
        assert row['comparisons'] > 0


def test_saved_content_digest_only_ignores_edge_order():
    import json
    from experiments.grounding_payback_evaluation import content_digest
    a = dict(graph=dict(edges=[['a','b',1],['b','c',2]]), other=[1,2])
    b = dict(graph=dict(edges=list(reversed(a['graph']['edges']))), other=[1,2])
    assert content_digest(json.dumps(a)) == content_digest(json.dumps(b))
    b['graph']['edges'].append(['a','b',1])
    assert content_digest(json.dumps(a)) != content_digest(json.dumps(b))
    b['graph']['edges'] = a['graph']['edges']
    b['other'].reverse()
    assert content_digest(json.dumps(a)) != content_digest(json.dumps(b))
