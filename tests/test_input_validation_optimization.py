from copy import deepcopy
from dataclasses import replace
import pytest
from risa.core.models import Event
from risa.core.state import RisaState
from risa.engine.runtime import TrainingOptions, _validate_and_filter_events, train_events
from experiments.references.runtime_before_history_20261008 import _validate_and_filter_events as validate_before
from experiments.references.runtime_before_history_20261008 import train_events as train_before


def event(id, timestamp, episode=None):
    return Event(id=id,timestamp=timestamp,actor='robot',action='go',episode_id=episode,observed_effects=['done'])


@pytest.mark.parametrize('case', ['empty','repeated','new-duplicate','conflict-history','conflict-episode','conflict-batch','late','tie','different-episode','mutated-history'])
def test_validation_preserves_results_errors_and_inputs(case):
    old=event('old',5,'a')
    state=RisaState();state.events_by_id={'old':old,'other':event('other',100,'b')}
    inputs={
        'empty':[], 'repeated':[deepcopy(old),deepcopy(old)],
        'new-duplicate':[event('new',6,'a'),event('new',6,'a')],
        'conflict-history':[replace(old,actor='other')],
        'conflict-episode':[replace(old,episode_id='new-episode')],
        'conflict-batch':[event('new',6,'a'),replace(event('new',6,'a'),actor='other')],
        'late':[event('late',4,'a')], 'tie':[event('aaa',5,'a')],
        'different-episode':[event('new',1,'c'),event('next',6,'a')],
        'mutated-history':[event('new',7,'a')],
    }[case]
    if case=='mutated-history':old.timestamp=8
    snapshot=deepcopy(state.events_by_id);input_snapshot=deepcopy(inputs)
    def outcome(function):
        try:return ('ok',function(state,inputs))
        except ValueError as exc:return ('error',str(exc))
    assert outcome(_validate_and_filter_events)==outcome(validate_before)
    assert state.events_by_id==snapshot and inputs==input_snapshot


def test_optimized_validation_preserves_full_training_chunks_and_idempotence():
    current,reference=RisaState(),RisaState()
    for start in range(0,60,6):
        chunk=[event(f'e{i:03d}',i+1,f'episode-{i//8}') for i in range(start,start+6)]
        # Include both in-batch and previously persisted duplicates.
        if start:chunk.append(deepcopy(current.events_by_id[f'e{start-1:03d}']))
        chunk.append(deepcopy(chunk[0]))
        train_events(current,deepcopy(chunk),TrainingOptions(replay_max_events=8))
        train_before(reference,deepcopy(chunk),TrainingOptions(replay_max_events=8))
        assert current.to_dict()==reference.to_dict()
