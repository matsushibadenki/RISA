from collections import Counter
import pytest
from risa.engine.grounding_sampling import GroundingSampleWindow


def test_bounded_uniform_inclusion_and_independent_streams():
    counts=Counter()
    for seed in range(512):
        sampler=GroundingSampleWindow(capacity=8,seed=seed)
        for i in range(64):sampler.observe('p',['a'],str(i),'other',['t'])
        sample=sampler.samples()['p']
        assert len(sample)==8
        counts.update(int(args[1]) for args in sample)
    # Expected count is 64 per position. Broad deterministic guard against prefix/tail bias.
    assert all(35 <= counts[i] <= 95 for i in range(64))
    a=GroundingSampleWindow();b=GroundingSampleWindow()
    for i in range(100):
        a.observe('p',['a'],str(i),'other',['t'])
        b.observe('noise',[],None,None,[])
        b.observe('p',['a'],str(i),'other',['t'])
    assert a.samples()['p']==b.samples()['p']


def test_joint_samples_freeze_inputs_and_detect_changed_tail():
    windows={n:GroundingSampleWindow(policy=p) for n,p in
             [('old','reservoir'),('new','reservoir'),('prefix','prefix')]}
    for i in range(128):
        windows['old'].observe('p',['a'],'same','same',['x'])
        for n in ('new','prefix'):
            changed=i>=8
            roles=['b'] if changed else ['a']
            windows[n].observe('p',roles,'same','other' if changed else 'same',['y'] if changed else ['x'])
            roles.append('mutated')
    assert windows['new'].samples()!=windows['old'].samples()
    assert windows['prefix'].samples()==windows['old'].samples()
    assert all(args in [(('a',),'same','same',('x',)),(('b',),'same','other',('y',))]
               for args in windows['new'].samples()['p'])
    for kwargs in (dict(capacity=0),dict(capacity=65),dict(capacity=True),dict(seed=True),dict(policy='bad')):
        with pytest.raises(ValueError):GroundingSampleWindow(**kwargs)


def test_sampling_world_parity_and_unchanged_prefix_drift():
    from experiments.grounding_sampling_evaluation import worker
    result=worker(densities=(32,))
    row=next(r for r in result['rows'] if r['world']=='concentrated')
    first,shift=row['trace'][:2]
    assert first['prefix8']['sample_digest']==shift['prefix8']['sample_digest']
    assert first['reservoir8']['sample_digest']!=shift['reservoir8']['sample_digest']
    assert shift['reservoir8']['sample_tv'] < shift['prefix8']['sample_tv']
    reports=row['stats']
    assert all(e['reused'] for e in reports['prefix8']['calibration'][1]['entries'].values())
    assert all(not e['reused'] for e in reports['reservoir8']['calibration'][1]['entries'].values())


def test_schedule_skips_without_observer_and_forces_refresh():
    from risa.engine.grounding_sampling import GroundingSampleSchedule
    schedule=GroundingSampleSchedule(interval=4)
    first=schedule.next_window()
    assert isinstance(first,GroundingSampleWindow)
    assert schedule.next_window() is None
    refreshed=schedule.next_window(force=True)
    assert refreshed is not first and refreshed.samples()=={}
    assert [schedule.next_window() for _ in range(3)]==[None]*3
    assert isinstance(schedule.next_window(),GroundingSampleWindow)
    for invalid in (0,-1,True,1.5):
        with pytest.raises(ValueError):GroundingSampleSchedule(interval=invalid)
    with pytest.raises(ValueError):schedule.next_window(force=1)


def test_cadence_world_parity_and_missed_drift():
    from experiments.grounding_cadence_evaluation import worker
    result=worker(densities=(32,))
    row=next(r for r in result['rows'] if r['world']=='concentrated')
    first,shift,refresh,_=row['trace']
    assert shift['every2']['sample_digest']==first['every2']['sample_digest']
    assert shift['every2']['sample_tv'] > shift['every1']['sample_tv']
    assert refresh['every2']['collected'] and not refresh['every4']['collected']
    assert refresh['every2']['sample_tv'] < refresh['every4']['sample_tv']
    assert [len(row['stats'][n]['calibration']) for n in ('every1','every2','every4')]==[3,2,1]
