import pytest
from risa.engine.grounding_sampling import GroundingCountTrigger


def test_count_hint_thresholds_and_observed_window_suppression():
    trigger=GroundingCountTrigger()
    assert not trigger.observe(16)
    assert not trigger.observe(31)
    assert trigger.observe(64)  # inclusive factor, above absolute floor
    assert not trigger.observe(128,sampled=True)
    assert trigger.observe(0)
    assert not trigger.observe(15)
    assert not trigger.observe(30)  # absolute change below floor
    assert trigger.observe(60)
    assert not trigger.observe(60)  # equal-count joint drift is invisible
    for kwargs in (dict(factor=1),dict(factor=True),dict(min_delta=0),dict(min_delta=1.5)):
        with pytest.raises(ValueError):GroundingCountTrigger(**kwargs)
    for count in (-1,True,1.5):
        with pytest.raises(ValueError):trigger.observe(count)
    with pytest.raises(ValueError):trigger.observe(128,sampled=1)
    assert trigger._previous==60


def test_transient_world_parity_and_causal_hints():
    from experiments.grounding_transient_evaluation import worker
    result=worker(densities=(32,))
    for row in result['rows']:
        traces=row['trace'];phase=row['phase']
        assert not traces[phase]['count4']['forced']  # never sees future count
        if not row['count_burst']:
            assert not any(t['count4']['forced'] for t in traces)
            assert [t['count4']['collected'] for t in traces]==[t['every4']['collected'] for t in traces]
        elif phase==1:
            assert not traces[phase]['count4']['collected']  # transient missed
            assert traces[2]['count4']['forced']
            assert not traces[3]['count4']['forced']  # return already sampled
        else:
            assert traces[phase]['count4']['collected']
            assert not traces[5]['count4']['forced']
            assert traces[6]['count4']['forced']  # observes return only at end of 5
            if row['world']=='concentrated':
                assert traces[6]['count4']['sample_tv'] < traces[6]['every4']['sample_tv']
    assert len(result['rows'])==12
