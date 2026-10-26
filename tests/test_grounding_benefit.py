import pytest
from risa.core.state import RisaState
from experiments.grounding_frequency_evaluation import query, event, OPTIONS
from risa.engine import primitive_grounding as g
from risa.engine.grounding_calibration import calibrate_grounding_benefits
from risa.engine.runtime import train_events


def state():
    s=RisaState()
    train_events(s,[event(p,k) for p in range(4) for k in range(64)],OPTIONS)
    g.build_primitive_grounding(s,incremental=True,total_lookup_budget_bytes=12000,allocation_policy='frequency')
    return s


def selected(s,p):
    return next(e for k,e in s._primitive_grounding_index['entries'].items() if f':go{p}->' in k)['lookup'] is not None


def test_benefit_gate_uses_net_savings_not_only_frequency():
    s=state()
    for k,e in s._primitive_grounding_index['entries'].items():
        e.update(benefit_seconds=0., benefit_setup_cpu=1.)
    hot=next(e for k,e in s._primitive_grounding_index['entries'].items() if ':go3->' in k)
    hot.update(benefit_seconds=.01,benefit_setup_cpu=.1)
    query(s,3,23,0,True)
    g.rebalance_primitive_grounding(s,allocation_metric='benefit')
    assert not selected(s,3)  # One hit cannot repay setup.
    for _ in range(20): query(s,3,23,0,True)
    g.rebalance_primitive_grounding(s,allocation_metric='benefit')
    assert selected(s,3)
    assert s._primitive_grounding_index['lookup_bytes_used']<=12000
    train_events(s,[event(p,64) for p in range(4)],OPTIONS)
    assert all('benefit_seconds' not in e for e in s._primitive_grounding_index['entries'].values())
    query(s,3,64,1,True)
    g.rebalance_primitive_grounding(s,allocation_metric='benefit')
    assert not selected(s,3)
    assert query(s,3,64,1,True)==query(s,3,64,1,False)
    with pytest.raises(ValueError):g.rebalance_primitive_grounding(s,allocation_metric='bad')


def test_calibration_preserves_counters_results_and_serialization():
    s=state()
    key=next(k for k in s.structural_primitives if ':go3->' in k)
    before=s.to_dict()
    query(s,3,23,0,True)
    entry=s._primitive_grounding_index['entries'][key]
    hits=entry['query_hits']
    lookup=entry['lookup']
    report=calibrate_grounding_benefits(s,{key:[(['a3-0','a3-1'],'n','n',['t23-0','t23-1']),
        (['a3-0'],'n','other',['absent'])]},repetitions=2)
    assert report['entries'][key]['fits']
    assert entry['query_hits']==hits and entry['lookup'] is lookup
    assert s.to_dict()==before
    assert entry['benefit_seconds']>=0
    assert entry['benefit_setup_cpu']>=report['entries'][key]['build_cpu']
    g.invalidate_primitive_grounding(s)
    query(s,3,23,0,True)
    assert all('benefit_seconds' not in e for e in s._primitive_grounding_index['entries'].values())
    with pytest.raises(ValueError):calibrate_grounding_benefits(s,{},rounds=True)


def test_benefit_experiment_complete_results_and_persistence():
    from experiments.grounding_benefit_evaluation import run_worker
    result=run_worker(densities=(8,))
    assert {r['world'] for r in result['rows']}=={'independent','coupled','concentrated'}


def test_calibration_reuse_requires_same_joint_rows_samples_and_settings():
    from experiments.compositional_holdout import training_episode
    s=RisaState()
    train_events(s,[e for i in range(8) for e in training_episode(17,'independent',i)],OPTIONS)
    ix=g.build_primitive_grounding(s,incremental=True,total_lookup_budget_bytes=2320,allocation_policy='frequency')
    key=next(k for k in ix['entries'] if 'prepare_a->' in k)
    samples={key:[(['operator'],'new','other',['remote_unit'])]}
    def calibrate(**kw):return calibrate_grounding_benefits(s,samples,repetitions=2,reuse=True,**kw)['entries'][key]
    assert not calibrate()['reused']
    train_events(s,training_episode(17,'independent',8),OPTIONS)
    assert calibrate()['reused']
    assert calibrate()['reused']
    assert not calibrate()['reused']  # periodic refresh after two reuses
    samples[key]=[(['operator'],'new','new',['remote_unit'])]
    assert not calibrate()['reused']  # changed identity sample
    assert not calibrate(max_reuses=0)['reused']
    g.invalidate_primitive_grounding(s)
    g.build_primitive_grounding(s,incremental=True,total_lookup_budget_bytes=2320,allocation_policy='frequency')
    assert not calibrate()['reused']
    for kw in (dict(reuse=1),dict(max_reuses=True),dict(max_reuses=-1)):
        with pytest.raises(ValueError):calibrate_grounding_benefits(s,samples,**kw)


def test_reuse_preserves_confirmation_and_bounds_sample_consumption():
    s=state();key=next(k for k in s.structural_primitives if ':go3->' in k)
    args=(['a3-0'],'n','other',['absent'])
    def bounded():
        for _ in range(64):yield args
        raise AssertionError('consumed more than 64 samples')
    calibrate_grounding_benefits(s,{key:bounded()},repetitions=1,reuse=True)
    ix=s._primitive_grounding_index
    ix.update(proposal=frozenset({key}),proposal_windows=1)
    result=calibrate_grounding_benefits(s,{key:bounded()},repetitions=1,reuse=True)
    assert result['entries'][key]['reused']
    assert ix['proposal_windows']==1


def test_reuse_experiment_complete_results_and_saved_bytes():
    from experiments.grounding_reuse_evaluation import worker
    result=worker(densities=(8,))
    for row in result['rows']:
        reports=row['stats']['reuse']['calibration']
        assert any(e.get('reused') for e in reports[1]['entries'].values())
        if row['world']=='concentrated':
            assert all(not e.get('reused') for e in reports[2]['entries'].values())
